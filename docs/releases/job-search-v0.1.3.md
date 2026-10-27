# job-search 0.1.3

**Type:** patch release under SE-2 (`docs/ACCEPTANCE.md`), wording only. Ships with the known
gaps below under owner-approved scope exception SE-3.
**Baseline:** `job-search--v0.1.2`. **Tag:** `job-search--v0.1.3`.

## What changed

The first-run message said everything the skill learns about you "stays on your machine." That
was not fully true. What you share in the chat -- your resume, your answers, postings you paste --
is sent to Anthropic like any Claude conversation. The message and the README now say what goes
where:

- What the skill saves (profile, scored roles, progress) stays in `.claude/job-search/` on your
  computer.
- The skill's own scripts contact job boards and employers' careers pages to read postings, and
  the npm package registry once, at first use, to download the document libraries. A job-board
  request names only the employer or posting being looked up; none carries your resume, profile
  or answers.
- What you type or paste into the chat reaches Anthropic and is handled under your Claude
  account's privacy settings.

The README also links the step-by-step setup guides (desktop app, adding the library, Python,
Node, installing and using the skill) and states the minimum Python version (3.8).

Plugin files: `plugins/job-search/README.md`, `plugins/job-search/skills/job-search/SKILL.md`,
`plugins/job-search/.claude-plugin/plugin.json` (version). No script, test, eval, dependency or
stored-state change.

Marketplace file: only the `job-search` `ref` moves, from `job-search--v0.1.2` to
`job-search--v0.1.3`. The `.claude-plugin/marketplace.json` diff from the baseline tag also
shows `linkedin-profile` removed; that is 449148d, already live on `main` since 2026-10-16 and
not part of this plugin's release.

## Deferred under SE-2

- **Workday adapter** (SE-1, A08). Not in this release.
- **Clean-Windows install proof** (A10). Still unproven; see the status correction at the top of
  `docs/ACCEPTANCE.md`.

## Known defect carried from 0.1.2

**A05, failed output I/O can leave a mixed package.** `scripts/docgen/package.js` stages the
package, then copies each file into the output folder one by one with no rollback. If a copy
fails partway, an earlier file may already have replaced the previous version, and no manifest
is written. Found by Codex review 21 with an injected copy failure. Unchanged by this release;
fixing it changes behavior, so it belongs in a release outside SE-2.

## Rollback

Move the marketplace `ref` back to `job-search--v0.1.2`. User state in `.claude/job-search/` is
not touched by either version.

## Acceptance matrix (basis: SE-2; known gaps carried under SE-3)

Candidate: the release commit tagged `job-search--v0.1.3`. Commands are in `AGENTS.md`. "Cited
tests pass" means the named suite passes; it is not a claim that every case the invariant lists
is exercised. Cases not shown exercised are named as unproven.

| Invariant | Status | Evidence |
|---|---|---|
| A01 one approval, one posting | pass | `test_binding.py` 21/0, `test_package_gate.py` 17/0 |
| A02 effective candidate | pass | `test_binding.py` 21/0 |
| A03 current, reviewed evidence | pass | `test_gates.py` 36/0, `test_package_gate.py` 17/0 |
| A04 location composes | pass | `test_location.py` 27/0 |
| A05 coherent publication | **fail** (output I/O failure case; see above) | cited test `test_package_gate.py` 17/0 does not exercise it |
| A06 auditable package | partial: cited tests pass; altered-artifact, missing-artifact and overwritten-state cases unproven | `test_package_gate.py` 17/0 |
| A07 grading measures execution | pass | `test_grader_calibration.py` 16/0 |
| A08 discovery, scoring, tracking | partial: Workday case **not run (SE-2)**; stale-cache, cross-board identity, application-status and adapter-section cases unproven | `test_coverage.py` 10/0 |
| A09 profile and user flow | partial: returning-user, pasted-URL, pasted-text and save-approval flows unproven | `test_entry_paths.py` 9/0, `validate_profile.py` on the example |
| A10 clean distribution | partial: relocated install passes; clean-Windows case **not run (SE-2)**; remote `/plugin marketplace add` not run before publication | `test_clean_install.py` 19/0, 1 not run; `check_no_personal_data.py` pass |

Also: `test_frontmatter.py` 9/0. Evals unchanged since `job-search--v0.1.2`.

Run 2026-10-26 on macOS. `test_clean_install.py` needs network access (it installs the npm
libraries) and must run with `JOB_SEARCH_STATE` unset.

`tools/check_marketplace.py` passes at the baseline. While the candidate's `plugin.json` says
0.1.3 and the pin still names `job-search--v0.1.2`, it fails on the version mismatch, as
expected. It is re-run after the tag exists and the pin moves, per SE-2.
