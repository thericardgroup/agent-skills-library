#!/usr/bin/env python3
"""Verify ONE posting and write the record the package gate reads.

Three rules this file exists to enforce, each learned from a failure:

1. Identity is the requisition id, never the title. Boards carry duplicate
   titles; matching on text certifies whichever one happens to be first.
2. Not knowing is not the same as passing. If the location language is
   ambiguous, or nobody has read the requirements, the record says so and the
   gate stays shut.
3. A check that could not complete invalidates the previous success. An
   unreachable board means we no longer know, not that nothing changed.

Usage:
  verify_one.py --url https://job-boards.greenhouse.io/acme/jobs/4056789
  verify_one.py --platform greenhouse --board acme --req 4056789 --requirements-reviewed
  verify_one.py --key 'greenhouse::acme::4056789'        re-check an existing record
"""
import argparse, hashlib, json, re, sys, os, urllib.request, urllib.error, html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import (record_verification, record_attempt_failed, verification_key,
                    profile_fingerprint, Timer)
from statepath import load

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

ONSITE = re.compile(r"""(
   \d\s*\+?\s*(?:day|days)\s*(?:per|a|/|each)\s*week\s*(?:in[- ]?(?:the\s*)?office|on[-\s]?site|in\s*office)
 | (?:in[- ]?office|on[-\s]?site|in\s*person)\s*\d\s*(?:day|days)\s*(?:per|a|/|each)\s*week
 | hybrid\s*(?:work\s*)?schedule
 | this\s*(?:is\s*a\s*)?hybrid\s*(?:role|position)
 | required\s*to\s*(?:be\s*)?(?:work\s*)?(?:on[-\s]?site|in\s*(?:the\s*)?office)
 | (?:work|working|based)\s*(?:at|in|from)\s*(?:the\s+|our\s+)?(?:[A-Z][\w.-]{2,20}\s+)?office
 | (?:one|two|three|four|five)\s*days?\s*(?:per|a|/|each)\s*week
 | (?:in\s*(?:the\s*)?office|on[-\s]?site)\s*(?:every\s*)?(?:day|daily|weekday|full[- ]time)
 | (?:every\s*weekday|five\s*days\s*a\s*week|5\s*days\s*a\s*week)
 | must\s*(?:be\s*)?(?:located|reside|live)\s*(?:in|within|near)
 | commut(?:e|ing)\s*distance
 | relocat(?:e|ion)\s*(?:is\s*)?required
)""", re.I | re.X)

# Affirmative remote evidence. Absence of onsite language is not permission --
# a posting that says nothing about location has told us nothing.
REMOTE = re.compile(r"""(
   (?:fully|100%|entirely|completely)\s*remote
 | remote[- ](?:first|only|friendly)
 | work\s*from\s*(?:anywhere|home)
 | \btelecommut
 | this\s*(?:is\s*a\s*)?remote\s*(?:role|position)
 | \bremote\b[\s\-,:()]{0,4}(?:u\.?s\.?a?\.?|united states|anywhere|nationwide)\b
 | \bremote\b[^.]{0,40}\b(?:united states|usa|anywhere)
 | \(\s*remote\s*\)
)""", re.I | re.X)

REQ_HEADING = re.compile(
    r'(requirements|qualifications|what you.{0,6}(need|bring|ll have)|who you are'
    r'|about you|you have|we.{0,4}re looking for|minimum qualifications)', re.I)


def _get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} from {url}"
    except Exception as e:
        return None, f"{type(e).__name__} fetching {url}"


def http_ok(url):
    """A live API record is not proof the user can apply. One employer's
    published link contained an unfilled template placeholder and every variant
    404'd while the posting itself looked perfectly healthy."""
    if not url:
        return False, "no apply URL on the posting"
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            code = r.getcode()
    except urllib.error.HTTPError as e:
        if e.code in (403, 405):   # some boards reject HEAD but serve GET
            try:
                with urllib.request.urlopen(
                        urllib.request.Request(url, headers=UA), timeout=20) as r:
                    code = r.getcode()
            except Exception as e2:
                return False, f"apply URL unreachable ({type(e2).__name__})"
        else:
            return False, f"apply URL returned HTTP {e.code}"
    except Exception as e:
        return False, f"apply URL unreachable ({type(e).__name__})"
    return (200 <= code < 400), f"apply URL HTTP {code}"


def _strip(h):
    """Unescape before stripping. Greenhouse returns entity-encoded HTML, so
    stripping first leaves &lt;p&gt; to decode into a visible tag afterwards."""
    text = re.sub(r'<[^>]+>', ' ', html.unescape(h or ""))
    return re.sub(r'[ \t]{2,}', ' ', html.unescape(text)).strip()


# --- ATS adapters ---------------------------------------------------------
# Each returns (posting_dict, error). posting_dict keys: title, body, location,
# apply_url. Adding a board means adding one function here, not touching main().

def _greenhouse(board, req):
    d, err = _get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{req}")
    if err:
        return None, err
    return dict(title=d.get("title", ""), body=_strip(d.get("content")),
                location=(d.get("location") or {}).get("name", ""),
                apply_url=d.get("absolute_url") or
                f"https://boards.greenhouse.io/embed/job_app?for={board}&token={req}"), None


def _ashby(board, req):
    d, err = _get(f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true")
    if err:
        return None, err
    for j in d.get("jobs", []):
        if str(j.get("id")) == str(req):
            # isRemote can be true while workplaceType is Hybrid. Trust the body.
            return dict(title=j.get("title", ""), body=_strip(j.get("descriptionHtml")),
                        location=f"{j.get('location','')} ({j.get('workplaceType','?')})",
                        apply_url=j.get("jobUrl", "")), None
    return None, f"requisition {req} not on the {board} board"


def _lever_body(d):
    # Lever splits a posting: the overview sits in descriptionPlain and the
    # requirements live in lists[].content. Reading only the overview drops the
    # qualifications, which is the one section the whole pipeline depends on.
    parts = [_strip(d.get("descriptionPlain") or d.get("description"))]
    for sec in d.get("lists") or []:
        parts.append(_strip(sec.get("text", "")))
        parts.append(_strip(sec.get("content", "")))
    parts.append(_strip(d.get("additionalPlain") or d.get("additional")))
    return "\n".join(p for p in parts if p)


def _lever(board, req):
    d, err = _get(f"https://api.lever.co/v0/postings/{board}/{req}?mode=json")
    if err:
        return None, err
    return dict(title=d.get("text", ""), body=_lever_body(d),
                location=(d.get("categories") or {}).get("location", ""),
                apply_url=d.get("hostedUrl", "")), None


def _smartrecruiters(board, req):
    d, err = _get(f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{req}")
    if err:
        return None, err
    sections = ((d.get("jobAd") or {}).get("sections") or {})
    body = " ".join(_strip((sections.get(k) or {}).get("text", ""))
                    for k in ("jobDescription", "qualifications", "companyDescription"))
    loc = d.get("location") or {}
    return dict(title=d.get("name", ""), body=body,
                location=f"{loc.get('city','')}, {loc.get('region','')}".strip(", "),
                apply_url=f"https://jobs.smartrecruiters.com/{board}/{req}"), None


def _workday(board, req):
    """board is "tenant:host:site"; req is the employer's jobReqId. The id is
    matched against the board rather than trusted from the caller, because a
    Workday external path changes whenever the title is edited."""
    from workday import find_requisition, job_detail
    try:
        tenant, host, site = board.split(":")
    except ValueError:
        return None, (f'Workday board must be "tenant:host:site", got {board!r}')
    try:
        match = find_requisition(tenant, host, site, req)
    except Exception as e:
        return None, f"{type(e).__name__} searching the {board} board"
    if not match:
        return None, f"requisition {req} not on the {tenant} Workday board"
    try:
        info = job_detail(tenant, host, site, match.get("externalPath", ""))
    except Exception as e:
        return None, f"{type(e).__name__} fetching requisition {req}"
    url = info.get("externalUrl") or (
        f"https://{tenant}.{host}.myworkdayjobs.com/{site}{match.get('externalPath','')}")
    return dict(title=info.get("title") or match.get("title", ""),
                body=_strip(info.get("jobDescription", "")),
                location=info.get("location") or match.get("locationsText", ""),
                company=tenant, apply_url=url), None


ADAPTERS = {"greenhouse": _greenhouse, "ashby": _ashby, "lever": _lever,
            "smartrecruiters": _smartrecruiters, "workday": _workday}

# Posting URLs carry the platform, board and requisition id. Without this, the
# skill's most common entry point -- someone pasting a posting -- had no route
# to the gate that every later stage depends on.
URL_SHAPES = [
    (re.compile(r'(?:job-)?boards\.greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)'
                r'(?:/jobs/|&token=)(\d+)', re.I), "greenhouse"),
    (re.compile(r'jobs\.ashbyhq\.com/([\w-]+)/([0-9a-f-]{36})', re.I), "ashby"),
    (re.compile(r'jobs\.lever\.co/([\w-]+)/([0-9a-f-]{36})', re.I), "lever"),
    (re.compile(r'jobs\.smartrecruiters\.com/([\w-]+)/(\d+)', re.I), "smartrecruiters"),
]


def _workday_from_url(url):
    """Workday posting URLs carry tenant, host, site and the requisition id."""
    from workday import parse_workday_url
    parsed = parse_workday_url(url or "")
    if not parsed:
        return None
    tenant, host, site = parsed
    m = re.search(r'_([A-Za-z0-9-]+)(?:[/?#]|$)', url)
    if not m:
        return None
    return "workday", f"{tenant}:{host}:{site}", m.group(1)


def parse_posting_url(url):
    """Returns (platform, board, requisition_id) or None."""
    wd = _workday_from_url(url)
    if wd:
        return wd
    for pattern, platform in URL_SHAPES:
        m = pattern.search(url or "")
        if m:
            return platform, m.group(1), m.group(2)
    return None


# Sections that follow the requirements and are not requirements. Everything
# from the heading to the end of the posting buried the useful part under EEO
# and benefits boilerplate.
TAIL_HEADING = re.compile(
    r'\n\s*(?:equal\s+(?:employment\s+)?opportunity|eeo\b|we are an equal|benefits\b'
    r'|perks\b|compensation\b|about (?:us|the company)|privacy|accommodations?\b'
    r'|e-?verify|pay (?:range|transparency))', re.I)


def requirements_block(body):
    """The requirements section, bounded at the next non-requirements heading.

    Shown alongside the full body rather than instead of it: the reviewer needs
    this part to judge, and needs to have seen the whole thing for the
    attestation to mean anything."""
    m = REQ_HEADING.search(body)
    start = m.start() if m else 0
    rest = body[start:]
    t = TAIL_HEADING.search(rest)
    return (rest[:t.start()] if t else rest).strip()


def body_fingerprint(body):
    """Attestation is bound to content. If the posting changes between the read
    and the confirmation, the earlier read no longer covers it."""
    normalized = " ".join((body or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


DAYS_WORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

DAYS_RE = re.compile(
    r'(\d|one|two|three|four|five)\s*(?:\+\s*)?days?\s*(?:per|a|/|each)\s*week'
    r'|(?:every\s*weekday|five\s*days\s*a\s*week|daily|full[- ]time\s*in\s*(?:the\s*)?office)',
    re.I)

# Negation has to be checked before the positive patterns, because "this is not
# a fully remote position" contains "fully remote" and read as permission.
NEGATED_REMOTE = re.compile(
    r'(?:not|isn.?t|is\s+not|no)\s+(?:a\s+)?(?:fully\s+|100%\s+|entirely\s+)?remote'
    r'|remote\s+work\s+is\s+not'
    r'|no\s+remote\s+(?:work|option)', re.I)

# A city is an option when the posting offers it as a place to work. A city
# named in prose is just a word: "our Chicago office does not host this team"
# mentions Chicago and offers nothing.
OFFERED_IN_BODY = re.compile(
    r'(?:this\s+(?:role|position)\s+(?:is|will\s+be)\s+(?:based|located)\s+in'
    r'|based\s+out\s+of|located\s+in|office\s+location[s]?\s*:'
    r'|open\s+to\s+candidates\s+in)\s+([A-Z][\w .\'-]{2,40})', re.I)

# "our Denver office" normally does name a workplace. It stops being an offer
# when the sentence takes it away again -- "our Chicago office does not host
# this team" -- so the phrasing counts unless the clause around it is negated.
OFFICE_PHRASE = re.compile(r'(?:our|the)\s+([A-Z][\w .\'-]{2,30}?)\s+office', re.I)
OFFICE_NEGATED = re.compile(
    r'\b(?:not|no|does\s+not|doesn.?t|will\s+not|won.?t|isn.?t|except|other\s+than)\b',
    re.I)

SPLIT_LOCATIONS = re.compile(r'\s*(?:•|\||;|,\s*(?:or|and)\s+|\s+or\s+|/)\s*')


def attendance_days(body):
    """Required office days per week, or None if the posting does not say."""
    m = DAYS_RE.search(body or "")
    if not m:
        return None
    tok = (m.group(1) or "").lower()
    if tok.isdigit():
        return int(tok)
    if tok in DAYS_WORD:
        return DAYS_WORD[tok]
    return 5          # "every weekday", "daily", "full-time in office"


# Two offices joined by "and" is one job in two places. Joined by "or" it is a
# choice. The difference decides whether an excluded city can be avoided, and
# reading both as a choice approved a role that required attending a city the
# user had ruled out.
CONJOINED = re.compile(r'\band\b|\bas well as\b|\bplus\b|\bboth\b', re.I)
ALTERNATIVE = re.compile(r'\bor\b|\beither\b', re.I)

# Wording that frames the whole sentence as a choice, wherever it sits relative
# to the place names. "Choose between A and B" is an offer of one, and reading
# only the words between A and B finds "and" and calls it an obligation.
CHOICE_FRAME = re.compile(
    r'\bchoose\b|\bchoice\b|\byour pick\b|\bwhichever\b|\beither\b'
    r'|\bone of\b|\bany of\b|\bbased (?:in|out of) (?:any|one)\b'
    r'|\bwork from (?:any|one|whichever)\b', re.I)

# Wording that actually mandates attending more than one place. Deliberately
# narrow: it must express an obligation, not merely mention two offices in one
# sentence. "Both of which support this role" is a description, not a demand.
REQUIRE_FRAME = re.compile(
    r'\bsplit (?:your )?time\b|\brotate (?:between|among)\b'
    r'|\bwork (?:from |in |at )?both\b|\bacross both\b'
    r'|\b(?:requires?|must|expected to|will need to)\b[^.]{0,60}\b(?:work\w*|be|attend\w*|present|based|located)\b'
    r'|\ball (?:of )?(?:our|these|the) (?:offices|locations|sites)\b', re.I)


def locations_are_alternatives(body, a, b):
    """True if a and b are offered as a choice, False if both are required,
    None when the posting does not say.

    Judged only within sentences that name both places. Measuring between their
    first occurrences anywhere in the text let unrelated prose decide: "Our
    Chicago office supports engineering and design. Our Boston office supports
    sales. You can be based in our Chicago office or our Boston office." was
    read as a combined obligation, because an "and" about departments sat
    between the two first mentions and outranked the sentence that actually
    offers the choice.
    """
    la, lb = a.lower(), b.lower()
    verdicts = []
    for sentence in re.split(r'(?<=[.!?;])\s+|\n+', body or ""):
        low = sentence.lower()
        if la not in low or lb not in low:
            continue
        # Only positive evidence decides. "and" between two place names proves
        # nothing on its own -- "our Chicago office supports engineering and our
        # Boston office supports sales" describes departments, and reading that
        # as an obligation rejected a perfectly good role. An unproven
        # relationship stays unresolved, where a human settles it.
        ia, ib = low.find(la), low.find(lb)
        between = low[min(ia, ib): max(ia, ib)]
        if CHOICE_FRAME.search(low) or ALTERNATIVE.search(between):
            verdicts.append(True)
        elif REQUIRE_FRAME.search(low):
            verdicts.append(False)
    if not verdicts:
        return None
    # Sentences that disagree are not a basis for a confident answer.
    return verdicts[0] if len(set(verdicts)) == 1 else None


def offered_locations(posting_location, body):
    """Places the posting actually offers as somewhere to work.

    The structured location field is authoritative; boards put the work options
    there. Body text contributes only through phrasings that name a work
    location explicitly, never through a bare city mention.
    """
    out = []
    for part in SPLIT_LOCATIONS.split(posting_location or ""):
        part = part.strip()
        if part:
            out.append(part.lower())
    for m in OFFERED_IN_BODY.finditer(body or ""):
        out.append(m.group(1).strip().lower())
    for m in OFFICE_PHRASE.finditer(body or ""):
        # Look at the sentence this sits in, not the whole posting.
        start = (body or "").rfind(".", 0, m.start()) + 1
        stop = (body or "").find(".", m.end())
        clause = (body or "")[start: stop if stop != -1 else len(body or "")]
        if not OFFICE_NEGATED.search(clause):
            out.append(m.group(1).strip().lower())
    return out


def assess_location(body, posting_location, profile):
    """Returns (verdict, evidence): True / False / None.

    A04 of docs/ACCEPTANCE.md. Four conditions, evaluated in an order that
    reflects which one can override which:

      1. country eligibility
      2. a mandatory obligation to attend an office, and where
      3. how often that attendance is required
      4. remote permission

    Remote wording is considered last and cannot waive an obligation. "We are
    remote-friendly. Work in our Boston office two days per week" is a Boston
    job with a generous tone, and reading the remote clause first approved it
    for someone who had excluded Boston.

    None means unresolved and the gate refuses. Information that is needed to
    decide and is not in the posting stays unknown rather than defaulting.
    """
    loc = (profile or {}).get("location") or {}
    if not profile or not loc:
        return None, ("no location constraints in the profile, so nothing can be "
                      "compared; resolve by hand or complete onboarding")

    accepts_remote = loc.get("remote_ok")
    acceptable = [m.lower() for m in loc.get("acceptable_metros", [])
                  + loc.get("metro_aliases", [])]
    rejects = [r.lower() for r in loc.get("reject_metros", [])]
    country = (loc.get("country") or "").lower()
    days_cap = ((profile or {}).get("constraints") or {}).get("onsite_days_max")

    text = f"{body} {posting_location or ''}"

    # --- 1. country ------------------------------------------------------
    if country:
        other = re.search(
            r'\b(?:must (?:be )?(?:located|based|eligible to work) in|residents? of)\s+'
            r'([A-Z][a-z]+(?: [A-Z][a-z]+)?)', text)
        if other and country not in other.group(1).lower():
            return False, (f'posting requires location in {other.group(1)}, outside the '
                           f'profile country')

    offered = offered_locations(posting_location, body)
    ok_here = [c for c in acceptable if any(c in o for o in offered)]
    bad_here = [r for r in rejects if any(r in o for o in offered)]
    days = attendance_days(body)
    # A stated attendance frequency IS an obligation, whether or not the
    # phrasing matches an ONSITE pattern. "Work in our Boston office two days
    # per week" puts the city between the verb and the noun and spells the
    # number as a word, so the pattern missed it while the frequency parser
    # found it -- and the remote clause earlier in the sentence then won.
    obligation = ONSITE.search(body) or (days is not None)

    def days_verdict(where):
        """Shared tail: an acceptable place, subject to how often.

        A cap of five is not a constraint -- a week has five working days, so
        nothing can exceed it. Treating an unstated frequency as unresolved
        against a cap that cannot be violated blocked roles on a question whose
        answer could not have mattered.
        """
        if days_cap is None or days_cap >= 5:
            note = f'; {days} office day(s) a week' if days is not None else ''
            return True, f'posting offers {where}, which this user accepts{note}'
        if days is None:
            return None, (f'{where} is acceptable, but the posting does not say how many '
                          f'office days are required and this user\'s limit is {days_cap}; '
                          f'find out before applying')
        if days > days_cap:
            return False, (f'{where} is offered, but the role requires {days} office day(s) '
                           f'a week and this user\'s limit is {days_cap}')
        return True, (f'posting offers {where}, which this user accepts; {days} office '
                      f'day(s) a week, within the limit of {days_cap}')

    # --- 2 and 3. a mandatory obligation settles the question ------------
    if obligation:
        om = ONSITE.search(body)
        phrase = (" ".join(om.group(0).split()) if om
                  else f"{days} office day(s) a week")
        if bad_here and not ok_here:
            return False, (f'mandatory attendance ("{phrase}") at {bad_here[0]}, which the '
                           f'profile excludes')
        if ok_here:
            if bad_here:
                # Only a genuine choice lets the user avoid the excluded place.
                field_listed = all(any(c in p.strip().lower() for p in
                                       SPLIT_LOCATIONS.split(posting_location or ""))
                                   for c in (ok_here[0], bad_here[0]))
                rel = True if field_listed else locations_are_alternatives(
                    body, ok_here[0], bad_here[0])
                if rel is False:
                    return False, (f'the role requires attending both {ok_here[0]} and '
                                   f'{bad_here[0]}, and {bad_here[0]} is excluded; this is '
                                   f'not a choice between them')
                if rel is None:
                    return None, (f'the posting names {ok_here[0]} and {bad_here[0]} without '
                                  f'saying whether you pick one or must attend both; '
                                  f'{bad_here[0]} is excluded, so read the posting')
                v, why = days_verdict(ok_here[0])
                return v, (why + f' (also offers {", ".join(bad_here)}, which you exclude '
                                 f'-- say {ok_here[0]} on the application)')
            return days_verdict(ok_here[0])
        if not acceptable:
            return None, (f'mandatory attendance ("{phrase}") found, but the profile lists '
                          f'no acceptable metros to compare against')
        mentioned = [c for c in acceptable if c in text.lower()]
        if mentioned:
            return None, (f'mandatory attendance ("{phrase}"), and {mentioned[0]} appears in '
                          f'the text but is not offered as a work location; read the posting')
        return False, (f'mandatory attendance ("{phrase}") and no acceptable location '
                       f'offered')

    # --- 4. no obligation: remote permission can now apply ---------------
    negated = NEGATED_REMOTE.search(text)
    remote_stated = REMOTE.search(f"{body}\n{posting_location or ''}") and not negated
    if remote_stated and accepts_remote:
        return True, (f'posting states remote work '
                      f'("{" ".join(REMOTE.search(text).group(0).split())}") with no '
                      f'office attendance required')
    if remote_stated and not accepts_remote:
        return None, ("posting is remote but this user does not want remote work; "
                      "confirm whether an office option exists")
    if negated and not ok_here:
        return None, ('posting rules out remote work and offers no location this user '
                      'accepts; read the posting')

    # --- offered locations with no stated obligation ---------------------
    # Same rule as above: an acceptable place alongside an excluded one is only
    # usable if the posting says you may choose.
    if ok_here and bad_here:
        field_listed = all(any(c in p.strip().lower() for p in
                               SPLIT_LOCATIONS.split(posting_location or ""))
                           for c in (ok_here[0], bad_here[0]))
        rel = True if field_listed else locations_are_alternatives(
            body, ok_here[0], bad_here[0])
        if rel is False:
            return False, (f'the posting ties {ok_here[0]} and {bad_here[0]} together, and '
                           f'{bad_here[0]} is excluded')
        if rel is None:
            return None, (f'the posting names {ok_here[0]} and {bad_here[0]} without saying '
                          f'whether you pick one; {bad_here[0]} is excluded, so read it')
    if ok_here:
        return days_verdict(ok_here[0])
    if bad_here:
        return False, (f'the only locations offered include {bad_here[0]}, which the profile '
                       f'excludes, and nowhere this user accepts')
    if offered and acceptable:
        return False, (f'posting offers {", ".join(offered[:3])}, none of which this user '
                       f'accepts')

    return None, ("the posting does not say where the work happens, and nothing in it "
                  "matches the profile's locations; read the posting and resolve by hand")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", choices=sorted(ADAPTERS))
    ap.add_argument("--board")
    ap.add_argument("--req", help="requisition id from the ATS, not the title")
    ap.add_argument("--key", help="re-check an existing record by its key")
    ap.add_argument("--url", help="a posting URL; platform, board and requisition "
                                  "are read from it")
    ap.add_argument("--requirements-reviewed", action="store_true",
                    help="set only after a human or model has actually read the "
                         "requirements printed by a previous run")
    a = ap.parse_args(argv)

    if a.url:
        parsed = parse_posting_url(a.url)
        if not parsed:
            ap.error(
                f"could not read a requisition from {a.url!r}.\n"
                f"Supported: Greenhouse, Ashby, Lever, SmartRecruiters posting URLs.\n"
                "If the posting was pasted as text rather than linked, find it on the "
                "employer's board first -- there is nothing to re-check later without "
                "a requisition id, and a pasted copy cannot be confirmed as still open.")
        a.platform, a.board, a.req = parsed
    if a.key:
        parts = a.key.split("::")
        if len(parts) != 3:
            ap.error("--key must look like platform::board::requisition_id")
        a.platform, a.board, a.req = parts
    if not (a.platform and a.board and a.req):
        ap.error("need --platform, --board and --req (or --url, or --key)")
    if a.platform not in ADAPTERS:
        ap.error(f"no adapter for {a.platform!r}. Supported: {', '.join(sorted(ADAPTERS))}. "
                 "Verify this one by hand and do not record it as checked.")

    key = verification_key(a.platform, a.board, a.req)
    profile = load("profile.json")
    if not profile:
        print("No profile found. Location cannot be judged without the user's "
              "constraints, so this run would record an unresolved location.",
              file=sys.stderr)

    with Timer(f"verify {key}", "10-30s"):
        post, err = ADAPTERS[a.platform](a.board, a.req)
        if err:
            record_attempt_failed(key, err)
            print(f"  FAILED: {err}")
            print("  Any earlier approval for this role has been invalidated.")
            return 1

        body = post["body"]
        if not body.strip():
            record_attempt_failed(key, "posting returned an empty body")
            print("  FAILED: empty posting body")
            return 1

        fingerprint = body_fingerprint(body)
        print(f"  title:    {post['title']}")
        print(f"  location: {post['location'] or '(not stated)'}")

        loc_ok, loc_evidence = assess_location(body, post["location"], profile)
        print(f"  location: {loc_evidence}")

        url_ok, url_evidence = http_ok(post["apply_url"])
        print(f"  apply:    {url_evidence}")

        reviewed = False
        if a.requirements_reviewed:
            prior = load("verified.json").get(key, {})
            seen = prior.get("body_fingerprint")
            if not seen:
                print("\n  REFUSING the attestation: there is no record of this posting "
                      "having been displayed for review.")
                print("  Run this command without --requirements-reviewed first, read the "
                      "requirements it prints, then confirm.")
                return 1
            if seen != fingerprint:
                record_attempt_failed(key, "posting text changed after it was read")
                print(f"\n  REFUSING the attestation: the posting has changed since it was "
                      f"read ({seen} -> {fingerprint}).")
                print("  The earlier review does not cover the current text. Read it again.")
                return 1
            reviewed = True
        else:
            # Both, in this order. The extracted block is what the reviewer needs
            # to judge; the full body is what the fingerprint covers, and showing
            # only an extract would mean attesting to text never displayed.
            block = requirements_block(body)
            print(f"\n  --- REQUIREMENTS ({len(block)} chars) ---")
            print("  " + "\n  ".join(block.splitlines()))
            print(f"\n  --- FULL POSTING ({len(body)} chars) -- this is what your "
                  f"confirmation attests to ---")
            print("  " + "\n  ".join(body.splitlines()))
            print("  --- end ---\n")

        record_verification(
            key, live=True, location_ok=loc_ok, apply_url_ok=url_ok,
            requirements_read=reviewed, apply_url=post["apply_url"],
            title_matched=post["title"], body_fingerprint=fingerprint,
            profile_rev=profile_fingerprint(profile) if profile else None,
            company=post.get("company", ""),
            notes=f"location: {loc_evidence}; {url_evidence}")

        ok = bool(loc_ok) and url_ok and reviewed
        print(f"  recorded. live=True location_ok={loc_ok} apply_url_ok={url_ok} "
              f"requirements_read={reviewed}")
        if not reviewed:
            print("  Gate stays shut until the requirements above are read and this is "
                  "re-run with --requirements-reviewed.")
        if loc_ok is None:
            print("  Gate stays shut: location unresolved. " + loc_evidence)
        elif loc_ok is False:
            print("  Gate stays shut: location fails this user's constraint.")
        if not url_ok:
            print("  Gate stays shut: " + url_evidence)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
