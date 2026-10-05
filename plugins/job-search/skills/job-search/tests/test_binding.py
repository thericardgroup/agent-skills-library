#!/usr/bin/env python3
"""A01 / A02 — one approval, one posting, one candidate.

Acceptance contract: docs/ACCEPTANCE.md v1.

An approval is evidence about a specific posting assessed against a specific
candidate. These cases drive every supported writing boundary -- the package
CLI, each direct CLI, and each exported write function -- and assert that none
of them will produce a deliverable the approval does not cover.

Written before the fix, to reproduce seq-12 findings 1, 2 and 3.
No network. Run: python3 tests/test_binding.py
"""
import copy, json, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCGEN = os.path.join(ROOT, "scripts", "docgen")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from checks import profile_fingerprint, candidate_id

KEY = "greenhouse::example::4056789"
OTHER_KEY = "lever::globex::4056789"        # same number, different board

PROFILE = {
    "identity": {"name": "Dana Okonkwo", "email": "dana@example.com"},
    "titles": {"target": ["researcher"]},
    "location": {"remote_ok": True, "acceptable_metros": ["chicago"]},
    "constraints": {"onsite_days_max": 2},
    "resume": {"required_sections": ["EXPERIENCE"], "min_chars": 10,
               "experience": [{"title": "Researcher", "employer": "Example",
                               "dates": "2020 - now", "bullets": ["Did the work."]}]},
}

APPROVED = dict(status="verified", live=True, location_ok=True, apply_url_ok=True,
                requirements_read=True, apply_url="https://example.com/apply",
                title_matched="Researcher", company="Example",
                body_fingerprint="bodyfp01")


def approved_for(profile):
    """An approval that names who it was assessed for."""
    return dict(APPROVED, profile_rev=profile_fingerprint(profile),
                candidate=candidate_id(profile))

GOOD_LETTER = {"date": "October 1, 2026", "title": "Researcher", "company": "Example",
               "letter": ["I am applying for this role."]}
GOOD_FIT = {"title": "Researcher", "company": "Example", "verdict": "apply"}
GOOD_RESUME = {"headline": "Researcher", "summary": "A summary.", "skills": ["Interviews"]}

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


def make_state(profile=None, record=None, key=KEY):
    st = tempfile.mkdtemp()
    json.dump(profile or PROFILE, open(os.path.join(st, "profile.json"), "w"))
    rec = dict(record if record is not None else approved_for(profile or PROFILE))
    rec.setdefault("checked_at", time.time())
    json.dump({key: rec}, open(os.path.join(st, "verified.json"), "w"))
    return st


def run_node(script, args, state):
    return subprocess.run(["node", os.path.join(DOCGEN, script)] + args,
                          capture_output=True, text=True, cwd=ROOT,
                          env=dict(os.environ, JOB_SEARCH_STATE=state))


def wrote_anything(d):
    return bool(os.path.isdir(d) and os.listdir(d))


def expect_refusal(label, script, cfg, state, outarg_is_dir=False, key=KEY):
    """Drive one CLI and assert it refuses and publishes nothing."""
    cfg_path = os.path.join(state, "cfg.json")
    json.dump(cfg, open(cfg_path, "w"))
    out = os.path.join(state, "out")
    args = ([cfg_path, out] if outarg_is_dir
            else [cfg_path, os.path.join(out, "doc.out"), key])
    proc = run_node(script, args, state)
    ok = proc.returncode != 0 and not wrote_anything(out)
    check(label, ok, f"exit {proc.returncode}, wrote={wrote_anything(out)}")


# --- A01: content must match the approved posting -------------------------
print("\nA01  every writer refuses content the approval does not cover")

for script, cfg_for, outdir_arg in [
    ("package.js", lambda L, F: {"key": KEY, "letter": L, "fit": F}, True),
]:
    unrelated_L = dict(GOOD_LETTER, title="Staff Designer", company="Globex")
    unrelated_F = dict(GOOD_FIT, title="Staff Designer", company="Globex")
    expect_refusal(f"{script:11} unrelated title and company",
                   script, cfg_for(unrelated_L, unrelated_F), make_state(), outdir_arg)

print()
for script, cfg_for, outdir_arg in [
    ("package.js", lambda L, F: {"key": KEY, "letter": L, "fit": F}, True),
]:
    # Codex's case: related names are not the same posting.
    over_L = dict(GOOD_LETTER, title="Senior Researcher",
                  company="Example Unrelated Subsidiary")
    over_F = dict(GOOD_FIT, title="Senior Researcher",
                  company="Example Unrelated Subsidiary")
    expect_refusal(f"{script:11} overlapping title and company",
                   script, cfg_for(over_L, over_F), make_state(), outdir_arg)

print()
expect_refusal("package.js  config key not the approved key", "package.js",
               {"key": OTHER_KEY, "letter": GOOD_LETTER}, make_state(), True)
expect_refusal("package.js  unchecked apply url", "package.js",
               {"key": KEY, "fit": dict(GOOD_FIT,
                                        apply_url="https://elsewhere.example.com/apply")},
               make_state(), True)

# same title on two requisitions: approving one must not cover the other
st = make_state()
json.dump({KEY: dict(APPROVED, checked_at=time.time())},
          open(os.path.join(st, "verified.json"), "w"))
expect_refusal("package.js  duplicate title, different requisition", "package.js",
               {"key": "greenhouse::example::9999999", "letter": GOOD_LETTER}, st, True)

# id collision across boards
st = make_state(key=OTHER_KEY)
expect_refusal("package.js  same id on a different board", "package.js",
               {"key": KEY, "letter": GOOD_LETTER}, st, True)


# --- A02: the profile actually used must be the approved one --------------
print("\nA02  the profile used for generation is the one the approval covers")

st = make_state(record=approved_for(PROFILE))
hostile = copy.deepcopy(PROFILE)
hostile["location"]["remote_ok"] = False
hostile["location"]["acceptable_metros"] = ["boston"]
expect_refusal("package.js  supplied profile override differs from the approved one",
               "package.js",
               {"key": KEY, "letter": GOOD_LETTER, "profile": hostile}, st, True)

# a record with no revision must not be implicitly trusted after an edit
st = make_state(record=dict(APPROVED))          # no candidate binding at all
changed = copy.deepcopy(PROFILE)
changed["location"]["remote_ok"] = False
json.dump(changed, open(os.path.join(st, "profile.json"), "w"))
expect_refusal("package.js  legacy record without a profile revision",
               "package.js", {"key": KEY, "letter": GOOD_LETTER}, st, True)

st = make_state(record=approved_for(PROFILE))
tight = copy.deepcopy(PROFILE)
tight["constraints"]["onsite_days_max"] = 0
json.dump(tight, open(os.path.join(st, "profile.json"), "w"))
expect_refusal("package.js  office-day limit tightened after approval",
               "package.js", {"key": KEY, "letter": GOOD_LETTER}, st, True)


# --- A02: the approval must identify WHO it was assessed for --------------
print("\nA02  an approval names a candidate, not just a geography")
base_loc = {"remote_ok": True, "acceptable_metros": ["chicago"]}
dana = {"identity": {"name": "Dana Okonkwo", "email": "dana@example.com"},
        "location": base_loc, "constraints": {"onsite_days_max": 2},
        "pay": {"floor": 95000}}
other = {"identity": {"name": "Someone Else", "email": "other@example.com"},
         "location": base_loc, "constraints": {"onsite_days_max": 2},
         "pay": {"floor": 95000}}
check("two different people are not the same candidate",
      candidate_id(dana) != candidate_id(other))

richer = copy.deepcopy(dana)
richer["pay"] = {"floor": 250000}
check("a changed pay floor changes the assessment revision",
      profile_fingerprint(dana) != profile_fingerprint(richer))

gapped = copy.deepcopy(dana)
gapped["gaps"] = [{"name": "clearance", "patterns": ["TS/SCI"], "hard": True}]
check("a changed gap inventory changes the assessment revision",
      profile_fingerprint(dana) != profile_fingerprint(gapped))

retitled = copy.deepcopy(dana)
retitled["titles"] = {"target": ["something else"], "source": "stated"}
check("changed target titles change the assessment revision",
      profile_fingerprint(dana) != profile_fingerprint(retitled))

cosmetic = copy.deepcopy(dana)
cosmetic["resume"] = {"required_sections": ["EXPERIENCE"]}
check("an unrelated resume edit does not invalidate the assessment",
      profile_fingerprint(dana) == profile_fingerprint(cosmetic))

# and the end-to-end consequence: another candidate cannot use the approval
st = make_state(profile=dana,
                record=dict(APPROVED, profile_rev=profile_fingerprint(dana),
                            candidate=candidate_id(dana)))
json.dump(other, open(os.path.join(st, "profile.json"), "w"))
expect_refusal("package.js  a different candidate cannot use the approval",
               "package.js", {"key": KEY, "letter": GOOD_LETTER}, st, True)


# The exported writers are the other way in. Removing the CLIs did not remove
# them, and a supplied profile object never reaches the Python gate, so the
# identity check has to happen at the boundary itself.
print("\nA02  an exported writer checks the profile it was handed")
imposter = copy.deepcopy(PROFILE)
imposter["identity"] = {"name": "Someone Else", "email": "other@example.com"}

st = make_state(record=approved_for(PROFILE))
probe = f"""
const {{ writeLetter }} = require({json.dumps(os.path.join(DOCGEN, 'letter'))});
writeLetter({json.dumps(GOOD_LETTER)},
            {json.dumps(os.path.join(st, 'out', 'x.docx'))},
            {json.dumps(imposter)}, {{ key: {json.dumps(KEY)} }})
  .then(() => console.log('WROTE')).catch(() => console.log('REFUSED'));
"""
r = subprocess.run(["node", "-e", probe], capture_output=True, text=True, cwd=ROOT,
                   env=dict(os.environ, JOB_SEARCH_STATE=st))
check("a supplied profile for another candidate is refused",
      "REFUSED" in r.stdout and not wrote_anything(os.path.join(st, "out")),
      r.stdout.strip()[:40])

st2 = make_state(record=approved_for(PROFILE))
probe_ok = probe.replace(json.dumps(imposter), json.dumps(PROFILE)).replace(st, st2)
r2 = subprocess.run(["node", "-e", probe_ok], capture_output=True, text=True, cwd=ROOT,
                    env=dict(os.environ, JOB_SEARCH_STATE=st2))
check("the rightful candidate is still allowed", "WROTE" in r2.stdout,
      (r2.stdout + r2.stderr).strip()[:60])


# --- A06: no supported write surface produces an unauditable document -----
print("\nA06  the only supported way to write a document is the package")
for script in ("letter.js", "resume.js", "fit.js"):
    src = open(os.path.join(DOCGEN, script), encoding="utf-8").read()
    check(f"{script:10} has no standalone CLI entry point",
          "require.main === module" not in src)


# --- the valid neighbouring case must still succeed -----------------------
print("\nvalid neighbour: a matching record and config succeeds")
st = make_state(record=approved_for(PROFILE))
cfg_path = os.path.join(st, "cfg.json")
json.dump({"key": KEY, "resume": GOOD_RESUME, "letter": GOOD_LETTER, "fit": GOOD_FIT},
          open(cfg_path, "w"))
out = os.path.join(st, "out")
proc = run_node("package.js", [cfg_path, out], st)
produced = sorted(os.listdir(out)) if os.path.isdir(out) else []
check("package.js  matching config produces the package",
      proc.returncode == 0 and "resume.docx" in produced
      and "cover-letter.docx" in produced and "fit-summary.md" in produced,
      f"exit {proc.returncode}, {produced}")

print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
