# AGENTS.md

This repository is a marketplace of Claude Code skills. Two agents work on it: Claude Code and
Codex CLI.

```
.claude-plugin/marketplace.json          the library
tools/check_no_personal_data.py          runs across every plugin
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/skills/<skill>/         SKILL.md, scripts, references, evals, tests
```

Current work is in `plugins/job-search/skills/job-search/`. Paths below are relative to it
unless stated otherwise.

## If you are Codex

You are the **independent reviewer**. You have not been part of the conversation that produced
this skill, and that is exactly why your read is worth having.

**First: check for mail.**

```
.handoffs/skill-dev/to-codex/latest.md
```

If that file exists, it contains your brief. Read it, then read whatever it points at — usually
`SKILL.md` and files under `references/`.

**Then: reply.** Write your response to:

```
.handoffs/skill-dev/from-codex/latest.md
```

and copy it to `.handoffs/skill-dev/archive/<UTC-timestamp>-from.md`.

The message format and the rules are in `.handoffs/skill-dev/PROTOCOL.md`. Read it once before
your first reply.

**What is useful from you:**

- Where the instructions assume something a stranger would not know
- Where a step cannot actually be followed as written
- Scripts referenced that do not exist, or paths that disagree between files
- Where the skill would produce a bad outcome for a user who is not its author

**What is not useful:** agreeing. Claude wrote this and cannot see its own assumptions. If it
reads fine to you, say which parts you verified by actually trying to follow them, rather than
which parts sounded reasonable.

## The acceptance contract

`docs/ACCEPTANCE.md` (v1) is the release standard: ten invariants A01-A10, the regression cases
each requires, and the exit criteria. It supersedes ad hoc rules. A fix is not done because a
test passes; it is done when its invariant's cases are exercised and recorded in the acceptance
matrix.

Owner-approved scope exceptions are listed at the top of that file. Criteria are not weakened to
accommodate current behaviour -- a conflict gets reported, not quietly dropped.

## Checks you can run

Both are offline except where noted, and neither writes into the skill directory.

From `plugins/job-search/skills/job-search/`:

```
python3 tests/test_gates.py                 the gate must fail closed
python3 tests/test_package_gate.py          drives the real packaging entry point
                                            against absent, unread, stale, failed,
                                            dead-link and unresolved-location records
python3 tests/test_grader_calibration.py    the grader must disagree with a broken run
python3 tests/test_binding.py               one approval, one posting, one candidate
python3 tests/test_location.py              location constraints compose
python3 tests/test_entry_paths.py           both ways in reach the same pipeline
python3 tests/test_coverage.py              an empty result says what it is about
python3 tests/test_clean_install.py         installs and runs outside the source tree
python3 tests/test_frontmatter.py           the skill's own metadata must parse
python3 scripts/validate_profile.py --file examples/profile.example.json
```

From the repository root:

```
python3 tools/check_no_personal_data.py     no single user's identity in any plugin
```

State goes to `$JOB_SEARCH_STATE` if set, otherwise `.claude/job-search/` under the working
directory. Set it to a temporary directory to exercise the scripts without touching anything:

```
export JOB_SEARCH_STATE=$(mktemp -d)
cp examples/profile.example.json "$JOB_SEARCH_STATE/profile.json"
```

**Do not** commit, push, or edit files outside `.handoffs/skill-dev/from-codex/` and
`.handoffs/skill-dev/archive/`. Report findings; do not apply them.

## Content rules

No secrets. No real names of people or employers. No compensation figures. This channel is about
the skill, not about anyone's job search.
