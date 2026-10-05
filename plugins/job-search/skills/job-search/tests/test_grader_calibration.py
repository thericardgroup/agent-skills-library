#!/usr/bin/env python3
"""The grader must disagree with a broken run.

A grader is only evidence if it separates good from bad. The first rebuilt
version scored 12/12 on a full run and still passed a state where records were
stale and self-certified while the real gate rejected them. These three
scenarios pin that down.

No network. Run: python3 tests/test_grader_calibration.py
"""
import json, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(ROOT, "evals", "check_artifacts.py")

PROFILE = {
    "identity": {"name": "Dana Okonkwo", "email": "dana@example.com"},
    "titles": {"target": ["product manager"]},
    "location": {"remote_ok": True, "acceptable_metros": ["chicago"]},
    "interests": [{"name": "healthcare", "patterns": ["patient"]}],
    "resume": {"required_sections": ["EXPERIENCE"]},
}
PERSONA = "product manager,chicago"


def grade(state, outputs=None):
    proc = subprocess.run(
        [sys.executable, CHECKER, "--state", state, "--skill", ROOT,
         "--persona-terms", PERSONA, "--json"]
        + (["--outputs", outputs] if outputs else []),
        capture_output=True, text=True)
    rows = json.loads(proc.stdout)["expectations"]
    return {r["text"]: r for r in rows}


def scenario_empty():
    return tempfile.mkdtemp(), None


def scenario_stale_self_certified():
    """Codex's counterexample: records that LOOK verified, documents on disk,
    and a real gate that would refuse every one of them."""
    state = tempfile.mkdtemp()
    out = os.path.join(state, "out")
    os.makedirs(out)
    json.dump(PROFILE, open(os.path.join(state, "profile.json"), "w"))
    json.dump({
        "greenhouse::acme::111": dict(
            status="verified", live=True, location_ok=True, apply_url_ok=True,
            requirements_read=True, apply_url="https://x", title_matched="PM",
            checked_at=time.time() - 9 * 86400),          # stale
        "greenhouse::acme::222": dict(
            status="failed", reason="unreachable", live=False, location_ok=False,
            apply_url_ok=False, requirements_read=False,
            checked_at=time.time()),
    }, open(os.path.join(state, "verified.json"), "w"))
    json.dump([dict(platform="greenhouse", board="acme", requisition_id="111",
                    companyName="Acme", title="Product Manager")],
              open(os.path.join(state, "postings.json"), "w"))
    json.dump({"Acme": {"platform": "greenhouse", "board": "acme", "confirmed": True}},
              open(os.path.join(state, "companies.json"), "w"))
    # Documents were produced anyway.
    open(os.path.join(out, "fit-summary.md"), "w").write("# fit\n")
    return state, out


def scenario_good():
    state = tempfile.mkdtemp()
    out = os.path.join(state, "out")
    os.makedirs(out)
    json.dump(PROFILE, open(os.path.join(state, "profile.json"), "w"))
    json.dump({"greenhouse::acme::111": dict(
        status="verified", live=True, location_ok=True, apply_url_ok=True,
        requirements_read=True, apply_url="https://x", title_matched="PM",
        checked_at=time.time())},
        open(os.path.join(state, "verified.json"), "w"))
    json.dump([dict(platform="greenhouse", board="acme", requisition_id="111",
                    companyName="Acme", title="Product Manager")],
              open(os.path.join(state, "postings.json"), "w"))
    json.dump({"Acme": {"platform": "greenhouse", "board": "acme", "confirmed": True}},
              open(os.path.join(state, "companies.json"), "w"))
    fit = os.path.join(out, "fit-summary.md")
    open(fit, "w").write("# fit\n")
    # A package now declares itself; a document with no manifest is not one.
    import hashlib
    json.dump({"schema": "job-search/package-manifest@1",
               "key": "greenhouse::acme::111", "generated_at": time.time(),
               "files": [{"name": "fit-summary.md", "bytes": os.path.getsize(fit),
                          "sha256": "sha256:" + hashlib.sha256(
                              open(fit, "rb").read()).hexdigest()[:32]}],
               "approval": {"status": "verified", "location_ok": True,
                            "apply_url_ok": True, "requirements_read": True,
                            "apply_url": "https://x", "title_matched": "PM",
                            "company": "Acme", "body_fingerprint": None,
                            "profile_rev": "rev-c"},
               "profile_rev": "rev-c", "preexisting_files": []},
              open(os.path.join(out, "package-manifest.json"), "w"))
    return state, out


passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


print("\nA. nothing executed")
g = grade(*scenario_empty())
n_pass = sum(1 for r in g.values() if r["passed"])
check("scores zero", n_pass == 0, f"{n_pass} passed")

print("\nB. stale and self-certified, documents present")
g = grade(*scenario_stale_self_certified())
check("gate_opened rejects the stale record", not g["gate_opened"]["passed"],
      g["gate_opened"]["evidence"][:62])
check("packaging_was_gated catches unapproved output",
      not g["packaging_was_gated"]["passed"],
      g["packaging_was_gated"]["evidence"][:62])
n_pass = sum(1 for r in g.values() if r["passed"])
check("does not score as a clean run", n_pass < len(g) - 2, f"{n_pass}/{len(g)} passed")

print("\nC. a run the real gate would allow")
g = grade(*scenario_good())
check("gate_opened passes", g["gate_opened"]["passed"])
check("packaging_was_gated passes", g["packaging_was_gated"]["passed"])
check("persona match passes", g["profile_matches_persona"]["passed"],
      g["profile_matches_persona"]["evidence"][:62])

# --- A07: the counterexamples seq 12 reproduced -------------------------
print("\nD. a package the grader must not accept")

import hashlib, shutil


def packaged(mutate_manifest=None, mutate_files=None, extra_record=False):
    """A real package, then tampered with."""
    state = tempfile.mkdtemp()
    out = os.path.join(state, "out")
    os.makedirs(out)
    json.dump(PROFILE, open(os.path.join(state, "profile.json"), "w"))

    appr = dict(status="verified", live=True, location_ok=True, apply_url_ok=True,
                requirements_read=True, checked_at=time.time(),
                apply_url="https://example.com/apply", title_matched="Product Manager",
                company="Acme", body_fingerprint="fp-original", profile_rev="rev-original")
    records = {"greenhouse::acme::111": appr}
    if extra_record:
        records["greenhouse::other::999"] = dict(appr)
    json.dump(records, open(os.path.join(state, "verified.json"), "w"))

    letter = os.path.join(out, "cover-letter.docx")
    open(letter, "w").write("a generated letter")
    fit = os.path.join(out, "fit-summary.md")
    open(fit, "w").write("# fit\n")
    digest = lambda f: "sha256:" + hashlib.sha256(open(f, "rb").read()).hexdigest()[:32]
    man = {"schema": "job-search/package-manifest@1",
           "key": "greenhouse::acme::111", "generated_at": time.time(),
           "files": [{"name": "cover-letter.docx", "bytes": os.path.getsize(letter),
                      "sha256": digest(letter)},
                     {"name": "fit-summary.md", "bytes": os.path.getsize(fit),
                      "sha256": digest(fit)}],
           "approval": {k: appr[k] for k in
                        ("status", "location_ok", "apply_url_ok", "requirements_read",
                         "apply_url", "title_matched", "company", "body_fingerprint",
                         "profile_rev")},
           "profile_rev": "rev-original", "preexisting_files": []}
    if mutate_manifest:
        mutate_manifest(man)
    json.dump(man, open(os.path.join(out, "package-manifest.json"), "w"))
    if mutate_files:
        mutate_files(out)
    return state, out


g = grade(*packaged())
check("an intact package passes", g["packaging_was_gated"]["passed"]
      and g["package_files_intact"]["passed"])

g = grade(*packaged(mutate_files=lambda d: open(
    os.path.join(d, "cover-letter.docx"), "w").write("not the generated bytes")))
check("a tampered artifact is caught", not g["package_files_intact"]["passed"],
      g["package_files_intact"]["evidence"][:58])

g = grade(*packaged(mutate_files=lambda d: os.remove(os.path.join(d, "fit-summary.md"))))
check("a missing artifact is caught", not g["package_files_intact"]["passed"],
      g["package_files_intact"]["evidence"][:58])

g = grade(*packaged(mutate_manifest=lambda m: m["approval"].update(requirements_read=False)))
check("a package whose own approval never read the requirements is caught",
      not g["packaging_was_gated"]["passed"])

g = grade(*packaged(mutate_manifest=lambda m: m["approval"].update(profile_rev=None)))
check("a package not bound to any profile is caught",
      not g["packaging_was_gated"]["passed"])

# Codex's case: the posting changed after generation.
st, out = packaged()
recs = json.load(open(os.path.join(st, "verified.json")))
recs["greenhouse::acme::111"]["body_fingerprint"] = "fp-changed"
json.dump(recs, open(os.path.join(st, "verified.json"), "w"))
g = grade(st, out)
check("a package describing superseded text is caught",
      not g["packaging_was_gated"]["passed"],
      g["packaging_was_gated"]["evidence"][:58])

# Codex's case: an unrelated valid approval must not vouch for this package.
g = grade(*packaged(mutate_manifest=lambda m: m["approval"].update(status="failed"),
                    extra_record=True))
check("an unrelated passing record does not rescue a bad package",
      not g["packaging_was_gated"]["passed"])

st, out = packaged()
os.remove(os.path.join(out, "package-manifest.json"))
g = grade(st, out)
check("documents with no manifest at all are caught",
      not g["packaging_was_gated"]["passed"])


print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
