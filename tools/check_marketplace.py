#!/usr/bin/env python3
"""Fail if the marketplace offers something a user cannot actually install.

Every entry in .claude-plugin/marketplace.json pins to a git ref so that pushing to the default
branch is not the same as shipping. That protection only works if the ref exists. An entry
pinned to a tag nobody cut looks correct in review, passes JSON validation, and fails for the
first person who tries to install it.

This has already happened once in this repository: a whole plugin reached the public marketplace
pinned to a tag that was never created, inside a commit about something else.

Run before every push. Exit 1 means do not push.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKETPLACE = os.path.join(ROOT, ".claude-plugin", "marketplace.json")


def _git(*args):
    try:
        out = subprocess.run(["git", "-C", ROOT, *args],
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _tags():
    out = _git("tag")
    return set(out.splitlines()) if out else set()


def _ref_exists(ref, tags):
    """A ref may be a tag, a branch, or a commit. Tags are the intended form."""
    if ref in tags:
        return True, "tag"
    if _git("rev-parse", "--verify", "--quiet", f"refs/heads/{ref}") is not None:
        return True, "branch"
    if _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
        return True, "commit"
    return False, None


def check():
    problems = []
    notes = []

    if not os.path.exists(MARKETPLACE):
        return [("marketplace.json", "missing")], []

    try:
        with open(MARKETPLACE, encoding="utf8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return [("marketplace.json", f"does not parse: {exc}")], []

    tags = _tags()
    if not tags:
        notes.append("no git tags found; ref checks may be running outside a clone")

    plugins = data.get("plugins") or []
    if not plugins:
        problems.append(("marketplace.json", "lists no plugins"))

    seen = set()
    for entry in plugins:
        name = entry.get("name") or "<unnamed>"
        where = f"marketplace entry '{name}'"

        if name in seen:
            problems.append((where, "duplicate plugin name"))
        seen.add(name)

        for field in ("name", "description", "source"):
            if not entry.get(field):
                problems.append((where, f"missing '{field}'"))

        src = entry.get("source") or {}
        path = src.get("path")
        ref = src.get("ref")

        # The pinned ref must resolve, and should be a tag.
        if not ref:
            problems.append((where, "no 'ref' — an unpinned entry ships main to installed users"))
        else:
            exists, kind = _ref_exists(ref, tags)
            if not exists:
                problems.append((
                    where,
                    f"ref '{ref}' does not exist — install will fail. "
                    f"Cut the tag, or remove the entry until you do."))
            elif kind != "tag":
                problems.append((
                    where,
                    f"ref '{ref}' is a {kind}, not a tag — a push to it reships to installed users"))

        # The path must point at a real plugin.
        if not path:
            problems.append((where, "no 'path'"))
            continue

        plugin_dir = os.path.join(ROOT, path)
        if not os.path.isdir(plugin_dir):
            problems.append((where, f"path '{path}' is not a directory"))
            continue

        manifest_path = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
        if not os.path.exists(manifest_path):
            problems.append((where, f"no plugin.json under '{path}'"))
            continue

        try:
            with open(manifest_path, encoding="utf8") as fh:
                manifest = json.load(fh)
        except (OSError, ValueError) as exc:
            problems.append((where, f"plugin.json does not parse: {exc}"))
            continue

        if manifest.get("name") != name:
            problems.append((
                where,
                f"name disagrees with its manifest: '{name}' here, "
                f"'{manifest.get('name')}' in plugin.json"))

        # A tag of the form <name>--vX.Y.Z should match the manifest version.
        version = manifest.get("version")
        if ref and version and ref.startswith(f"{name}--v"):
            tagged = ref[len(f"{name}--v"):]
            if tagged != version:
                problems.append((
                    where,
                    f"pinned tag says v{tagged}, plugin.json says v{version}"))

        # A skill directory with no SKILL.md installs as nothing.
        skills_dir = os.path.join(plugin_dir, "skills")
        if os.path.isdir(skills_dir):
            for skill in sorted(os.listdir(skills_dir)):
                sd = os.path.join(skills_dir, skill)
                if os.path.isdir(sd) and not os.path.exists(os.path.join(sd, "SKILL.md")):
                    problems.append((where, f"skill '{skill}' has no SKILL.md"))

    # A plugin on disk that nobody can install is usually deliberate during development.
    # Say so rather than failing, so work in progress is visible without blocking a push.
    plugins_root = os.path.join(ROOT, "plugins")
    if os.path.isdir(plugins_root):
        listed = {e.get("source", {}).get("path") for e in plugins}
        for d in sorted(os.listdir(plugins_root)):
            full = os.path.join(plugins_root, d)
            rel = f"plugins/{d}"
            if os.path.isdir(full) and rel not in listed:
                notes.append(f"{rel} is in the repo but not offered in the marketplace")

    return problems, notes


if __name__ == "__main__":
    problems, notes = check()
    for n in notes:
        print(f"note  {n}")
    if not problems:
        print("PASS  every marketplace entry resolves and matches its plugin")
        sys.exit(0)
    print(f"\nFAIL  {len(problems)} problem(s) in the marketplace:\n")
    for where, msg in problems:
        print(f"  {where}: {msg}")
    print("\nAn entry that does not resolve fails for the first person who installs it.")
    sys.exit(1)
