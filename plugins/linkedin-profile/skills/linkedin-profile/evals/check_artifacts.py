#!/usr/bin/env python3
"""Inspect what a linkedin-profile run actually wrote, not what it said.

A skill can describe a careful process fluently while doing none of it. These checks read the
snapshot directory and report what is on disk.

Honest scope: this skill's main effect lands on a third-party profile that no local checker can
see. The durable local artifact is the snapshot, which is also the artifact that matters most for
safety, because it is the only thing standing between a bad write and an unrecoverable one. The
checks here are about that file. Everything else in this skill is judged from the transcript, and
that is a real limit, not a design choice.

A check with nothing to inspect returns None and reports n/a. A guard that passes on an empty
directory measures nothing.
"""
import argparse, json, os, re, sys, datetime

CHECKS = {}


def check(name):
    def wrap(fn):
        CHECKS[name] = fn
        return fn
    return wrap


def _snapshots(ctx):
    """Every snapshot file in the state directory, newest first."""
    d = ctx.get("state")
    if not d or not os.path.isdir(d):
        return []
    out = []
    for root, _dirs, files in os.walk(d):
        for f in files:
            if f.startswith("snapshot-") and f.endswith(".md"):
                p = os.path.join(root, f)
                out.append((p, os.path.getmtime(p)))
    return [p for p, _ in sorted(out, key=lambda x: -x[1])]


def _text(path):
    try:
        with open(path, encoding="utf8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


# Author vocabulary. Residue from the profile rebuild this skill was written from would look
# like this. Shapes, not one person's details, so this file stays safe to publish.
AUTHOR_TERMS = re.compile(
    r"\b(product manager|product management|\bPRD\b|roadmap|AI agent|agentic|voice agent|"
    r"conversational AI|applicant tracking|greenhouse|ashby|lever\b|workday|"
    r"software engineer|SaaS|startup)\b", re.I)


@check("snapshot_written")
def _(ctx):
    """A snapshot exists before anything could have been overwritten."""
    snaps = _snapshots(ctx)
    if not snaps:
        return False, "no snapshot-*.md found in the state directory"
    return True, f"{len(snaps)} snapshot(s): {', '.join(os.path.basename(s) for s in snaps[:3])}"


@check("snapshot_uniquely_named")
def _(ctx):
    """Filenames carry a timestamp, not a bare date, so a second run cannot clobber the first."""
    snaps = _snapshots(ctx)
    if not snaps:
        return None, "no snapshots to inspect"
    bare_date = re.compile(r"^snapshot-\d{4}-\d{2}-\d{2}(\.md)$")
    bad = [os.path.basename(s) for s in snaps if bare_date.match(os.path.basename(s))]
    if bad:
        return False, f"date-only filenames, a same-day rerun would overwrite: {', '.join(bad)}"
    names = [os.path.basename(s) for s in snaps]
    if len(set(names)) != len(names):
        return False, "duplicate snapshot filenames"
    return True, f"{len(names)} uniquely named: {names[0]}"


@check("snapshot_carries_account")
def _(ctx):
    """A snapshot you cannot attribute to an account is not a recovery copy."""
    snaps = _snapshots(ctx)
    if not snaps:
        return None, "no snapshots to inspect"
    missing = []
    for s in snaps:
        t = _text(s)
        has_url = "linkedin.com/in/" in t.lower()
        has_time = bool(re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", t))
        if not (has_url and has_time):
            missing.append(
                f"{os.path.basename(s)}(url={'y' if has_url else 'n'},time={'y' if has_time else 'n'})")
    if missing:
        return False, "snapshot lacks account URL and/or capture time: " + ", ".join(missing)
    return True, f"all {len(snaps)} carry a profile URL and capture time"


@check("snapshot_has_content")
def _(ctx):
    """An empty or truncated snapshot passes a 'file exists' test and recovers nothing."""
    snaps = _snapshots(ctx)
    if not snaps:
        return None, "no snapshots to inspect"
    thin = [(os.path.basename(s), len(_text(s))) for s in snaps if len(_text(s)) < 400]
    if thin:
        return False, "snapshot too short to be a recovery copy: " + ", ".join(
            f"{n} ({c} chars)" for n, c in thin)
    sizes = [len(_text(s)) for s in snaps]
    return True, f"smallest snapshot {min(sizes)} chars"


@check("snapshot_covers_sections")
def _(ctx):
    """The snapshot names the sections a rewrite touches, not just a headline."""
    snaps = _snapshots(ctx)
    if not snaps:
        return None, "no snapshots to inspect"
    newest = _text(snaps[0]).lower()
    want = ["headline", "about", "experience"]
    missing = [w for w in want if w not in newest]
    if missing:
        return False, f"newest snapshot does not cover: {', '.join(missing)}"
    return True, "newest snapshot covers headline, about and experience"


@check("nothing_written_in_skill_dir")
def _(ctx):
    """Updating the skill must never be able to destroy someone's recovery copy."""
    skill = ctx.get("skill")
    if not skill or not os.path.isdir(skill):
        return None, "skill directory not supplied"
    hits = []
    for root, dirs, files in os.walk(skill):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "evals"}]
        for f in files:
            if f.startswith("snapshot-") or ".linkedin-profile" in root:
                hits.append(os.path.relpath(os.path.join(root, f), skill))
    if hits:
        return False, "run state written inside the skill: " + ", ".join(hits[:5])
    return True, "no run state inside the skill directory"


@check("no_author_terms_in_outputs")
def _(ctx):
    """Residue from the profile this skill was built against, leaking into someone else's."""
    snaps = _snapshots(ctx)
    if not snaps:
        return None, "no snapshots to inspect"
    found = {}
    for s in snaps:
        for m in set(x.lower() for x in AUTHOR_TERMS.findall(_text(s))):
            found.setdefault(m, os.path.basename(s))
    if found:
        return False, "author vocabulary present: " + ", ".join(
            f"{k} in {v}" for k, v in list(found.items())[:5])
    return True, f"no author vocabulary across {len(snaps)} snapshot(s)"


@check("snapshot_matches_persona")
def _(ctx):
    """The snapshot describes the person who ran it."""
    terms = [t.strip().lower() for t in (ctx.get("persona_terms") or []) if t.strip()]
    if not terms:
        return None, "no persona terms supplied"
    snaps = _snapshots(ctx)
    if not snaps:
        return None, "no snapshots to inspect"
    blob = " ".join(_text(s) for s in snaps).lower()
    hit = [t for t in terms if t in blob]
    if not hit:
        return False, f"none of the persona terms appear: {', '.join(terms)}"
    return True, f"persona present: {', '.join(hit)}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", help="the run's .linkedin-profile directory")
    ap.add_argument("--skill", help="the skill directory, to confirm nothing was written into it")
    ap.add_argument("--persona-terms", default="", help="comma-separated")
    ap.add_argument("--checks", default="", help="comma-separated; default all")
    ap.add_argument("--negate", default="", help="comma-separated; these pass when they fail")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.list:
        for n, fn in sorted(CHECKS.items()):
            print(f"{n:32} {(fn.__doc__ or '').strip().splitlines()[0]}")
        return 0

    ctx = {"state": a.state, "skill": a.skill,
           "persona_terms": [t for t in a.persona_terms.split(",") if t.strip()]}
    names = [c for c in a.checks.split(",") if c.strip()] or sorted(CHECKS)
    negate = {c.strip() for c in a.negate.split(",") if c.strip()}

    results, failed = [], 0
    for n in names:
        if n not in CHECKS:
            print(f"unknown check: {n}", file=sys.stderr)
            return 2
        passed, evidence = CHECKS[n](ctx)
        if n in negate and passed is not None:
            passed = not passed
            evidence = f"(negated) {evidence}"
        results.append({"text": n, "passed": passed, "evidence": evidence})
        if passed is False:
            failed += 1

    if a.json:
        print(json.dumps(results, indent=1))
    else:
        for r in results:
            mark = "n/a " if r["passed"] is None else ("PASS" if r["passed"] else "FAIL")
            print(f"{mark}  {r['text']:32} {r['evidence']}")
        na = sum(1 for r in results if r["passed"] is None)
        print(f"\n{len(results) - failed - na}/{len(results) - na} passed, {na} n/a")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
