#!/usr/bin/env python3
"""Pull every posting from the boards in companies.json into postings.json.

Boards are authoritative where aggregators are stale, so this is the sweep that
matters. Each posting keeps its platform, board and requisition id, because that
triple is the only stable identity a posting has -- titles repeat and change, and
a package built from a title alone can be built for the wrong role.

Partial results are a trap: a board that returns its first page and then fails
looks exactly like a small board. Failures are counted, named, and reported, and
a sweep that lost boards says so rather than quietly shrinking the market.

Usage:
  sweep_ats.py                 sweep every confirmed board
  sweep_ats.py --only acme     sweep one
"""
import argparse, json, sys, os, re, time, html, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statepath import load, save
from checks import Timer

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return json.load(r)


def _strip(h):
    """Unescape before stripping. Greenhouse returns entity-encoded HTML, so
    stripping first leaves &lt;p&gt; to decode into a visible tag afterwards."""
    text = re.sub(r'<[^>]+>', ' ', html.unescape(h or ""))
    return re.sub(r'[ \t]{2,}', ' ', html.unescape(text)).strip()


def _ts(s):
    """Board date formats vary. An unparseable date is 0, never 'now' -- dating a
    stale posting to today is how a dead role reaches the top of a ranking."""
    if not s:
        return 0
    import datetime
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.datetime.strptime(s[:32], fmt).timestamp()
        except (ValueError, TypeError):
            continue
    if isinstance(s, (int, float)):
        return s / 1000 if s > 1e11 else s
    return 0


def _row(platform, board, company, rid, title, body, location, url, posted):
    return dict(platform=platform, board=board, requisition_id=str(rid),
                companyName=company, title=title, description=body,
                locationRestrictions=[location] if location else [],
                applicationLink=url, pubDate=posted, source="board",
                fetched_at=time.time(),
                minSalary=None, maxSalary=None, salaryPeriod="yearly")


def greenhouse(board, company):
    d = _get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
    return [_row("greenhouse", board, company, j.get("id"), j.get("title", ""),
                 _strip(j.get("content")), (j.get("location") or {}).get("name", ""),
                 j.get("absolute_url", ""), _ts(j.get("updated_at")))
            for j in d.get("jobs", [])]


def ashby(board, company):
    d = _get(f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true")
    out = []
    for j in d.get("jobs", []):
        # isRemote can be true while workplaceType says Hybrid. Keep both; the
        # location gate reads the body anyway.
        loc = f"{j.get('location','')} ({j.get('workplaceType','?')})"
        r = _row("ashby", board, company, j.get("id"), j.get("title", ""),
                 _strip(j.get("descriptionHtml")), loc, j.get("jobUrl", ""),
                 _ts(j.get("publishedAt")))
        comp = (j.get("compensation") or {}).get("compensationTierSummary")
        if comp:
            nums = [int(n.replace(",", "")) for n in re.findall(r'\$([\d,]{4,})', comp)]
            if nums:
                r["minSalary"], r["maxSalary"] = min(nums), max(nums)
        out.append(r)
    return out


def _lever_body(j):
    # Lever splits a posting: the overview sits in descriptionPlain and the
    # requirements live in lists[].content. Reading only the overview drops the
    # qualifications, which is the one section the whole pipeline depends on.
    parts = [_strip(j.get("descriptionPlain") or j.get("description"))]
    for sec in j.get("lists") or []:
        parts.append(_strip(sec.get("text", "")))
        parts.append(_strip(sec.get("content", "")))
    parts.append(_strip(j.get("additionalPlain") or j.get("additional")))
    return "\n".join(p for p in parts if p)


def lever(board, company):
    d = _get(f"https://api.lever.co/v0/postings/{board}?mode=json")
    return [_row("lever", board, company, j.get("id"), j.get("text", ""),
                 _lever_body(j), (j.get("categories") or {}).get("location", ""),
                 j.get("hostedUrl", ""), (j.get("createdAt") or 0) / 1000)
            for j in d]


def _sr_detail(board, rid):
    """The listing endpoint carries no description. Scoring reads the
    requirements block, so a posting with an empty body cannot be scored on
    requirements at all -- it just quietly looks like a role with no demands."""
    try:
        d = _get(f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{rid}")
    except Exception:
        return ""
    sections = ((d.get("jobAd") or {}).get("sections") or {})
    return " ".join(_strip((sections.get(k) or {}).get("text", ""))
                    for k in ("companyDescription", "jobDescription",
                              "qualifications", "additionalInformation"))


def smartrecruiters(board, company, with_bodies=True):
    rows, offset = [], 0
    while True:
        d = _get(f"https://api.smartrecruiters.com/v1/companies/{board}/postings"
                 f"?limit=100&offset={offset}")
        page = d.get("content", [])
        for j in page:
            loc = j.get("location") or {}
            rows.append(_row("smartrecruiters", board, company, j.get("id"),
                             j.get("name", ""), "",
                             f"{loc.get('city','')}, {loc.get('region','')}".strip(", "),
                             f"https://jobs.smartrecruiters.com/{board}/{j.get('id')}",
                             _ts(j.get("releasedDate"))))
        offset += len(page)
        # Trusting one page is how a 705-posting board was reported as 100 and a
        # live role was called gone.
        if len(page) < 100 or offset >= d.get("totalFound", 0):
            break

    if with_bodies and rows:
        with ThreadPoolExecutor(max_workers=8) as pool:
            bodies = pool.map(lambda r: _sr_detail(board, r["requisition_id"]), rows)
            for row, body in zip(rows, bodies):
                row["description"] = body
        empty = sum(1 for r in rows if not r["description"].strip())
        if empty:
            print(f"  !! {empty}/{len(rows)} SmartRecruiters postings returned no body; "
                  f"their requirements cannot be scored", file=sys.stderr)
    return rows


def workday(board, company, with_bodies=True):
    """board is "tenant:host:site". Bodies need one request per posting, so a
    large board is slow -- the caller is told the count before it starts."""
    from workday import list_all, job_detail, requisition_id, posting_location
    tenant, host, site = board.split(":")
    rows = []
    probe = __import__("workday").probe(tenant, host, site) or 0
    if probe:
        pages = (probe + 19) // 20
        print(f"  {company}: {probe} postings on Workday, ~{pages} requests to list"
              + (f" plus {probe} for requirement text" if with_bodies else ""),
              file=sys.stderr)
    postings = list_all(tenant, host, site)
    for j in postings:
        rid = requisition_id(j)
        if not rid:
            continue
        rows.append(_row("workday", board, company, rid, j.get("title", ""), "",
                         posting_location(j),
                         f"https://{tenant}.{host}.myworkdayjobs.com/{site}"
                         f"{j.get('externalPath','')}",
                         _ts(j.get("postedOn"))))
        rows[-1]["_external_path"] = j.get("externalPath", "")

    if with_bodies and rows:
        def body(r):
            try:
                return _strip(job_detail(tenant, host, site,
                                         r["_external_path"]).get("jobDescription", ""))
            except Exception:
                return ""
        with ThreadPoolExecutor(max_workers=6) as pool:
            for r, b in zip(rows, pool.map(body, rows)):
                r["description"] = b
        empty = sum(1 for r in rows if not r["description"].strip())
        if empty:
            print(f"  !! {empty}/{len(rows)} Workday postings returned no body; their "
                  f"requirements cannot be scored", file=sys.stderr)
    for r in rows:
        r.pop("_external_path", None)
    return rows


FETCHERS = {"greenhouse": greenhouse, "ashby": ashby, "lever": lever,
            "smartrecruiters": smartrecruiters, "workday": workday}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="sweep a single company name")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)

    companies = load("companies.json")
    targets = [(n, r) for n, r in companies.items()
               if r.get("confirmed") and (not a.only or n == a.only)]
    if not targets:
        raise SystemExit("No confirmed boards. Run resolve_ats.py first.")

    rows, failed = [], []

    def one(item):
        name, rec = item
        fetch = FETCHERS.get(rec["platform"])
        if not fetch:
            return name, None, f"no fetcher for {rec['platform']}"
        try:
            return name, fetch(rec["board"], name), None
        except Exception as e:
            return name, None, f"{type(e).__name__}: {e}"

    with Timer(f"sweep {len(targets)} boards", f"~{max(5, len(targets) * 2)}s"):
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            for name, got, err in pool.map(one, targets):
                if err:
                    failed.append((name, err))
                else:
                    rows.extend(got)

    # Overwriting good data with a half-finished sweep loses more than it gains.
    if failed and not rows:
        print(f"\n  EVERY board failed ({len(failed)}). Keeping the previous "
              f"postings.json rather than replacing it with nothing.", file=sys.stderr)
        for n, e in failed:
            print(f"    {n}: {e}", file=sys.stderr)
        return 1

    save("postings.json", rows)
    print(f"\n  {len(rows)} postings from {len(targets) - len(failed)} boards",
          file=sys.stderr)
    if failed:
        print(f"  !! {len(failed)} board(s) FAILED. This sweep is incomplete and any "
              f"ranking from it is missing these employers:", file=sys.stderr)
        for n, e in failed:
            print(f"     {n}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
