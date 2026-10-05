#!/usr/bin/env python3
"""A10 — the skill works from a clean user environment.

Acceptance contract: docs/ACCEPTANCE.md v1.

Every other guarantee is invisible if installation fails on a machine that is
not the one it was built on. This copies the repository somewhere else, strips
what a fresh download would not have, and runs a complete workflow from a
different working directory.

What it deliberately does NOT claim: that `/plugin marketplace add` works from
GitHub. Nothing has been pushed, so that path cannot be exercised here and is
reported as an outstanding condition rather than a pass.

Offline except the preflight dependency install. Run: python3 tests/test_clean_install.py
"""
import json, os, shutil, subprocess, sys, tempfile

SKILL_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# skills/<skill> -> skills -> plugins/<plugin> -> plugins -> repo root
REPO_SRC = os.path.abspath(os.path.join(SKILL_SRC, "..", "..", "..", ".."))

passed, failed, notrun = [], [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


def skip(name, why):
    notrun.append(name)
    print(f"  n/a   {name}  {why}")


def run(cmd, cwd, env=None, timeout=300):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, **(env or {})))


# --- install: a download unpacked somewhere with a space in the path ------
print("\ninstall into a path containing spaces")
home = tempfile.mkdtemp()
install_root = os.path.join(home, "My Documents", "claude skills")
os.makedirs(install_root)
repo = os.path.join(install_root, "agent-skills-library")
shutil.copytree(REPO_SRC, repo,
                ignore=shutil.ignore_patterns(".git", "node_modules", ".handoffs",
                                              ".claude", "__pycache__", "*.pyc"))
SKILL = os.path.join(repo, "plugins", "job-search", "skills", "job-search")
check("the repository unpacks under a path with spaces", os.path.isdir(SKILL), install_root)

# a fresh download has no installed dependencies
check("no node_modules came along",
      not os.path.isdir(os.path.join(SKILL, "scripts", "docgen", "node_modules")))

print("\nmanifests and referenced files survive the copy")
for rel in (".claude-plugin/marketplace.json",
            "plugins/job-search/.claude-plugin/plugin.json"):
    p = os.path.join(repo, rel)
    try:
        json.load(open(p))
        ok = True
    except Exception as e:
        ok = False
    check(f"{rel} parses", ok)

man = json.load(open(os.path.join(repo, ".claude-plugin", "marketplace.json")))
raw_src = man["plugins"][0]["source"]
# A source is either a relative path inside this repo, or an object naming a
# git source with its own ref. Both are valid; they are checked differently.
if isinstance(raw_src, str):
    src = raw_src.lstrip("./")
    check("the marketplace source path exists in the package",
          os.path.isdir(os.path.join(repo, src)), src)
else:
    src = (raw_src.get("path") or "").lstrip("./")
    check("the pinned source names a path that exists in the package",
          bool(src) and os.path.isdir(os.path.join(repo, src)), src)
    check("the release is pinned to a tag rather than a branch",
          raw_src.get("ref") not in (None, "", "main", "master", "HEAD"),
          str(raw_src.get("ref")))
    check("the pinned tag exists in this repository",
          subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                          f"{raw_src['ref']}^{{commit}}"],
                         cwd=REPO_SRC, capture_output=True).returncode == 0,
          str(raw_src.get("ref")))
check("SKILL.md is where a plugin loader expects it",
      os.path.isfile(os.path.join(SKILL, "SKILL.md")))

missing = []
for root, _dirs, files in os.walk(SKILL):
    for f in files:
        if not f.endswith(".md"):
            continue
        text = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
        import re
        for m in re.finditer(r'`((?:scripts|references|examples|tests|evals)/[\w./-]+'
                             r'\.(?:py|js|md|json))`', text):
            if not os.path.exists(os.path.join(SKILL, m.group(1))):
                missing.append(f"{f} -> {m.group(1)}")
check("every file the documentation points at is present",
      not missing, "; ".join(sorted(set(missing))[:3]))

# --- first run from an unrelated working directory ------------------------
print("\nfirst run, from a different working directory")
workdir = os.path.join(home, "job hunt")
os.makedirs(workdir)
state = os.path.join(workdir, ".claude", "job-search")

pf = run([sys.executable, os.path.join(SKILL, "scripts", "preflight.py")], cwd=workdir)
report = {}
try:
    report = json.loads(pf.stdout)
except Exception:
    pass
check("preflight runs and reports", pf.returncode == 0 and bool(report),
      (pf.stderr or pf.stdout)[:70])
# realpath on both sides: /var is a symlink to /private/var on macOS, and
# comparing the unresolved strings fails on a correct result.
_root = os.path.realpath(report.get("state_root", "") or os.devnull)
check("state lands under the user's working directory, not the install",
      _root.startswith(os.path.realpath(workdir)), _root[:62])
check("state is not inside the installed skill tree",
      not _root.startswith(os.path.realpath(SKILL)))
check("nothing was written inside the installed skill",
      not os.path.isdir(os.path.join(SKILL, ".claude")))

if report.get("fixed") or os.path.isdir(os.path.join(SKILL, "scripts", "docgen",
                                                      "node_modules")):
    check("preflight installed the document libraries itself",
          os.path.isdir(os.path.join(SKILL, "scripts", "docgen", "node_modules")),
          "; ".join(report.get("fixed", []))[:60])
else:
    check("a missing dependency is reported with a recovery instruction",
          any("npm" in b or "Node" in b for b in report.get("blocked", [])),
          "; ".join(report.get("blocked", []))[:70])

# --- a complete workflow, offline, from that directory --------------------
print("\na complete workflow in the installed copy")
env = {"JOB_SEARCH_STATE": state}
shutil.copy(os.path.join(SKILL, "examples", "profile.example.json"),
            os.path.join(state, "profile.json"))

v = run([sys.executable, os.path.join(SKILL, "scripts", "validate_profile.py"),
         "--file", os.path.join(state, "profile.json")], cwd=workdir, env=env)
check("the shipped example profile validates in place", v.returncode == 0,
      (v.stdout or "").strip().splitlines()[-1][:60] if v.stdout else "")

# synthetic approval, then package -- no network
seed = f'''
import sys, json, time
sys.path.insert(0, {os.path.join(SKILL, "scripts")!r})
from statepath import save, load
from checks import record_verification, profile_fingerprint, candidate_id
prof = load("profile.json")
save("postings.json", [])
record_verification("greenhouse::example::1", live=True, location_ok=True,
    requirements_read=True, apply_url_ok=True, apply_url="https://example.com/a",
    title_matched="Senior UX Researcher", company="Example",
    body_fingerprint="fp1", profile_rev=profile_fingerprint(prof),
    candidate=candidate_id(prof))
json.dump({{"key": "greenhouse::example::1",
  "resume": {{"headline": "Senior UX Researcher", "summary": "A summary.",
             "skills": ["Usability testing"]}},
  "letter": {{"date": "October 4, 2026", "title": "Senior UX Researcher",
             "company": "Example", "letter": ["I am applying for this role."]}},
  "fit": {{"title": "Senior UX Researcher", "company": "Example", "verdict": "apply"}}}},
  open({os.path.join(workdir, "pkg.json")!r}, "w"))
'''
s = run([sys.executable, "-c", seed], cwd=workdir, env=env)
check("state helpers import from the installed copy", s.returncode == 0,
      (s.stderr or "").strip().splitlines()[-1][:70] if s.stderr else "")

out = os.path.join(workdir, "applications", "example")
pkg = run(["node", os.path.join(SKILL, "scripts", "docgen", "package.js"),
           os.path.join(workdir, "pkg.json"), out], cwd=workdir, env=env)
produced = sorted(os.listdir(out)) if os.path.isdir(out) else []
check("a package is produced from the installed copy",
      pkg.returncode == 0 and "package-manifest.json" in produced,
      f"exit {pkg.returncode}, {produced or (pkg.stderr or '').strip()[:60]}")

grade = run([sys.executable, os.path.join(SKILL, "evals", "check_artifacts.py"),
             "--state", state, "--outputs", out, "--skill", repo,
             "--checks", "packaging_was_gated,package_files_intact,state_outside_skill_dir"],
            cwd=workdir, env=env)
check("the installed copy grades its own output",
      grade.returncode == 0, (grade.stdout or "").strip().splitlines()[-1][:60])

# --- update must not touch the user's data --------------------------------
print("\nan update leaves the user's data alone")
marker = os.path.join(state, "applications.json")
json.dump({"Example::Senior UX Researcher": {"status": "submitted"}}, open(marker, "w"))
before = open(marker).read()
shutil.rmtree(SKILL)
shutil.copytree(os.path.join(SKILL_SRC), SKILL,
                ignore=shutil.ignore_patterns("node_modules", "__pycache__", "*.pyc"))
check("reinstalling the skill does not disturb user state",
      os.path.exists(marker) and open(marker).read() == before)

print("\nwhat could not be tested here")
skip("remote install via /plugin marketplace add",
     "nothing is pushed; needs a published repository")

print(f"\n{len(passed)} passed, {len(failed)} failed, {len(notrun)} not run")
sys.exit(1 if failed else 0)
