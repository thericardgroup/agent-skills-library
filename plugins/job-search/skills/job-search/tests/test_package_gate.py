#!/usr/bin/env python3
"""Drive the real packaging entry point against every bad record state.

Inspecting verified.json tells you what a record says. It does not tell you
whether the code that reads it actually refuses. The first rebuilt grader passed
a workflow in which all three generators wrote files against an empty
verified.json, because nothing in the harness ever invoked them.

So this calls node scripts/docgen/package.js for real and asserts two things
every time: a non-zero exit, and nothing written to disk.

No network. Run: python3 tests/test_package_gate.py
"""
import json, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from checks import profile_fingerprint, candidate_id

KEY = "greenhouse::acme::4056789"
PROFILE = {
    "identity": {"name": "Dana Okonkwo", "email": "dana@example.com",
                 "location": "Chicago, IL"},
    "titles": {"target": ["product manager"]},
    "location": {"remote_ok": True, "acceptable_metros": ["chicago"]},
    "resume": {"required_sections": ["EXPERIENCE"], "min_chars": 10,
               "experience": [{"title": "PM", "employer": "Example Co",
                               "dates": "2020 - now", "bullets": ["Did the work."]}]},
}
CFG = {
    "key": KEY,
    "letter": {"date": "October 1, 2026", "title": "Product Manager",
               "company": "Example Co", "letter": ["I am applying for this role."]},
    "fit": {"title": "Product Manager", "company": "Example Co", "verdict": "apply"},
}

RECORDS = {
    "absent": None,
    "unread requirements": dict(status="verified", live=True, location_ok=True,
                                apply_url_ok=True, requirements_read=False),
    "stale": dict(status="verified", live=True, location_ok=True, apply_url_ok=True,
                  requirements_read=True, _age_days=5),
    "failed recheck": dict(status="failed", reason="board unreachable", live=False,
                           location_ok=False, apply_url_ok=False,
                           requirements_read=False),
    "no profile revision": dict(status="verified", live=True, location_ok=True,
                                apply_url_ok=True, requirements_read=True,
                                _no_profile_rev=True),
    "dead apply link": dict(status="verified", live=True, location_ok=True,
                            apply_url_ok=False, requirements_read=True),
    "unresolved location": dict(status="verified", live=True, location_ok=False,
                                apply_url_ok=True, requirements_read=True),
}

passed, failed = [], []


def check(name, cond):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}")


def run_case(label, record, expect_refusal):
    state = tempfile.mkdtemp()
    outdir = os.path.join(state, "out")
    with open(os.path.join(state, "profile.json"), "w") as fh:
        json.dump(PROFILE, fh)
    if record is not None:
        rec = dict(record)
        age = rec.pop("_age_days", 0)
        rec.setdefault("apply_url", "https://example.com/apply")
        rec.setdefault("title_matched", "Product Manager")
        rec.setdefault("company", "Example Co")
        if rec.pop("_no_profile_rev", False):
            rec.pop("profile_rev", None)
        else:
            rec.setdefault("profile_rev", profile_fingerprint(PROFILE))
            rec.setdefault("candidate", candidate_id(PROFILE))
        rec["checked_at"] = time.time() - age * 86400
        with open(os.path.join(state, "verified.json"), "w") as fh:
            json.dump({KEY: rec}, fh)

    cfg_path = os.path.join(state, "cfg.json")
    with open(cfg_path, "w") as fh:
        json.dump(CFG, fh)

    env = dict(os.environ, JOB_SEARCH_STATE=state)
    proc = subprocess.run(
        ["node", os.path.join(ROOT, "scripts", "docgen", "package.js"), cfg_path, outdir],
        capture_output=True, text=True, env=env, cwd=ROOT)

    produced = []
    if os.path.isdir(outdir):
        produced = [f for f in os.listdir(outdir)]

    if expect_refusal:
        ok = proc.returncode != 0 and not produced
        detail = (f"exit {proc.returncode}, "
                  f"{len(produced) or 'no'} file(s) written")
        if produced:
            detail += f" ({', '.join(produced)})"
    else:
        ok = proc.returncode == 0 and produced
        detail = f"exit {proc.returncode}, produced {', '.join(produced) or 'nothing'}"
        if not ok and proc.stderr:
            detail += f" | {proc.stderr.strip().splitlines()[-1][:80]}"

    (passed if ok else failed).append(label)
    print(f"  {'ok  ' if ok else 'FAIL'}  {label:26} {detail}")


print("\npackaging must refuse")
for label, rec in RECORDS.items():
    run_case(label, rec, expect_refusal=True)

print("\npackaging must succeed when the record is complete")
run_case("fully verified", dict(status="verified", live=True, location_ok=True,
                                apply_url_ok=True, requirements_read=True),
         expect_refusal=False)

print("\ncontent must match the posting the approval covers")
for label, mutate in [
    ("different company", lambda c: c["letter"].update(company="Globex")),
    ("different role",    lambda c: c["letter"].update(title="Staff Designer")),
    ("unverified apply link",
     lambda c: c["fit"].update(apply_url="https://elsewhere.example.com/apply")),
]:
    import copy
    cfg_bad = copy.deepcopy(CFG)
    mutate(cfg_bad)
    state = tempfile.mkdtemp()
    outdir = os.path.join(state, "out")
    json.dump(PROFILE, open(os.path.join(state, "profile.json"), "w"))
    json.dump({KEY: dict(status="verified", live=True, location_ok=True, apply_url_ok=True,
                         requirements_read=True, checked_at=time.time(),
                         apply_url="https://example.com/apply",
                         title_matched="Product Manager", company="Example Co",
                         profile_rev=profile_fingerprint(PROFILE),
                         candidate=candidate_id(PROFILE))},
              open(os.path.join(state, "verified.json"), "w"))
    cfg_path = os.path.join(state, "cfg.json")
    json.dump(cfg_bad, open(cfg_path, "w"))
    proc = subprocess.run(
        ["node", os.path.join(ROOT, "scripts", "docgen", "package.js"), cfg_path, outdir],
        capture_output=True, text=True, env=dict(os.environ, JOB_SEARCH_STATE=state), cwd=ROOT)
    produced = os.path.isdir(outdir) and os.listdir(outdir)
    ok = proc.returncode != 0 and not produced
    (passed if ok else failed).append(label)
    print(f"  {'ok  ' if ok else 'FAIL'}  {label:26} exit {proc.returncode}, "
          f"{len(produced or []) or 'no'} file(s)")

print("\na package says what it is evidence for")
state = tempfile.mkdtemp(); outdir = os.path.join(state, "out")
json.dump(PROFILE, open(os.path.join(state, "profile.json"), "w"))
json.dump({KEY: dict(status="verified", live=True, location_ok=True, apply_url_ok=True,
                     requirements_read=True, checked_at=time.time(),
                     apply_url="https://example.com/apply",
                     title_matched="Product Manager", company="Example Co",
                     body_fingerprint="abc123",
                     profile_rev=profile_fingerprint(PROFILE),
                     candidate=candidate_id(PROFILE))},
          open(os.path.join(state, "verified.json"), "w"))
cfg_path = os.path.join(state, "cfg.json"); json.dump(CFG, open(cfg_path, "w"))
subprocess.run(["node", os.path.join(ROOT, "scripts", "docgen", "package.js"), cfg_path, outdir],
               capture_output=True, text=True,
               env=dict(os.environ, JOB_SEARCH_STATE=state), cwd=ROOT)
mpath = os.path.join(outdir, "package-manifest.json")
man = json.load(open(mpath)) if os.path.exists(mpath) else {}
names = {f.get("name") for f in (man.get("files") or [])}
check("a manifest binds the files to the requisition",
      man.get("key") == KEY and "cover-letter.docx" in names)
check("the manifest carries a schema version", man.get("schema", "").startswith(
      "job-search/package-manifest@"))
check("every declared file carries a content digest",
      bool(names) and all(f.get("sha256", "").startswith("sha256:")
                          for f in man["files"]))
check("the manifest snapshots the approval rather than pointing at mutable state",
      (man.get("approval") or {}).get("body_fingerprint") == "abc123"
      and man["approval"].get("requirements_read") is True)
check("pre-existing files in the output directory are declared",
      isinstance(man.get("preexisting_files"), list))

print("\nmissing key is refused outright")
state = tempfile.mkdtemp()
with open(os.path.join(state, "profile.json"), "w") as fh:
    json.dump(PROFILE, fh)
cfg = {k: v for k, v in CFG.items() if k != "key"}
cfg_path = os.path.join(state, "cfg.json")
with open(cfg_path, "w") as fh:
    json.dump(cfg, fh)
proc = subprocess.run(
    ["node", os.path.join(ROOT, "scripts", "docgen", "package.js"), cfg_path,
     os.path.join(state, "out")],
    capture_output=True, text=True, env=dict(os.environ, JOB_SEARCH_STATE=state), cwd=ROOT)
ok = proc.returncode != 0 and not os.path.isdir(os.path.join(state, "out"))
(passed if ok else failed).append("no key")
print(f"  {'ok  ' if ok else 'FAIL'}  {'no requisition key':26} exit {proc.returncode}")

print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
