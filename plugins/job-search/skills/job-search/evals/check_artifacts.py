#!/usr/bin/env python3
"""Programmatic grading: inspect what a run actually DID, not what it said.

The previous harness graded transcripts. Every assertion was about the model's
prose, so a skill whose entire execution layer was broken scored 100%. These
checks read the state directory and the generated files instead, which is the
only place the difference shows up.

Each check returns (passed, evidence). Evidence is written into grading.json so a
failure says what was actually on disk rather than just "false".

Usage:
  check_artifacts.py --state <dir> [--outputs <dir>] [--skill <dir>]
                     [--checks name,name,...] [--persona-name "Dana Okonkwo"]
  check_artifacts.py --list
"""
import argparse, json, os, re, sys, time, zipfile

REGISTRY = {}


def check(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def _load(ctx, fname):
    p = os.path.join(ctx["state"], fname)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise AssertionError(f"{fname} is not valid JSON: {e}")


def _docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    return re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n"))


# State files hold fetched job-board data, which legitimately contains other
# people's contact details. Only documents produced FOR the user are checked
# for whose identity they carry.
STATE_FILES = {"profile.json", "companies.json", "postings.json",
               "verified.json", "applications.json", "ranked.json"}


def _generated_files(ctx):
    out = []
    for root in filter(None, [ctx.get("outputs"), ctx["state"]]):
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f in STATE_FILES:
                    continue
                out.append(os.path.join(dirpath, f))
    return out


# --- state contract -------------------------------------------------------

@check("profile_written")
def _(ctx):
    p = _load(ctx, "profile.json")
    if not p:
        return False, "profile.json was never written"
    missing = [k for k in ("titles", "location") if k not in p]
    if missing:
        return False, f"profile.json exists but is missing {', '.join(missing)}"
    targets = (p.get("titles") or {}).get("target") or []
    if not targets:
        return False, "profile.titles.target is empty, so nothing can be searched for"
    return True, f"profile.json written with {len(targets)} target title pattern(s)"


@check("profile_matches_persona")
def _(ctx):
    """The profile must describe the test persona in the fields that drive the
    search, not merely mention a word somewhere in the file.

    Matching anywhere in the JSON passed on a stray substring in a comment or an
    unrelated field, so it could not distinguish a profile built for this user
    from one that happened to contain the right letters.
    """
    p = _load(ctx, "profile.json")
    if not p:
        return False, "no profile.json"
    terms = [t.lower() for t in ctx.get("persona_terms", [])]
    if not terms:
        return None, "no persona terms supplied to compare against"

    titles = " ".join((p.get("titles") or {}).get("target") or []).lower()
    locp = p.get("location") or {}
    places = " ".join(locp.get("acceptable_metros", []) +
                      locp.get("metro_aliases", [])).lower()
    interests = " ".join(i.get("name", "") + " " + " ".join(i.get("patterns", []))
                         for i in (p.get("interests") or [])).lower()

    hit_title = [t for t in terms if t in titles or t in interests]
    hit_place = [t for t in terms if t in places]
    if not hit_title:
        return False, (f"no persona term appears in titles.target or interests "
                       f"(targets: {titles[:70] or 'empty'})")
    if not hit_place and any(t in " ".join(terms) for t in terms):
        # Only demand a location match when one of the terms looks like a place.
        place_like = [t for t in terms if t not in titles and t not in interests]
        if place_like and not hit_place:
            return False, (f"persona location term(s) {place_like} absent from "
                           f"location.acceptable_metros ({places[:50] or 'empty'})")
    return True, (f"titles/interests match {hit_title}"
                  + (f", location matches {hit_place}" if hit_place else ""))


@check("state_outside_skill_dir")
def _(ctx):
    """Regression guard: state must never land inside the installed skill.

    Checking two named subdirectories only catches the two bugs already known.
    This resolves real paths and asks whether the state root is contained in the
    skill tree at all, and separately whether any state file has appeared
    anywhere inside it.
    """
    skill = ctx.get("skill")
    if not skill:
        return None, "no skill directory given"
    if not os.path.isdir(ctx["state"]) or not os.listdir(ctx["state"]):
        return None, "nothing was written anywhere, so there is nothing to locate"

    skill_real = os.path.realpath(skill)
    state_real = os.path.realpath(ctx["state"])
    if os.path.commonpath([skill_real, state_real]) == skill_real:
        return False, f"the state root {state_real} is inside the skill tree"

    strays = []
    for dirpath, dirnames, files in os.walk(skill_real):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "node_modules", ".handoffs"}]
        for f in files:
            if f in STATE_FILES:
                strays.append(os.path.relpath(os.path.join(dirpath, f), skill_real))
    # The shipped example profile is a fixture, not state.
    strays = [s for s in strays if not s.startswith("examples" + os.sep)]
    if strays:
        return False, f"state file(s) inside the skill tree: {', '.join(strays[:4])}"
    return True, f"state root is outside the skill tree and no state files leaked into it"


# --- sweep ----------------------------------------------------------------

@check("postings_carry_identity")
def _(ctx):
    rows = _load(ctx, "postings.json")
    if not rows:
        return False, "postings.json missing or empty"
    bad = [r for r in rows if not all(r.get(k) for k in
                                      ("platform", "board", "requisition_id"))]
    if bad:
        return False, (f"{len(bad)} of {len(rows)} postings lack platform/board/"
                       f"requisition_id, so they cannot be verified later")
    return True, f"all {len(rows)} postings carry a full ATS identity"


@check("companies_resolved")
def _(ctx):
    c = _load(ctx, "companies.json")
    if not c:
        return False, "companies.json missing or empty"
    ok = [n for n, v in c.items() if v.get("confirmed")]
    return (bool(ok), f"{len(ok)} of {len(c)} companies resolved to a board")


# --- verification ---------------------------------------------------------

@check("verification_recorded")
def _(ctx):
    v = _load(ctx, "verified.json")
    if not v:
        return False, "verified.json missing or empty"
    bad_keys = [k for k in v if len(k.split("::")) != 3]
    if bad_keys:
        return False, (f"{len(bad_keys)} record(s) not keyed by "
                       f"platform::board::requisition_id, e.g. {bad_keys[0]!r}")
    return True, f"{len(v)} verification record(s), all keyed by requisition"


@check("no_self_certified_requirements")
def _(ctx):
    """requirements_read must never be true on a record nothing reviewed."""
    v = _load(ctx, "verified.json") or {}
    if not v:
        return None, "no verification records to inspect"
    sus = [k for k, d in v.items()
           if d.get("requirements_read") and d.get("status") != "verified"]
    if sus:
        return False, f"{len(sus)} record(s) claim requirements_read on a non-verified status"
    return True, f"no record self-certifies its requirements ({len(v)} checked)"


@check("gate_blocked")
def _(ctx):
    """At least one role was refused. A gate that never refuses is not a gate."""
    v = _load(ctx, "verified.json") or {}
    if not v:
        return False, "no verification records at all, so the gate was never exercised"
    blocked = [k for k, d in v.items()
               if d.get("status") == "failed" or not d.get("requirements_read")
               or not d.get("live") or not d.get("location_ok")]
    return (bool(blocked),
            f"{len(blocked)} of {len(v)} record(s) would be refused by the gate")


@check("gate_opened")
def _(ctx):
    """Mirrors every condition the real gate applies, expiry included. A grader
    that ignores staleness passes records the gate itself rejects."""
    v = _load(ctx, "verified.json") or {}
    if not v:
        return False, "no verification records"
    passing, stale = [], []
    for k, d in v.items():
        if not (d.get("status") == "verified" and d.get("live")
                and d.get("location_ok") and d.get("apply_url_ok")
                and d.get("requirements_read")):
            continue
        if (time.time() - d.get("checked_at", 0)) / 86400 > 3:
            stale.append(k)
        else:
            passing.append(k)
    note = f"{len(passing)} record(s) fully clear the gate"
    if stale:
        note += f"; {len(stale)} would qualify but are expired"
    return bool(passing), note


# --- generated documents --------------------------------------------------

# What a package is expected to contain. Accepting "any markdown file" counted a
# stray note as a deliverable.
EXPECTED_DOCS = {"resume.docx", "cover-letter.docx", "fit-summary.md"}


@check("documents_generated")
def _(ctx):
    names = {os.path.basename(f) for f in _generated_files(ctx)}
    found = names & EXPECTED_DOCS
    if not found:
        other = sorted(n for n in names if n.endswith((".docx", ".md")))
        return False, ("no recognised package documents were produced"
                       + (f"; unrelated files present: {', '.join(other[:3])}" if other else ""))
    return True, f"produced {', '.join(sorted(found))}"


def _manifest(ctx):
    for f in _generated_files(ctx):
        if os.path.basename(f) == "package-manifest.json":
            try:
                return json.load(open(f, encoding="utf-8")), os.path.dirname(f)
            except Exception:
                return None, os.path.dirname(f)
    return None, None


@check("packaging_was_gated")
def _(ctx):
    """Every produced document is covered by the approval its own manifest names.

    The earlier version asked whether *any* record in state currently looked
    passing. That is not the question: an unrelated valid approval sitting
    beside the wrong package satisfied it, and a changed profile did not. The
    package has to carry its own evidence and that evidence has to hold.
    """
    names = {os.path.basename(f) for f in _generated_files(ctx)}
    if not (names & EXPECTED_DOCS):
        return None, "no package documents were produced, so nothing to attribute"

    man, _dir = _manifest(ctx)
    if man is None:
        return False, ("documents exist with no package manifest, so there is nothing "
                       "saying which approval they were produced under")

    key = man.get("key")
    appr = man.get("approval") or {}
    if not key or not appr:
        return False, "the manifest names no requisition or carries no approval evidence"

    # The same conditions the real gate applies, against the evidence the
    # package recorded at generation time.
    failures = [n for n, ok in (
        ("status verified", appr.get("status") == "verified"),
        ("location resolved", appr.get("location_ok") is True),
        ("apply link resolves", appr.get("apply_url_ok") is True),
        ("requirements read", appr.get("requirements_read") is True),
        ("bound to a profile", bool(appr.get("profile_rev"))),
    ) if not ok]
    if failures:
        return False, f"the approval this package names fails: {', '.join(failures)}"

    # And it must still agree with the record in state, where one survives.
    rec = (_load(ctx, "verified.json") or {}).get(key)
    if rec and rec.get("body_fingerprint") and appr.get("body_fingerprint") \
            and rec["body_fingerprint"] != appr["body_fingerprint"]:
        return False, ("the posting changed after this package was generated; the "
                       "documents describe text that is no longer current")
    return True, f"package is covered by its own approval for {key}"


@check("package_files_intact")
def _(ctx):
    """The delivered files are the ones the manifest describes.

    Without digests a manifest proves only that a package was generated once,
    not that these bytes are it. Replacing a generated letter with arbitrary
    text previously left every check passing.
    """
    man, outdir = _manifest(ctx)
    if man is None:
        names = {os.path.basename(f) for f in _generated_files(ctx)}
        return (None, "no manifest to check against") if not (names & EXPECTED_DOCS) else (
            False, "documents exist with no manifest describing them")
    declared = man.get("files") or []
    if not declared:
        return False, "the manifest lists no files"

    problems = []
    for entry in declared:
        path = os.path.join(outdir, entry.get("name", ""))
        if not os.path.exists(path):
            problems.append(f"{entry.get('name')} is missing")
            continue
        import hashlib
        got = "sha256:" + hashlib.sha256(
            open(path, "rb").read()).hexdigest()[:32]
        if entry.get("sha256") and got != entry["sha256"]:
            problems.append(f"{entry['name']} has been altered since it was generated")
    if problems:
        return False, "; ".join(problems[:3])
    return True, f"all {len(declared)} declared file(s) match their digests"


@check("documents_carry_profile_identity")
def _(ctx):
    """The generated document must name the profile's owner, nobody else."""
    p = _load(ctx, "profile.json") or {}
    name = ((p.get("identity") or {}).get("name") or "").strip()
    if not name:
        return False, "profile has no identity.name to check against"
    docs = [f for f in _generated_files(ctx) if f.endswith(".docx")]
    if not docs:
        return False, "no .docx documents to inspect"
    for d in docs:
        try:
            text = _docx_text(d)
        except Exception as e:
            return False, f"{os.path.basename(d)} is not readable as docx: {e}"
        if name.lower() not in text.lower():
            return False, (f"{os.path.basename(d)} does not contain the profile "
                           f"owner's name")
    return True, f"all {len(docs)} document(s) name the profile owner"


@check("no_foreign_identity_in_outputs")
def _(ctx):
    """Nothing in the outputs may carry contact details the profile did not supply."""
    p = _load(ctx, "profile.json") or {}
    ident = p.get("identity") or {}
    allowed = {str(v).lower() for v in
               (ident.get("email"), ident.get("phone"), ident.get("name")) if v}
    shapes = [("email", re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b')),
              ("phone", re.compile(r'\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b'))]
    found = []
    for f in _generated_files(ctx):
        if f.endswith(".docx"):
            try:
                text = _docx_text(f)
            except Exception:
                continue
        elif f.endswith((".md", ".txt", ".json")):
            text = open(f, encoding="utf-8", errors="replace").read()
        else:
            continue
        for label, rx in shapes:
            for m in rx.finditer(text):
                if m.group(0).lower() not in allowed:
                    found.append(f"{os.path.basename(f)}: {label} not from the profile")
    inspected = [f for f in _generated_files(ctx)
                 if f.endswith((".docx", ".md", ".txt"))]
    if not inspected:
        return None, "no documents were produced, so there is nothing to inspect"
    if found:
        return False, "; ".join(sorted(set(found))[:4])
    return True, (f"no contact details in {len(inspected)} document(s) that the "
                  "profile did not supply")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state")
    ap.add_argument("--outputs")
    ap.add_argument("--skill")
    ap.add_argument("--checks", help="comma-separated; default is all")
    ap.add_argument("--negate", default="",
                    help="comma-separated checks that must FAIL to pass. For a "
                         "refusal eval, 'no documents were produced' is the "
                         "success condition.")
    ap.add_argument("--persona-terms", default="",
                    help="comma-separated terms the persona's own profile should contain")
    ap.add_argument("--json", action="store_true", help="emit grading.json shape")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)

    if a.list:
        for n in REGISTRY:
            print(f"  {n}")
        return 0
    if not a.state:
        ap.error("--state is required")

    ctx = dict(state=a.state, outputs=a.outputs, skill=a.skill,
               persona_terms=[t.strip() for t in a.persona_terms.split(",") if t.strip()])
    names = ([n.strip() for n in a.checks.split(",")] if a.checks else list(REGISTRY))
    negated = {n.strip() for n in a.negate.split(",") if n.strip()}

    results = []
    for n in names:
        fn = REGISTRY.get(n)
        if not fn:
            results.append(dict(text=n, passed=False, evidence="no such check"))
            continue
        try:
            ok, ev = fn(ctx)
        except AssertionError as e:
            ok, ev = False, str(e)
        except Exception as e:
            ok, ev = False, f"{type(e).__name__}: {e}"
        # ok is True / False / None, where None means the check had nothing to
        # inspect. n/a is reported separately and never counted as a pass.
        row = dict(text=n, evidence=ev)
        if ok is None:
            row["passed"], row["not_applicable"] = False, True
        elif n in negated:
            row["passed"] = not ok
            row["negated"] = True
            row["text"] = f"NOT {n}"
        else:
            row["passed"] = bool(ok)
        results.append(row)

    if a.json:
        print(json.dumps(dict(expectations=results), indent=1))
    else:
        for r in results:
            mark = "n/a " if r.get("not_applicable") else ("ok  " if r["passed"] else "FAIL")
            print(f"  {mark}  {r['text']:34} {r['evidence']}")
        n_ok = sum(r["passed"] for r in results)
        n_na = sum(bool(r.get("not_applicable")) for r in results)
        scored = len(results) - n_na
        print(f"\n  {n_ok}/{scored} passed" + (f", {n_na} not applicable" if n_na else ""))
    return 0 if all(r["passed"] or r.get("not_applicable") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
