#!/usr/bin/env python3
"""A04 — location constraints compose.

Acceptance contract: docs/ACCEPTANCE.md v1.

Remote permission, mandatory office attendance, country eligibility and an
office-day ceiling are four separate conditions. A posting satisfying one of
them has not thereby satisfied the others, and "remote-friendly" is marketing
copy that cannot waive a mandatory office. Information needed to decide and
not present stays unresolved.

No network. Run: python3 tests/test_location.py
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("JOB_SEARCH_STATE", "/tmp/_loc_test_state")
from verify_one import assess_location

CHI = {"location": {"remote_ok": True, "acceptable_metros": ["chicago"],
                    "reject_metros": ["boston"], "country": "united states"},
       "constraints": {"onsite_days_max": 2}}
CHI_NOCAP = {"location": CHI["location"], "constraints": {}}
CHI_STRICT = {"location": CHI["location"], "constraints": {"onsite_days_max": 0}}

passed, failed = [], []


def case(label, body, loc, profile, want):
    v, ev = assess_location(body, loc, profile)
    ok = v is want
    (passed if ok else failed).append(label)
    print(f"  {'ok  ' if ok else 'FAIL'}  {label:52} -> {str(v):5} (want {want})")
    if not ok:
        print(f"        {ev[:100]}")


print("\nremote wording cannot waive a mandatory office")
case("remote-friendly plus mandatory excluded office",
     "We are remote-friendly. Work in our Boston office two days per week.", "", CHI, False)
case("remote-friendly plus mandatory acceptable office",
     "We are remote-friendly. Work in our Chicago office two days per week.", "", CHI, True)
case("genuinely remote, no obligation",
     "This is a fully remote role.", "", CHI, True)
case("negated remote is not permission",
     "This is not a fully remote position.", "", CHI, None)

print("\nattendance frequency is its own condition")
case("office days over the cap, acceptable city",
     "Based in our Chicago office. Four days per week in office.", "", CHI, False)
case("office days within the cap, acceptable city",
     "Based in our Chicago office. Two days per week in office.", "", CHI, True)
case("unknown frequency with a finite cap stays unresolved",
     "This is a hybrid role in our Chicago office.", "", CHI, None)
case("unknown frequency with no cap is acceptable",
     "This is a hybrid role in our Chicago office.", "", CHI_NOCAP, True)
# A cap of five cannot be exceeded, so an unstated frequency cannot matter.
CHI_CAP5 = {"location": CHI["location"], "constraints": {"onsite_days_max": 5}}
case("unknown frequency against a cap that cannot be exceeded",
     "This is a hybrid role in our Chicago office.", "", CHI_CAP5, True)
case("a five-day cap still accepts a stated five days",
     "Based in our Chicago office. Five days a week in office.", "", CHI_CAP5, True)
case("any office day at all when the cap is zero",
     "Based in our Chicago office. One day per week in office.", "", CHI_STRICT, False)

print("\nmentions, negation and multiple required places")
case("acceptable city mentioned but not offered",
     "Work in the office every weekday in Boston. Our Chicago office does not host "
     "this team.", "", CHI, None)
# A04 requires unknown-but-needed information to stay unresolved. A user who
# caps office days cannot be told a multi-city posting clears that cap when the
# posting never states an arrangement. The cost is more unresolved results for
# users who set a cap, which is the honest outcome rather than a cheerful guess.
case("cities offered, attendance unstated, user has a cap", "",
     "Chicago, IL | Boston, MA", CHI, None)
case("cities offered, attendance unstated, user has no cap", "",
     "Chicago, IL | Boston, MA", CHI_NOCAP, True)
case("offered alternatives, none acceptable", "",
     "Boston, MA | Austin, TX", CHI, False)

print("\ncountry eligibility is separate from remote")
case("remote but country-restricted",
     "Fully remote role. Candidates must be located in Canada.", "", CHI, False)

print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
