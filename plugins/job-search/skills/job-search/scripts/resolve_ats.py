#!/usr/bin/env python3
"""Work out which applicant tracking system a company uses, and its board slug.

Boards are the only place a posting is authoritative. Aggregators go stale within
days; the board is what the employer is actually running. To read a board you need
two facts -- the platform and the slug -- and neither is published anywhere.

The approach is to guess the slug from the company name, then confirm by actually
fetching the board. A guess that returns postings is right; one that 404s is not.
Confirmed guesses are cached in companies.json so this runs once per employer.

Usage:
  resolve_ats.py "Northstar Health" "Beacon Labs"
  resolve_ats.py --from-postings        resolve every employer in postings.json
  resolve_ats.py --list                 show what is already resolved
"""
import argparse, difflib, json, re, sys, os, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statepath import load, save
from checks import Timer

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

PROBES = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                   lambda d: d.get("jobs")),
    "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{slug}",
              lambda d: d.get("jobs")),
    "lever": ("https://api.lever.co/v0/postings/{slug}?mode=json",
              lambda d: d if isinstance(d, list) else None),
    "smartrecruiters": ("https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1",
                        lambda d: d.get("content")),
}


def slug_candidates(name):
    """Companies pick their slug casually. Cover the common shapes."""
    base = re.sub(r'[^a-z0-9 ]', '', name.lower()).strip()
    words = base.split()
    joined = "".join(words)
    out = [joined, "-".join(words)]
    # Many drop a trailing legal or generic suffix
    generic = {"inc", "llc", "corp", "corporation", "co", "group", "labs",
               "technologies", "technology", "health", "software", "systems"}
    trimmed = [w for w in words if w not in generic]
    if trimmed and trimmed != words:
        out += ["".join(trimmed), "-".join(trimmed)]
    if words:
        out.append(words[0])
    seen, uniq = set(), []
    for s in out:
        if s and s not in seen:
            seen.add(s); uniq.append(s)
    return uniq


def board_owner(platform, slug):
    """Ask the board who it belongs to.

    A slug guess that returns postings proves a board exists, not that it is the
    right company's. "Beacon Labs" guessed down to "beacon" will happily match an
    unrelated employer's board, and every posting on it then gets labelled with
    the name we were looking for.
    """
    try:
        if platform == "greenhouse":
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://boards-api.greenhouse.io/v1/boards/{slug}",
                    headers=UA), timeout=15) as r:
                return json.load(r).get("name")
        if platform == "lever":
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=1",
                    headers=UA), timeout=15) as r:
                rows = json.load(r)
                if rows:
                    return (rows[0].get("categories") or {}).get("team")
        if platform == "ashby":
            # Ashby's posting API publishes no owner name, so the public board
            # page is the only corroboration available. Without this, every
            # Ashby employer stayed a candidate and was silently dropped from
            # sweeps -- an entire platform invisible to the search.
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://jobs.ashbyhq.com/{slug}", headers=UA), timeout=20) as r:
                page = r.read().decode("utf-8", "replace")
            m = re.search(r'<title[^>]*>([^<]{1,120})</title>', page, re.I)
            if m:
                return re.sub(r'\s+(jobs|careers)\s*$', '', m.group(1).strip(), flags=re.I)
        if platform == "smartrecruiters":
            with urllib.request.urlopen(urllib.request.Request(
                    f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1",
                    headers=UA), timeout=15) as r:
                rows = json.load(r).get("content") or []
                if rows:
                    return (rows[0].get("company") or {}).get("name")
    except Exception:
        return None
    return None


def names_agree(requested, found):
    """Lenient on formatting, strict on identity."""
    if not found:
        return None          # no evidence either way
    norm = lambda x: re.sub(r'[^a-z0-9]', '', x.lower())
    a, b = norm(requested), norm(found)
    if not a or not b:
        return None
    # Containment is only evidence in one direction. A board owned by
    # "Figma, Inc." covering a request for "Figma" is the same company written
    # formally. A board owned by "Notion" answering a request for "Notion Health
    # Systems" is a different company that happens to share a first word, and
    # that is precisely the guess this check exists to reject.
    if a in b:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def probe(platform, slug):
    url, extract = PROBES[platform]
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url.format(slug=slug), headers=UA), timeout=15) as r:
            jobs = extract(json.load(r))
            return len(jobs) if jobs else 0
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def register_from_url(name, url):
    """Record a board the user pointed at directly.

    Automated discovery is biased towards employers whose boards are guessable
    from their name, which in practice means technology companies. For everyone
    else this is the path that works, so it is a documented first-class entry
    rather than a fallback: the user pastes the careers or posting URL and the
    board is registered from it.
    """
    from workday import parse_workday_url
    wd = parse_workday_url(url)
    if wd:
        tenant, host, site = wd
        n = probe_workday(tenant, host, site)
        if not n:
            return None, f"no Workday board at {tenant}:{host}:{site}"
        return dict(platform="workday", board=f"{tenant}:{host}:{site}",
                    postings_seen=n, board_owner=tenant, confirmed=True,
                    evidence=f"registered from a URL the user supplied: {url}"), None

    shapes = [
        (re.compile(r'(?:job-)?boards\.greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)', re.I),
         "greenhouse"),
        (re.compile(r'jobs\.ashbyhq\.com/([\w-]+)', re.I), "ashby"),
        (re.compile(r'jobs\.lever\.co/([\w-]+)', re.I), "lever"),
        (re.compile(r'jobs\.smartrecruiters\.com/([\w-]+)', re.I), "smartrecruiters"),
    ]
    for pattern, platform in shapes:
        m = pattern.search(url or "")
        if not m:
            continue
        slug = m.group(1)
        n = probe(platform, slug)
        if not n:
            return None, f"no {platform} board at {slug!r}"
        return dict(platform=platform, board=slug, postings_seen=n,
                    board_owner=slug, confirmed=True,
                    evidence=f"registered from a URL the user supplied: {url}"), None

    return None, ("that URL is not a board on a supported platform "
                  "(Greenhouse, Ashby, Lever, SmartRecruiters, Workday). "
                  "Supported platforms are listed in the README.")


def probe_workday(tenant, host, site):
    from workday import probe as wprobe
    return wprobe(tenant, host, site)


def resolve_workday(name):
    """Workday boards are addressed by tenant, datacentre and site. A guessed
    tenant is only a candidate: the tenant string is the employer's own
    identifier, so it corroborates the name or it does not."""
    from workday import discover, discover_from_careers

    # The careers page first: it yields the employer's real site name, which
    # cannot be guessed because each employer invents one.
    found = discover_from_careers(name)
    if found:
        tenant, host, site, src = found
        n = probe_workday(tenant, host, site)
        if n:
            return dict(platform="workday", board=f"{tenant}:{host}:{site}",
                        postings_seen=n, board_owner=tenant, confirmed=True,
                        evidence=f"board linked from {src}")

    for tenant in slug_candidates(name):
        found = discover(tenant)
        if not found:
            continue
        host, site, total = found
        agree = names_agree(name, tenant)
        rec = dict(platform="workday", board=f"{tenant}:{host}:{site}",
                   postings_seen=total, board_owner=tenant, confirmed=bool(agree))
        rec["evidence" if agree else "note"] = (
            f"Workday tenant {tenant!r} matches the employer name" if agree else
            f"Workday board found at tenant {tenant!r}, which does not match {name!r}")
        return rec
    return None


def resolve(name):
    """Returns the best match found. `confirmed` is only true when the board
    itself corroborates the employer name; everything else stays a candidate
    that a human has to approve."""
    best = None
    wd = resolve_workday(name)
    if wd and wd.get("confirmed"):
        return wd
    best = wd or None
    for slug in slug_candidates(name):
        for platform in PROBES:
            n = probe(platform, slug)
            if not n:
                continue
            owner = board_owner(platform, slug)
            agree = names_agree(name, owner)
            rec = dict(platform=platform, board=slug, postings_seen=n,
                       board_owner=owner, confirmed=bool(agree))
            if agree:
                rec["evidence"] = f"board identifies itself as {owner!r}"
                return rec
            rec["note"] = (
                f"board exists but identifies itself as {owner!r}, which does not "
                f"match {name!r}" if owner else
                "board exists but publishes no owner name to corroborate it")
            best = best or rec
    return best


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("companies", nargs="*")
    ap.add_argument("--from-postings", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--recheck", action="store_true", help="re-probe already-resolved names")
    ap.add_argument("--url", help="register a board from a careers or posting URL; "
                                  "the reliable path when name guessing fails")
    ap.add_argument("--company", help="employer name to file a --url registration under")
    a = ap.parse_args(argv)

    known = load("companies.json")

    if a.list:
        if not known:
            print("Nothing resolved yet.")
        for name, rec in sorted(known.items()):
            status = f"{rec['platform']}::{rec['board']}" if rec.get("confirmed") else "UNRESOLVED"
            print(f"  {name:38} {status}")
        return 0

    if a.url:
        label = a.company or (a.companies[0] if a.companies else None)
        if not label:
            ap.error("--url needs --company to say which employer it belongs to")
        rec, err = register_from_url(label, a.url)
        if err:
            print(f"  {label}: {err}")
            return 1
        known[label] = rec
        save("companies.json", known)
        print(f"  {label:38} {rec['platform']}::{rec['board']} "
              f"({rec['postings_seen']} postings, registered from URL)")
        return 0

    names = list(a.companies)
    if a.from_postings:
        names += sorted({(p.get("companyName") or "").strip()
                         for p in load("postings.json", []) if p.get("companyName")})
    names = [n for n in dict.fromkeys(names) if n]
    if not names:
        ap.error("give one or more company names, or --from-postings")

    todo = [n for n in names if a.recheck or n not in known or not known[n].get("confirmed")]
    print(f"{len(names)} requested, {len(names) - len(todo)} already resolved, "
          f"{len(todo)} to probe", file=sys.stderr)

    found = 0
    with Timer("resolve boards", f"~{max(1, len(todo) * 3)}s"):
        for name in todo:
            rec = resolve(name)
            if rec and rec.get("confirmed"):
                known[name] = rec
                found += 1
                print(f"  {name:38} {rec['platform']}::{rec['board']} "
                      f"({rec['postings_seen']} postings)")
            elif rec:
                known[name] = rec
                print(f"  {name:38} CANDIDATE {rec['platform']}::{rec['board']} "
                      f"-- {rec['note']}")
            else:
                known[name] = dict(confirmed=False,
                                   note="no board found by name guessing")
                print(f"  {name:38} not found. Find the careers page by hand and add "
                      f"the slug to companies.json.")

    save("companies.json", known)
    candidates = [n for n in todo if known.get(n, {}).get("board")
                  and not known[n].get("confirmed")]
    print(f"\n  confirmed {found}/{len(todo)}.", file=sys.stderr)
    if candidates:
        print(f"  {len(candidates)} candidate board(s) found but NOT confirmed as belonging "
              f"to the employer asked for. They are excluded from sweeps until someone "
              f"checks the careers page and sets confirmed: true:", file=sys.stderr)
        for n in candidates[:8]:
            print(f"     {n} -> {known[n]['platform']}::{known[n]['board']}", file=sys.stderr)
    print(f"  Unresolved employers are not a failure of the search -- they just need "
          f"their slug added by hand.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
