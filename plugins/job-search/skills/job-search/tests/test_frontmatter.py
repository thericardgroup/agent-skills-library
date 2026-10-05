#!/usr/bin/env python3
"""The skill's own metadata has to parse.

Acceptance contract: docs/ACCEPTANCE.md v1, A09 and A10.

A SKILL.md whose YAML frontmatter fails to parse still loads -- with every
field silently dropped. The skill keeps its directory name and loses its
description, which is the entire mechanism by which Claude knows when to use
it. Nothing errors and nothing warns; the skill simply never triggers.

This was live in the first published commit. A colon followed by a space inside
an unquoted scalar ("If they know: build a profile") ends the value early, and
embedded double quotes do the same. Both read perfectly well to a human.

No network. Run: python3 tests/test_frontmatter.py
"""
import os, re, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


path = os.path.join(SKILL, "SKILL.md")
raw = open(path, encoding="utf-8").read()

m = re.match(r'^---\n(.*?)\n---\n', raw, re.S)
check("SKILL.md opens with a frontmatter block", bool(m))
if not m:
    sys.exit(1)
fm = m.group(1)

fields = {}
for line in fm.splitlines():
    k, _, v = line.partition(":")
    if _ and not line.startswith(" "):
        fields[k.strip()] = v.strip()

check("name is present", bool(fields.get("name")), fields.get("name", ""))
check("description is present", bool(fields.get("description")))

# The two constructions that break an unquoted YAML scalar, whatever a human
# reads. Quoting the value would also work, but plain scalars are what the
# rest of the ecosystem uses and are easier to keep correct.
for field in ("name", "description"):
    val = fields.get(field, "")
    check(f"{field} has no colon-space, which ends the value early",
          ": " not in val, repr(val[max(0, val.find(": ") - 24): val.find(": ") + 24])
          if ": " in val else "")
    check(f"{field} has no quote characters",
          '"' not in val and "'" not in val)

check("description is within the 1024-character limit",
      len(fields.get("description", "")) <= 1024,
      f"{len(fields.get('description', ''))} chars")
check("name is a valid skill identifier",
      bool(re.fullmatch(r'[a-z0-9-]{1,64}', fields.get("name", ""))))

# Parse it the way a YAML reader would, if one is available.
try:
    import yaml
    parsed = yaml.safe_load(fm)
    check("a real YAML parser reads every field",
          isinstance(parsed, dict) and parsed.get("name") and parsed.get("description"),
          str(list(parsed) if isinstance(parsed, dict) else parsed))
except ImportError:
    print("  n/a   a real YAML parser reads every field  (pyyaml not installed)")
except Exception as e:
    check("a real YAML parser reads every field", False, f"{type(e).__name__}: {e}")

print(f"\n{len(passed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
