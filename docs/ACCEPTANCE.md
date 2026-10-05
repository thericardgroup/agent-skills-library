# Job-search release acceptance contract — v1

**Canonical path:** `docs/ACCEPTANCE.md` · **Version:** v1 · **Adopted:** 2026-10-01
**Source:** authored by Codex, `.handoffs/skill-dev/from-codex/acceptance-contract-v1.md`,
SHA-256 `57cf2a1246251aa1bccfbfc1ce01833bc62fff14f80a04d2aa07f6823a9ec26c` (verified on adoption).

## Owner-approved scope exceptions

**SE-1 (2026-10-01): Workday adapter is in scope for this release.** The contract scopes ATS
support to Greenhouse, Ashby, Lever and SmartRecruiters and lists new adapters as out of scope.
The owner has directed otherwise: the skill must serve professionals outside technology, and a
measurement across 30 employers in five sectors found 6/6 tech reachable and 1/24 elsewhere
(healthcare 0/6, retail 0/6, education and government 0/6). Workday is where most large
non-technology employers post. It is therefore a release prerequisite, tested under A08, and
not a silent weakening of the criterion. Taleo, SuccessFactors and iCIMS remain out of scope
and must be disclosed as unsupported.

---

Status: owner requested this contract; implementation and test evidence remain pending.
Purpose: replace isolated example fixes with explicit, reusable behavioral requirements.
This is not release approval or a claim that tests already exist. Seq 12 findings remain open
until evidence closes them. No test count alone constitutes acceptance.

## Scope and ownership

Release target: the existing job-search skill in the multi-skill marketplace. Retain its
onboarding, discovery, scoring, verification, document generation and tracking workflow.
Current implemented ATS scope: Greenhouse, Ashby, Lever and SmartRecruiters. Adding more ATS
adapters is not required for this release. Unsupported platforms and insufficient search
coverage must be disclosed, with an actionable supported alternative or an honest stop.
Do not present an unsupported-platform posting as verifiable/packageable by the current CLI.

Claude implements and maintains source, documentation and regression tests. Codex independently
reviews and tries counterexamples. Neither role's own pass claim substitutes for the other's
review. Do not commit, push or publish merely because this contract exists; existing user
authorization boundaries still apply.

Claude should adopt this contract into a maintained repository document, referenced by AGENTS.md
and the test instructions. Keep implementation details out of the end-user skill workflow.
Return the canonical path and version in every handoff. Until adoption, this mailbox copy is
the baseline. Changes to criteria must be explicit, justified and reviewed; do not weaken an
assertion solely to accommodate current behavior.

## Invariants and executable acceptance cases

A01 — One approval, one posting
Every supported file-writing entry point must enforce the same exact stable identity:
platform + board + requisition id. Derive employer/title/apply URL from the verified record or
validate explicit approved display aliases. Substring similarity is not identity. The effective
config key must agree with the approved key; a different key sharing the title is still different.
Cases: unrelated title/company, overlapping title/company, duplicate title on two requisitions,
id collision on two boards, conflicting config key and unchecked URL. Each conflict refuses
before output publication. A matching record/config succeeds.

A02 — One approval, the effective candidate and assessment
Validate the profile actually used for generation, including overrides; checking a different
on-disk profile is insufficient. Bind approval to candidate identity and the decision-relevant
profile revision. Missing legacy binding fields require re-verification, not implicit trust.
Cases: changed location, office-day limit, relevant eligibility/gap information, pay constraint,
different candidate, supplied-profile override, absent revision. Changes that affect assessment
block until reassessed; irrelevant display-only edits must follow a documented rule. Separate
posting-liveness evidence from candidate-fit attestation rather than pretending either proves
both. Record the complete generation-input revision for audit.

A03 — Current and actually reviewed evidence
Absent, expired, failed-recheck, unread, changed-body, unresolved-location and dead-link approvals
refuse generation. Review confirmation binds to the full displayed posting content. Reject
malformed/missing/future-invalid timestamps and missing required evidence with a useful error.
Cases: each invalid state separately; a valid state; read then body changes; successful check
then failed check. The explicit model/human attestation is not proof of comprehension.

A04 — Location constraints compose
Remote permission does not erase mandatory office attendance, country eligibility or day limits.
An offered alternative is different from incidental mention, negation or a requirement to attend
multiple places. Unknown information needed for a decision remains unresolved.
Cases: genuine city alternatives succeed; remote-friendly plus a mandatory excluded office fails;
negated remote does not grant permission; office days over the cap fail; unknown frequency with
a finite cap stays unresolved; irrelevant/negated acceptable-city mentions cannot rescue an
excluded mandatory location. Persist True/False/None and preserve distinct explanations.

A05 — Coherent output publication
Failed validation leaves no newly published or partially replaced deliverable. Existing output
must either be preserved intact on failure or replaced as one coherent successful package.
Cases: invalid resume section, failed letter validation, output I/O failure, rerun into a populated
directory, and a package omitting an earlier document type. Define treatment of obsolete files;
never silently leave a mixed package. Apply to package CLI, direct CLIs and exported writers.
Removing unsupported write surfaces is acceptable if documentation and callers are updated.
Pure in-memory document constructors are not security boundaries; tests target supported writes,
not arbitrary caller code that deliberately writes bytes itself.

A06 — Auditable package
Each delivered package carries exact requisition identity, generation time, immutable approval
evidence/reference, reviewed body fingerprint, effective candidate/profile revision, schema
version and file content digests. Check named files, their contents and extra/obsolete files
against the declared package. Retain enough evidence when mutable state is overwritten.
Cases: altered artifact, wrong manifest/key, missing artifact, mixed prior output, overwritten
verification state. Historical generation validity and current approval freshness are reported
separately. Individual supported outputs need equivalent provenance, not an exemption.

A07 — Grading measures execution
Use the production acceptance rules for current eligibility while keeping independent fixtures
with expected outcomes. Inspect each package's bindings and artifacts, not the existence of any
passing record. A test harness failure is an error, not success after negation.
Calibration cases: empty run; convincing transcript without artifacts; invalid approval with
artifacts; unrelated valid approval beside the wrong package; profile changed; tampered file;
valid complete run. Report not-applicable separately. A pressure request may finish successfully
after verification: assert that checks were not skipped, not that the final answer must refuse.

A08 — Discovery, scoring and tracking preserve evidence
Carry full ATS identity and complete requirement sections through normalization. Confirm employer
ownership before assigning its name. Track retrieval time separately from publication/update time.
Stale/incomplete cache cannot silently appear current; preserve the documented triage distinction
from live verification. Application suppression uses full identity and relevant statuses.
Cases: duplicate ids across boards; long-open but freshly fetched role; stale cache; failed sweep;
requirements in separate adapter sections; applied versus draft/withdrawn status; unrelated board
at guessed slug. Report coverage losses and unknowns rather than describing an empty result as
proof that no jobs exist.

A09 — Profile and user flow are executable
Document and validate minimum input for each stage. Every collected hard constraint must have a
consumer or an explicit unresolved/manual-review path. Ask for approval before saving the profile.
Test returning users, pasted supported URLs, pasted text needing a canonical URL, short valid
histories, incomplete profiles and an unsupported-sector/platform scenario. Do not invent facts
or force long employment histories just to satisfy a length check. Publish known coverage limits.

A10 — Distribution works from a clean user environment
Test the documented installation path or an equivalent local packaged-install path, followed by
one complete synthetic workflow outside the source tree with no preinstalled skill dependencies.
Include a path containing spaces and a different working directory. Test missing dependencies
with clear recovery; protect existing user state during an update. Verify manifests, referenced
files and dependency setup. Run the personal-data guard. If remote installation cannot be tested
before publication, report that precise remaining condition instead of claiming it passed.

## Efficient implementation loop

1. Map seq 12 findings to A01-A10 and inventory all supported writing boundaries once.
2. Add failing behavioral tests for the defect family before fixing it. Capture the observed
   failure and a valid neighboring case; avoid tests that merely search source wording.
3. Fix shared contracts at the narrowest common layer. Keep one source for validation rules;
   independent test fixtures must still challenge that source. Avoid a fresh bypass flag or a
   separately maintained grader approximation.
4. Work in cohesive batches: approval/content/profile binding; location/constraint decisions;
   publication/audit/grading; then distribution and end-to-end verification. Run targeted tests
   during each batch. Run the full offline suite once the batch is coherent, not after every edit.
5. After offline acceptance, run a small live smoke check per supported adapter with bounded
   requests. No real applications, employer messages or personal search data are needed. Separate
   external outages/rate limits from deterministic failures; do not weaken guards to get a pass.
6. Send one evidence-backed handoff per coherent batch. Codex will independently select fresh
   counterexamples, concentrating on changed invariants and their callers. Run the final whole
   workflow and clean-install check before asking for release acceptance.

No external-agent delegation is required by this contract. Tests use isolated temporary state
and fictional fixtures. No personal data, secrets or compensation figures belong in handoffs.

## Required handoff evidence

Include:
- Contract version/canonical path and immutable candidate identifier: commit if available, or
  digest of the reviewed source snapshot. Do not commit merely to obtain an identifier.
- Invariant IDs changed; prior finding dispositions: fixed, open, disputed or deferred, with reason.
- Regression tests and observed before/after behavior, plus valid neighboring cases.
- Commands run, exit results and concise artifact evidence. State anything not executed.
- Changed-file list, remaining limitations and a specific question for independent review.
- Acceptance matrix: A01-A10 each pass/fail/not-run/blocked, backed by evidence. 'Pass' means its
  relevant cases and supported paths were exercised, not that the implementation looks plausible.

Keep the message concise and link maintained evidence by relative file path. Do not paste whole
logs or source diffs. No 'all fixed' claim with open failing cases or untested promised paths.

## Release exit criteria

All in-scope criteria pass with recorded evidence; no known blocking correctness defects remain;
documentation describes the shipped behavior and coverage; clean installation and complete
workflow are exercised; independent review finds no remaining blocker on the same candidate.
Live checks must have a dated outcome; a blocked external check is not a pass. Any scope exception
is explicit and user-approved rather than silently removed from the matrix. Optional new adapters
and research-scale persona comparisons are outside this release, not hidden prerequisites.

This establishes a bounded release decision, not a guarantee of a bug-free or perfectly behaving
system. Future regressions become tests against these invariants rather than accumulating ad hoc
rules in SKILL.md.
