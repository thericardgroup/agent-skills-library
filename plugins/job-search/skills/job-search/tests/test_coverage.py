#!/usr/bin/env python3
"""A08 — an empty result says what it is a statement about.

Acceptance contract: docs/ACCEPTANCE.md v1.

No network. Run: python3 tests/test_coverage.py
"""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ["JOB_SEARCH_STATE"] = tempfile.mkdtemp()
from statepath import save
from coverage import summarize, render

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


print("\nnothing searched at all")
save("companies.json", {n: {"confirmed": False, "note": "no board found"}
                        for n in ["Tampa General", "AdventHealth", "BayCare"]})
save("postings.json", [])
s = summarize(); out = render(s)
check("unreachable employers are counted", s["unreachable"] == 3)
check("an empty result is labelled as coverage, not absence",
      "statement about coverage" in out)
check("the unsupported platforms are named", "Taleo" in out)
check("the user is told the workaround", "copy the URL" in out)
check("it does not claim no jobs exist", "no jobs" not in out.lower())

print("\na partial search")
save("companies.json", {
    "Reachable Co": {"confirmed": True, "platform": "greenhouse", "board": "reachable"},
    "Guessed Co": {"confirmed": False, "platform": "lever", "board": "guessed"},
    "Opaque Co": {"confirmed": False, "note": "no board found"}})
save("postings.json", [
    dict(platform="greenhouse", board="reachable", requisition_id="1",
         companyName="Reachable Co", title="Analyst", description="Requirements: things."),
    dict(platform="greenhouse", board="reachable", requisition_id="2",
         companyName="Reachable Co", title="Analyst II", description="")])
s = summarize(); out = render(s)
check("confirmed, candidate and unreachable are separated",
      (s["confirmed"], s["candidates"], s["unreachable"]) == (1, 1, 1),
      str((s["confirmed"], s["candidates"], s["unreachable"])))
check("postings without requirement text are flagged",
      s["postings_without_requirements"] == 1 and "could not be scored" in out)
check("the platform breakdown is reported", s["by_platform"].get("greenhouse") == 2)
check("a partial search is not described as nothing searched",
      "Nothing was searched" not in out)

print("\nbefore anything has been resolved")
save("companies.json", {})
save("postings.json", [])
check("an unstarted search says so rather than reporting zero coverage",
      "no coverage to report" in render(summarize()))

print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
