#!/usr/bin/env python3
"""A09 — both entry paths reach the same pipeline.

Acceptance contract: docs/ACCEPTANCE.md v1.

Two kinds of person arrive. One can name the roles they want. One cannot, and
asking them to is how that user gets stalled or guessed at. Both must end up
with a profile the rest of the pipeline can run on, and the profile must record
which way it got there -- a derived target is a hypothesis the first ranking
should be allowed to revise, and a stated one is not.

No network. Run: python3 tests/test_entry_paths.py
"""
import copy, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ["JOB_SEARCH_STATE"] = tempfile.mkdtemp()
from validate_profile import validate

BASE = {
    "identity": {"name": "Dana Okonkwo", "email": "dana@example.com"},
    "location": {"remote_ok": True, "acceptable_metros": ["columbus"]},
    "constraints": {"onsite_days_max": 3},
    "pay": {"floor": 60000},
}

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


def errs(profile, stage="search"):
    return validate(profile, stage)[0]


def warns(profile, stage="search"):
    return validate(profile, stage)[1]


print("\npath A: the user names their targets")
stated = copy.deepcopy(BASE)
stated["titles"] = {"target": ["claims", "underwrit"], "source": "stated"}
check("a stated profile validates", not errs(stated), str(errs(stated))[:70])

print("\npath B: the user cannot name a target, so it is derived")
derived = copy.deepcopy(BASE)
derived["titles"] = {
    "target": ["claims", "adjuster", "underwrit"],
    "source": "derived",
    "derived_from": [
        {"family": "Claims", "evidence": "Seven years adjudicating auto and property claims"},
        {"family": "Underwriting", "evidence": "Owned risk decisions on renewals"},
    ],
}
check("a derived profile validates", not errs(derived), str(errs(derived))[:70])
check("a derived profile is marked as a hypothesis, not a statement",
      derived["titles"]["source"] == "derived")

print("\nthe derivation has to carry its evidence")
naked = copy.deepcopy(derived)
naked["titles"].pop("derived_from")
check("derived targets without evidence are rejected",
      any("derived_from" in e for e in errs(naked)), str(errs(naked))[:70])

empty_ev = copy.deepcopy(derived)
empty_ev["titles"]["derived_from"] = [{"family": "Claims"}]
check("each derived family needs the evidence behind it",
      any("evidence" in e for e in errs(empty_ev)), str(errs(empty_ev))[:70])

print("\nneither path may leave the pipeline without a destination")
nothing = copy.deepcopy(BASE)
nothing["titles"] = {"target": [], "source": "derived", "derived_from": []}
check("an empty target is still an error however it was produced",
      any("target" in e for e in errs(nothing)))

print("\nan unknown source is not silently accepted")
bogus = copy.deepcopy(stated)
bogus["titles"]["source"] = "guessed"
check("source must be stated or derived",
      any("source" in e for e in errs(bogus)), str(errs(bogus))[:70])

print("\nolder profiles without a source still work")
legacy = copy.deepcopy(BASE)
legacy["titles"] = {"target": ["claims"]}
check("a profile predating this field validates", not errs(legacy))
check("...and says the provenance is unknown",
      any("source" in w for w in warns(legacy)), str(warns(legacy))[:70])

print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
