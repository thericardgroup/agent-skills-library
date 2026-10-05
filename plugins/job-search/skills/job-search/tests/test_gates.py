#!/usr/bin/env python3
"""The gate must fail closed. These are the mechanisms that were broken once.

No network. Run: python3 tests/test_gates.py
"""
import os, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
os.environ["JOB_SEARCH_STATE"] = tempfile.mkdtemp()

from checks import (record_verification, record_attempt_failed, verification_gate,
                    verification_key, GateLog)
from verify_one import assess_location

passed, failed = [], []


def check(name, cond):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")


print("\nverification gate")
k = verification_key("greenhouse", "acme", "4056789")
record_verification(k, live=True, location_ok=True, requirements_read=True,
                    apply_url_ok=True, apply_url="https://x", title_matched="PM")
check("a complete verification opens the gate", verification_gate(k)[0] is True)

record_attempt_failed(k, "board unreachable")
check("a failed recheck invalidates the earlier success", verification_gate(k)[0] is False)

k2 = verification_key("greenhouse", "acme", "999")
record_verification(k2, live=True, location_ok=True, requirements_read=False,
                    apply_url_ok=True, apply_url="https://x", title_matched="PM")
check("unread requirements keep the gate shut", verification_gate(k2)[0] is False)

k3 = verification_key("greenhouse", "acme", "111")
k4 = verification_key("greenhouse", "acme", "222")
record_verification(k3, live=True, location_ok=True, requirements_read=True,
                    apply_url_ok=True, apply_url="https://a", title_matched="Product Manager")
check("same title, different requisition, is not certified",
      verification_gate(k4)[0] is False)

check("an unverified key is refused", verification_gate("greenhouse::x::nope")[0] is False)

try:
    verification_key("greenhouse", "acme", "")
    check("a missing requisition id is rejected", False)
except ValueError:
    check("a missing requisition id is rejected", True)


k5 = verification_key("greenhouse", "acme", "555")
record_verification(k5, live=True, location_ok=True, requirements_read=True,
                    apply_url_ok=False, apply_url="", title_matched="PM")
check("a dead apply link keeps the gate shut", verification_gate(k5)[0] is False)

import time as _t
k6 = verification_key("greenhouse", "acme", "666")
record_verification(k6, live=True, location_ok=True, requirements_read=True,
                    apply_url_ok=True, apply_url="https://x", title_matched="PM")
_d = __import__("statepath").load("verified.json")
_d[k6]["checked_at"] = _t.time() - 5 * 86400
__import__("statepath").save("verified.json", _d)
check("a stale record is refused", verification_gate(k6)[0] is False)


print("\napproval is bound to the profile it was made against")
from checks import profile_fingerprint
_p = {"location": {"remote_ok": True, "acceptable_metros": ["chicago"]},
      "constraints": {"onsite_days_max": 2}}
k7 = verification_key("greenhouse", "acme", "777")
record_verification(k7, live=True, location_ok=True, requirements_read=True,
                    apply_url_ok=True, apply_url="https://x", title_matched="PM",
                    profile_rev=profile_fingerprint(_p))
check("unchanged profile keeps the approval", verification_gate(k7, _p)[0] is True)
_changed = {**_p, "location": {**_p["location"], "remote_ok": False}}
check("refusing remote afterwards invalidates it",
      verification_gate(k7, _changed)[0] is False)
_tighter = {**_p, "constraints": {"onsite_days_max": 0}}
check("tightening the office-day limit invalidates it",
      verification_gate(k7, _tighter)[0] is False)


print("\na timestamp has to be a real time in the past")
import math, time
for label, ts in [("one year in the future", time.time() + 365 * 86400),
                  ("missing", None), ("not a number", "yesterday"),
                  ("infinite", math.inf), ("not a number at all", math.nan)]:
    k = verification_key("greenhouse", "acme", f"ts-{abs(hash(label)) % 9999}")
    record_verification(k, live=True, location_ok=True, requirements_read=True,
                        apply_url_ok=True, apply_url="https://x", title_matched="PM",
                        profile_rev=profile_fingerprint(_p))
    _d = __import__("statepath").load("verified.json")
    if ts is None:
        _d[k].pop("checked_at", None)
    else:
        _d[k]["checked_at"] = ts
    __import__("statepath").save("verified.json", _d)
    try:
        ok, why = verification_gate(k, _p)
    except Exception as e:
        ok, why = None, f"raised {type(e).__name__}"
    check(f"a {label} timestamp is refused ({str(why)[:40]})", ok is False)


print("\nlocation assessment")
prof = {"location": {"remote_ok": True, "acceptable_metros": ["dallas"],
                     "metro_aliases": ["dfw"]}}
check("affirmative remote evidence passes",
      assess_location("Fully remote, work from anywhere in the US.", "", prof)[0] is True)
check("silence about location is unresolved, not a pass",
      assess_location("A great opportunity to join a growing team.", "", prof)[0] is None)
check("everyday office attendance is caught",
      assess_location("Work at the office every weekday.", "", prof)[0] is False)
check("no profile means unresolved",
      assess_location("Fully remote.", "", {})[0] is None)
check("an excluded metro fails",
      assess_location("This is a hybrid role in our New York office.", "",
                      {"location": {"remote_ok": True, "acceptable_metros": ["dallas"],
                                    "reject_metros": ["new york"]}})[0] is False)
check("an offered office in an acceptable metro passes",
      assess_location("This is a hybrid role. Our Dallas office, 3 days per week.",
                      "", prof)[0] is True)
check("a city merely mentioned is not an offered location",
      assess_location("Work in the office every weekday in Boston. Our Dallas office "
                      "does not host this team.", "",
                      {"location": {"remote_ok": False, "acceptable_metros": ["dallas"],
                                    "reject_metros": ["boston"]}})[0] is not True)
check("negated remote is not remote evidence",
      assess_location("This is not a fully remote position.", "", prof)[0] is not True)
check("more office days than the user accepts fails",
      assess_location("Based in our Dallas office. Four days per week in office.", "",
                      {"location": {"remote_ok": True, "acceptable_metros": ["dallas"]},
                       "constraints": {"onsite_days_max": 2}})[0] is False)
check("onsite outside acceptable metros fails",
      assess_location("This is a hybrid role. Boston office, 3 days per week.", "", prof)[0] is False)
check("no metros to compare against is unresolved, not a pass",
      assess_location("This is a hybrid role in our office.", "", {"location": {}})[0] is None)
check("remote posting is unresolved for a user who does not want remote",
      assess_location("This is a fully remote role.", "",
                      {"location": {"remote_ok": False}})[0] is None)


print("\ngate accounting")
import io

# Above the noise floor: a silent gate is worth flagging.
big = GateLog(200, gates=["title", "location"])
for _ in range(50):
    big.drop("title")
buf = io.StringIO()
big.report(150, stream=buf)
out = buf.getvalue()
check("on a large sweep, a gate that never fired is reported",
      "gate 'location' never fired" in out)
check("a balanced report raises no alarm", "unaccounted" not in out)

# Below it: most gates legitimately match nothing and the warnings are noise.
small = GateLog(10, gates=["title", "location"])
small.drop("title")
buf_s = io.StringIO()
small.report(9, stream=buf_s)
out_s = buf_s.getvalue()
check("on a small sweep, silent gates are summarised not alarmed",
      "never fired" not in out_s and "matched nothing" in out_s)

# A08: an empty result must say what it is a statement about. When one gate
# removes everything, the rest never saw a record, and warning about each of
# them buries the only finding that matters.
starved = GateLog(148, gates=["title mismatch", "pay floor", "location", "travel"])
for _ in range(148):
    starved.drop("title mismatch")
buf_st = io.StringIO()
starved.report(0, stream=buf_st)
out_st = buf_st.getvalue()
check("a dominant gate is named rather than warned around",
      "Everything was removed by one gate: title mismatch" in out_st)
check("starved gates are reported as unknown, not broken",
      "never saw a record" in out_st and "never fired" not in out_st)
check("an empty result is not presented as proof none exist",
      "not proof that no suitable roles exist" in out_st)

# 200 in, 50 accounted removals, 149 out -- one record vanished unclaimed.
buf2 = io.StringIO()
big.report(149, stream=buf2)
check("a record dropped by no declared gate is reported",
      "1 unaccounted for" in buf2.getvalue())

g = small
try:
    g.drop("typo")
    check("an undeclared gate raises", False)
except KeyError:
    check("an undeclared gate raises", True)

print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
