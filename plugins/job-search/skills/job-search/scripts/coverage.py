#!/usr/bin/env python3
"""What the search could and could not see.

A08 of docs/ACCEPTANCE.md. A profile can be correct, the filters can all work,
and the result can still be empty because none of the user's employers are on a
platform this skill can read. Reported as "0 roles found", that looks like a
verdict on the person. It is a statement about coverage.

A measurement across 30 employers in five sectors reached 6/6 in technology and
1/24 everywhere else, so for most users outside software this is the dominant
fact about their search and it has to be said out loud.

Usage:
  coverage.py            report on the current state
  coverage.py --json
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from statepath import load

SUPPORTED = ("greenhouse", "ashby", "lever", "smartrecruiters", "workday")
UNSUPPORTED_HINT = ("Taleo", "iCIMS", "SuccessFactors", "a custom careers site")


def summarize():
    companies = load("companies.json") or {}
    postings = load("postings.json", []) or []

    confirmed = {n: r for n, r in companies.items() if r.get("confirmed")}
    candidates = {n: r for n, r in companies.items()
                  if r.get("board") and not r.get("confirmed")}
    unreachable = {n: r for n, r in companies.items()
                   if not r.get("board")}

    by_platform, by_employer, bodyless = {}, {}, 0
    for p in postings:
        by_platform[p.get("platform", "?")] = by_platform.get(p.get("platform", "?"), 0) + 1
        co = (p.get("companyName") or "?").strip()
        by_employer[co] = by_employer.get(co, 0) + 1
        if not (p.get("description") or "").strip():
            bodyless += 1

    return dict(
        asked=len(companies), confirmed=len(confirmed), candidates=len(candidates),
        unreachable=len(unreachable), postings=len(postings),
        by_platform=by_platform, employers_with_postings=len(by_employer),
        postings_without_requirements=bodyless,
        candidate_names=sorted(candidates), unreachable_names=sorted(unreachable))


def render(s):
    L = []
    if not s["asked"]:
        return ("No employers have been resolved yet, so there is no coverage to report. "
                "Nothing here says anything about what exists.")

    L.append(f"Employers asked about: {s['asked']}")
    L.append(f"  reachable and searched:  {s['confirmed']}")
    if s["candidates"]:
        L.append(f"  found but unconfirmed:   {s['candidates']}  "
                 f"({', '.join(s['candidate_names'][:3])}" +
                 (", ..." if s["candidates"] > 3 else "") + ")")
    if s["unreachable"]:
        L.append(f"  not reachable:           {s['unreachable']}  "
                 f"({', '.join(s['unreachable_names'][:3])}" +
                 (", ..." if s["unreachable"] > 3 else "") + ")")
    L.append("")
    L.append(f"Postings read: {s['postings']} across {s['employers_with_postings']} employer(s)")
    for plat, n in sorted(s["by_platform"].items(), key=lambda x: -x[1]):
        L.append(f"  {n:>6}  {plat}")
    if s["postings_without_requirements"]:
        L.append(f"  !! {s['postings_without_requirements']} posting(s) had no requirement "
                 f"text, so they could not be scored on requirements")

    if s["unreachable"]:
        L.append("")
        L.append(f"The {s['unreachable']} employer(s) above could not be searched. That is "
                 f"usually not because they are not hiring -- it is because their job board "
                 f"runs on something this skill cannot read "
                 f"({', '.join(UNSUPPORTED_HINT[:3])}, or similar).")
        L.append("You can still search them: open their careers page, copy the URL, and "
                 "register it directly. Everything downstream works the same.")

    if s["confirmed"] == 0:
        L.append("")
        L.append("**Nothing was searched.** An empty result here is a statement about "
                 "coverage, not about whether suitable roles exist.")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    s = summarize()
    print(json.dumps(s, indent=1) if a.json else render(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
