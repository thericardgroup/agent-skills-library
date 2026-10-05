#!/usr/bin/env python3
"""Workday adapter.

A08 of docs/ACCEPTANCE.md, owner-approved scope exception SE-1.

Workday is where most large non-technology employers post: hospitals, health
systems, universities, government, retail, logistics, insurance. Without it a
measurement across five sectors reached 6/6 technology employers and 1/24
everywhere else, which made this a technology job-search tool wearing a general
name.

Three facts identify a Workday board: the tenant, the datacentre host (wdN) and
the site name. All three appear in the employer's careers URL, which is the
reliable way to get them. Guessing works often enough to be worth trying and
never well enough to trust on its own, so a guessed board stays a candidate
until its tenant corroborates the employer name.

  list:   POST /wday/cxs/{tenant}/{site}/jobs
  detail: GET  /wday/cxs/{tenant}/{site}{externalPath}
"""
import json, re, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
JSON_HDRS = dict(UA, **{"Content-Type": "application/json", "Accept": "application/json"})

HOSTS = ("wd1", "wd2", "wd3", "wd5", "wd10", "wd12", "wd103")

URL_RE = re.compile(
    r'https?://(?P<tenant>[\w-]+)\.(?P<host>wd\d+)\.myworkdayjobs\.com'
    r'(?:/\w{2}-\w{2})?/(?P<site>[\w-]+)', re.I)


def parse_workday_url(url):
    """tenant, host, site from a careers or posting URL. The dependable path."""
    m = URL_RE.search(url or "")
    if not m:
        return None
    site = m.group("site")
    if site.lower() in ("wday", "job"):
        return None
    return m.group("tenant"), m.group("host"), site


def site_candidates(tenant):
    t = tenant.strip()
    return [
        "External", "Careers", "External_Career_Site", "ExternalCareerSite",
        f"{t.upper()}ExternalCareerSite", f"{t.capitalize()}ExternalCareerSite",
        f"{t}_Careers", f"{t.capitalize()}_Careers", f"{t.capitalize()}Careers",
        "External_Careers", "CareerSite", "careers", "jobs",
    ]


def _post(url, body, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=JSON_HDRS, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=JSON_HDRS),
                                timeout=timeout) as r:
        return json.load(r)


def base(tenant, host, site):
    return f"https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"


def probe(tenant, host, site):
    """Returns the posting count, or None when this combination is not a board."""
    try:
        d = _post(f"{base(tenant, host, site)}/jobs",
                  {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
        return d.get("total")
    except Exception:
        return None


BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

BOARD_RE = re.compile(r'([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[\w-]{2,5}/)?([\w-]+)', re.I)


def careers_urls(company):
    """Plausible careers pages for an employer name. Deliberately few: this is
    a cheap attempt before asking the user, not a crawler."""
    base = re.sub(r'[^a-z0-9 ]', '', company.lower()).split()
    generic = {"inc", "llc", "corp", "the", "of", "university", "health",
               "system", "systems", "group", "company"}
    stems = [s for s in dict.fromkeys(
        ["".join(base), "".join(w for w in base if w not in generic),
         base[0] if base else ""]) if s]
    out = []
    for stem in stems:
        for tld in (".com", ".org", ".edu"):
            out += [f"https://careers.{stem}{tld}", f"https://www.{stem}{tld}/careers",
                    f"https://jobs.{stem}{tld}"]
    return out[:12]


def discover_from_careers(company, timeout=12):
    """Look for a Workday board linked from the employer's careers page.

    Succeeds when the link is in the served HTML. Many large employers render
    their careers page entirely in JavaScript, so the board only exists after
    the page runs -- nothing static can see it, and that is the usual reason
    this returns nothing rather than the employer not using Workday.
    """
    for url in careers_urls(company):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=BROWSER), timeout=timeout) as r:
                final, html = r.geturl(), r.read(500000).decode("utf-8", "replace")
        except Exception:
            continue
        m = BOARD_RE.search(final) or BOARD_RE.search(html)
        if m:
            return m.group(1), m.group(2), m.group(3), url
    return None


def discover(tenant, hosts=HOSTS, workers=12):
    """Find a working (host, site) for a tenant. Best effort, never conclusive."""
    combos = [(h, s) for h in hosts for s in site_candidates(tenant)]

    def one(c):
        h, s = c
        n = probe(tenant, h, s)
        return (h, s, n) if n else None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(one, combos):
            if res:
                return res
    return None


PAGE = 20          # Workday rejects anything larger with HTTP 400


def list_jobs(tenant, host, site, limit=PAGE, cap=4000, progress=None):
    """Every posting on the board, or `cap` of them.

    Workday caps a page at 20, so a 2,000-posting board is 100 requests. That
    is slow enough that the caller must be able to say so before starting
    rather than appearing to hang.
    """
    limit = min(limit, PAGE)
    out, offset, total = [], 0, None
    while offset < cap:
        d = _post(f"{base(tenant, host, site)}/jobs",
                  {"appliedFacets": {}, "limit": limit, "offset": offset,
                   "searchText": ""})
        page = d.get("jobPostings") or []
        out.extend(page)
        # Workday reports the total on the first page and zero on every page
        # after it. Re-reading it each time ends the loop at page two and
        # reports a 2,000-posting board as 40.
        if total is None:
            total = d.get("total") or 0
        offset += len(page)
        if progress:
            progress(len(out), total)
        if not page or (total and offset >= total) or len(page) < limit:
            break
    return out, total


def list_all(tenant, host, site, **kw):
    """Just the postings, for callers that do not need the reported total."""
    rows, _ = list_jobs(tenant, host, site, **kw)
    return rows


def find_requisition(tenant, host, site, req):
    """Locate one posting by requisition id in a single request.

    Paging an entire board to verify one role made verification cost as much as
    a sweep -- 100 requests against a 2,000-posting employer. Workday's own
    search matches the requisition id, so the targeted lookup is one call.
    """
    d = _post(f"{base(tenant, host, site)}/jobs",
              {"appliedFacets": {}, "limit": PAGE, "offset": 0, "searchText": str(req)})
    for j in d.get("jobPostings") or []:
        if str(requisition_id(j)) == str(req):
            return j
    return None


def job_detail(tenant, host, site, external_path):
    d = _get(f"{base(tenant, host, site)}{external_path}")
    return d.get("jobPostingInfo") or {}


def posting_location(posting):
    """Where a listed posting is, across the shapes tenants actually return.

    Workday's list response is not uniform. One tenant returns locationsText
    and a single bulletField holding the requisition id; another omits
    locationsText entirely and puts [location, id, title] in bulletFields. The
    externalPath carries the location in its /job/<Location>/ segment in every
    case seen, so it is the fallback. Getting this wrong is not cosmetic: an
    empty location means the location gate has nothing to judge and every role
    on the board becomes unresolved.
    """
    text = (posting.get("locationsText") or "").strip()
    if text:
        return text
    path = posting.get("externalPath") or ""
    m = re.match(r'/job/([^/]+)/', path)
    if m:
        return urllib.parse.unquote(m.group(1)).replace("-", " ").strip()
    rid = str(requisition_id(posting) or "")
    for b in posting.get("bulletFields") or []:
        if str(b) != rid and not re.fullmatch(r'[A-Z]{0,3}\d{4,}[-\d]*', str(b)):
            return str(b)
    return ""


def requisition_id(posting_or_info):
    """jobReqId is the employer's own stable id; externalPath is a slug that
    changes when the title is edited."""
    return (posting_or_info.get("jobReqId")
            or (posting_or_info.get("externalPath") or "").rsplit("_", 1)[-1] or None)
