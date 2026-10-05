#!/usr/bin/env python3
"""The one place that decides where this user's data lives.

Every script imports from here. When state had two roots, a verification written by
one script was invisible to the gate in another, and the gate silently passed. One
function, one answer, no exceptions.

Resolution order:
  1. $JOB_SEARCH_STATE          explicit override, for tests and multiple searches
  2. <cwd>/.claude/job-search/  the default a user never has to think about

Never inside the skill directory. The skill is shared code; state is one person's
data, and installing an update must not touch it.
"""
import os, sys, json, tempfile

FILES = ("profile.json", "companies.json", "postings.json",
         "verified.json", "applications.json")


def state_root():
    override = os.environ.get("JOB_SEARCH_STATE")
    root = os.path.abspath(override) if override else os.path.join(
        os.getcwd(), ".claude", "job-search")
    os.makedirs(root, exist_ok=True)
    return root


def state_file(name):
    if name not in FILES:
        raise ValueError(f"unknown state file {name!r}; expected one of {FILES}")
    return os.path.join(state_root(), name)


def load(name, default=None):
    try:
        with open(state_file(name), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {} if default is None else default
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"{state_file(name)} is not valid JSON ({e}).\n"
            "Fix or delete the file; deleting loses only cached data, not your profile."
        )


def save(name, data):
    """Atomic. A half-written profile after an interrupt is worse than no profile."""
    path = state_file(name)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        os.path.exists(tmp) and os.unlink(tmp)
        raise


def require_profile(stage="search"):
    """Scripts that filter or rank must not guess what the user wants.

    Validated on load, not merely parsed. A profile with an uncompilable regex
    or a pay floor written as a string produces a search that runs and is
    quietly wrong, which is worse than one that refuses.
    """
    p = load("profile.json")
    if not p:
        raise SystemExit(
            "No profile yet. This script ranks against the user's own criteria and has "
            "no defaults to fall back on.\n"
            f"Expected: {state_file('profile.json')}\n"
            "Run the onboarding interview in SKILL.md first."
        )
    # Imported here rather than at module scope: the validator imports this file.
    from validate_profile import validate
    errors, warnings = validate(p, stage)
    for w in warnings:
        print(f"  warn  {w}", file=sys.stderr)
    if errors:
        raise SystemExit(
            f"The profile at {state_file('profile.json')} cannot be used for '{stage}':\n"
            + "\n".join(f"  - {e}" for e in errors)
            + "\n\nFix these, or re-run the onboarding interview."
        )
    return p


if __name__ == "__main__":
    root = state_root()
    print(root)
    for f in FILES:
        print(f"  {'present' if os.path.exists(os.path.join(root, f)) else 'not yet'}  {f}")
