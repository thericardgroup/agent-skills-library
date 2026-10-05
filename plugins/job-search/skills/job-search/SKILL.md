---
name: job-search
description: Run a rigorous job search, whether or not the person knows what role they want. If they know: build a profile by interview, find the employers hiring it, read their applicant tracking systems directly, score openings against stated requirements, verify every role is still live before investing in it, and generate tailored resumes, cover letters and interview prep. If they do not know: work backwards from what they have actually done to the two or three role families their record supports, with the evidence for each, then run the same search on whichever they pick. Use whenever someone mentions job hunting, applying to roles, being laid off, changing careers, not knowing what to do next, tailoring a resume or cover letter, whether they fit a job description, how to find openings, why applications are not converting, or tracking what they have sent - even if they never say "job search". Also when someone pastes a job description and asks what you think, or asks to be talked out of applying.
---

# Job Search

A job search fails in two ways. The cheap failure is not finding roles. The expensive failure is
spending months on roles you were never going to win. This skill is built mostly against the
second one.

The single highest-value action in this entire workflow is **reading a posting's stated
requirements before recommending it**. Scoring narrows thousands to twenty; reading confirms five.
Every bad recommendation this method ever produced came from skipping the read. No amount of
scoring sophistication substitutes for it.

## Before anything else

Run `scripts/preflight.py`. It creates the state directory, installs the document libraries, and
reports what is missing. **Do not make the user do setup.** If something cannot be fixed
automatically, mention it once, in plain language, at the moment it actually matters — a missing
Node install is irrelevant until they package a resume.

Assume the person is new to Claude Code. They may not know what a skill is, what a terminal path
means, or that files are being written on their behalf. None of that should ever surface. Talk
about what you are doing for them, not about the machinery doing it.

This skill needs **Claude Code** specifically: it fetches live job boards, which claude.ai
restricts and the Claude API blocks entirely.

## Two ways in, one pipeline

The user says something like "help me find a job", or pastes a posting, or says they have no
idea what they are looking for. They will not name a stage. Work out where they are and do the
next useful thing.

```
                    ┌─ knows the target ──────────────┐
onboard ────────────┤                                 ├─→ discover → sweep → score → VERIFY → package → track
                    └─ does not ──→ ORIENT ───────────┘                                 ↑
                                                                                  blocking gate
```

Both routes end in the same place: `profile.titles.target`. One fills it because the user said
so, the other derives it from their own history. Everything downstream is identical.

**Never ask which route they want.** "Do you know what you are looking for?" is a question that
makes someone who does not know feel behind. Their first message almost always tells you —
"I want senior PM roles" is one route, "I got laid off and I'm not sure what's next" is the
other. When it is genuinely unclear, start the interview; the answer arrives by question two.

That sequence is architecture, not a menu. Never present it as one. Check the state directory
first — a returning user should never be re-interviewed, and should be greeted with where they
left off.

State lives in `.claude/job-search/` under the working directory: `profile.json` (who they are
and what they cannot do), `companies.json` (company to ATS mapping), `postings.json` (last
sweep), `verified.json` (what the gate reads), `applications.json` (what was sent and what
happened). `scripts/statepath.py` is the only thing that decides that location, and every script
imports it — when two files each decided for themselves, records written by one were invisible
to the other and the gate passed on an empty set. `references/schemas.md` documents the shape of
each file; `$JOB_SEARCH_STATE` overrides the root for tests or a second search.
`scripts/validate_profile.py` checks a profile before anything depends on it, and the scoring
and packaging stages refuse an invalid one — a regex that does not compile or a pay floor
written as a string produces a search that runs and is quietly wrong.

Nothing is written into the skill's own directory. The skill is shared code and state is one
person's data, so installing an update must never touch it.

**Never show the user raw JSON.** Summarize in prose. The files are an implementation detail.

## The first thirty seconds

One short message before anything else. It has three jobs, and a fourth it must not do.

**Say what this is and who made it, in one line.** Credit belongs in a clause, not a paragraph:
*"This is the job-search skill from The Ricard Group — free, and everything it learns about you
stays on your machine."* That is the whole brand moment. A user who just got laid off opened
this at eleven at night; the first thing they read should be about them, not about us.

**Say what happens next and what it costs.** "The setup is a conversation, about fifteen
minutes, and you can stop anywhere and pick up later" removes the two fears people actually
have: that this will take all evening, and that stopping means starting over.

**Give the fast path immediately.** Someone who knows what they want should not sit through an
interview to prove it:

> *"If you already know the kind of role you're after, tell me and we'll go straight to
> finding them. If you don't, that's the more common case and we'll work it out from what
> you've already done — either way, start wherever you like."*

That sentence is doing the real work. It tells the undecided person they are normal, and it
lets the decided person skip ahead, in the same breath, without either being asked to
self-identify.

**What it must not do:** open with a thank-you, a feature list, or a question. Gratitude for
downloading is a request for the user's attention before anything has been given. A feature
list is a menu, and the pipeline is not a menu. And an opening question — especially "do you
know what you're looking for?" — puts the burden back on someone who came here because they
were stuck.

**Only on a first run.** A returning user gets where they left off, not the introduction
again — check the state directory before saying anything.

### The message

Adapt the wording; keep the shape.

```
This is the job-search skill from The Ricard Group. It's free, and everything it
learns about you stays on your machine -- nothing leaves except the requests that
read job boards on your behalf.

Setup is a conversation, around fifteen minutes, and you can stop anywhere and
pick it up later.

If you already know the kind of role you want, say so and we'll go straight to
finding them. If you don't, that's the more common place to start, and we'll work
it out from what you've already done.

Whichever is easiest: paste a posting you're considering, share your resume, or
just tell me what you've been doing lately.
```

The last line matters as much as the credit. It is an open door rather than a question,
and it offers three on-ramps of increasing ease, so the person with nothing to hand still
has something they can answer. "Just tell me what you've been doing lately" is the one most
people take.

Then stop talking and do something useful.

## Stage 1: Onboard

Four moves: **prove value → interview → confirm → set a rhythm.** Fifteen to twenty minutes,
ending with a profile good enough that every later stage is honest rather than flattering.

Some users have neither a posting nor a resume — they have not started, which is the real cold
start. Do not ask them for a document before you have given them anything. Ask what they did
most recently and who paid them for it, then build the timeline conversationally. See
`references/onboarding-interview.md`, "When the user has nothing to hand"; for many of these
users that reconstructed timeline is the first deliverable and is worth more than the ranking
they came for.

```
User: "help me find a job"
→ Check for an existing profile; if present, show it and ask what changed
→ Prove value in the first two minutes, before any interview
→ Ask five questions, one at a time
→ Show the profile, get approval, save
→ "Say 'check my search' any time and I'll pull what's new."
```

### Prove value first, always

This is the step most likely to be skipped and the one that decides whether the person finishes.
A stranger will not answer twenty minutes of questions for a tool that has not yet done anything
for them.

Ask: *"Is there a job posting you're already looking at? Paste it in."*

Then analyse it — honestly, including whether they should not bother. Even with almost nothing in
the profile, you can read the stated requirements and say something true and useful. That two
minutes is what earns the interview.

If they have no posting to hand, ask for a resume and **reflect their history back to
them**: the timeline, any unexplained gaps, and anything buried in an early role that they have
stopped mentioning. People routinely drop the roles that contain their only evidence of managing
people or operating at scale. Surfacing one of those lands as well as a fit analysis does.

Narrate what you are doing while you do it. This is the moment they decide the rest is worth it.

### Then interview — five questions, one at a time

Wait for a full answer before asking the next. If they seem pressed for time, compress to the
first three, but never fewer than three — those are the ones that drive every filter downstream.

1. **"What kind of role are you going after? A title is fine, or just describe it."**
   *Unless they have already said they do not know.* For a career-changer this question is
   unanswerable, and asking it first produces a stall or a guess that every later stage then
   treats as fact. Take it last instead and turn it into a proposal: run the other questions,
   then name the two or three title families their own history points at and let them react.
   Reacting to something concrete is far easier than generating it from nothing.
2. **"Where can you work? Remote only, or are there places you could go in to?"** — Follow it
   with travel ceiling, whether they would relocate, and whether they need visa sponsorship.
   All three go in `profile.constraints` and each one silently filters roles later; a profile
   without them gets a validator warning rather than a guess. Usually the
   highest-leverage filter in the whole search. Location alone can remove most of a market.
3. **"What do these postings keep asking for that you don't have?"** — Uncomfortable, and nobody
   volunteers it. Ask plainly and without judgment. This is what generates the disqualifying
   filters, and it is the difference between a tool that protects them and one that flatters
   them. Frame it that way if they hesitate: naming it here is what stops them spending a month
   on a role that was never going to happen.
4. **"What are you targeting for compensation?"** — Then, separately and only in the file, the
   lowest they would accept. **The floor never leaves the profile.** A candidate who names their
   floor is offered their floor.
5. **"Tell me one thing you did that you're proud of — and how you know it worked."** — The
   second half is the point. A number they cannot defend collapses under one follow-up question.
   This also teaches them the standard for every other claim you will collect later.

Read `references/onboarding-interview.md` for the deeper sequence used when someone wants to go
further, and for what to do when they have very little to work with.

### Confirm before saving

Show the profile in plain language and wait for an explicit yes. This is not ceremony — reading
it back routinely surfaces a correction they would never have volunteered, and it is the moment
they realise you understood them.

Never write silently. Never show them raw JSON.

### Set a rhythm

Offer something like: *"Say 'check my search' whenever you want, and I'll pull what's new and
flag anything worth your time."* If they want a specific day, store it.

See `references/gotchas.md` for the failure patterns this sequence is built to avoid.

## Stage 1b: Orient — only when they do not know what they want

Skip this entirely for someone who named their targets. For everyone else it is the most
valuable thing the skill does, and it runs on nothing but what the interview already produced.

**The move is to work backwards from evidence to lanes.** Someone who cannot answer "what role
do you want?" can almost always answer "what did you do, and how do you know it worked" — and
two or three role families fall out of those answers. A claims specialist who owned renewal
risk decisions is looking at claims, adjusting, and underwriting whether or not they have ever
said the word "underwriting" out loud.

Name three or four families. For each, say in one line what in *their* history carries it, and
what they would be missing. Then let them react. Reacting to something concrete is far easier
than generating it from nothing, and their correction is usually the most informative thing
they say in the whole interview.

```
"Three lanes your record already supports:

 Claims consulting — seven years adjudicating auto and property, and the
   reopened-rate number is the kind of thing this work is measured on.
   You would be missing commercial lines exposure.
 ..."
```

Write the result to `profile.titles` with `source: "derived"` and the evidence for each family
in `derived_from`. The schema requires that evidence, because a lane nobody can see the
reasoning for is a lane nobody can argue with.

**A derived target is a hypothesis, not a decision.** After the first ranking, come back to it:
if a lane produced nothing worth reading, say so and propose dropping it. A stated target gets
no such treatment — that one is theirs.

If a lane turns out to have no reachable employers rather than no suitable roles, say which it
is. Those are different problems and only one of them is about the user.

## Stage 2: Discover

Build the company list. This is the durable asset — job listings decay within days, but
company-to-ATS mappings hold for months.

1. Pull a job aggregator once to find companies hiring for the target titles. `references/ats-endpoints.md`
   lists which aggregators actually work and which advertise capability they do not deliver.
2. For each company, resolve which ATS it uses by fetching its careers page and pattern-matching.
   `scripts/resolve_ats.py` does this.
3. Keep the reachable ones in `companies.json`.

Expect roughly a third to be unreachable — companies on ATS platforms without public APIs, or on
none at all. That is the real ceiling on any automated search, and it is worth telling the user
the number so they understand what the tool can and cannot see.

## Stage 3: Sweep

Enumerate current openings from the boards in `companies.json` using `scripts/sweep_ats.py`.

This is the step to re-run. Everything upstream is stable; this is the part that goes stale.

**Tell the user the cost before starting.** Timings are in the README. A tool that looks instant
and then runs for twenty minutes has broken a promise.

## Stage 4: Score

`scripts/score.py` reads `profile.json` and `postings.json` and ranks. Scoring is cheap triage,
not judgment — its only job is to get a few thousand postings down to a shortlist a human-quality
read can handle.

Two things matter more than the weights:

**Gates come from the gap inventory.** If the profile says no SQL, roles requiring SQL get
penalized. This is the mechanism by which an uncomfortable interview question protects the user
for months.

**Print what each gate removed.** `scripts/checks.py` provides `GateLog` for this. A gate that
fires on almost nothing is broken, and a filter change that silently removes a large chunk of the
pool is worse than no filter. The accounting is what makes the scoring auditable.

**Report coverage before results.** Run `scripts/coverage.py` and tell the user what was
actually searched before you show them a ranking. A short list looks like a verdict on them
when it is often a statement about which employers this skill can reach -- and for anyone
outside software that is usually the dominant fact about their search. An empty result with no
coverage report is the single most misleading thing this skill can produce.

Show the user the top twenty and ask them to flag anything that looks wrong. Domain keyword
patterns produce false positives that are obvious to a human and invisible to a regex — the word
"property" matches real estate and cloud infrastructure equally well. Tighten from their
corrections.

### When to call it a no

Scores rank; they do not decide. The decision rule, once the requirements have been read:

- **One hard minimum missed, stated as required** — a licence, a clearance, a named years-of-
  experience floor they are well under. That is a no. Say so plainly and do not soften it into a
  stretch. Profile gaps marked `hard` drop the role automatically for this reason.
- **Two or more soft gaps in the same area** — say, no SQL and no experimentation experience on a
  data-heavy role. Treat as a no. Individually survivable, together they are the job.
- **Soft gaps scattered across areas** — apply, and name each one in the fit summary with the
  sentence to say about it.

**Stretch and overqualified can both be true, and usually mean different things.** Above their
level on scope but below on years is a stretch worth taking. Below their level on scope with a
title that caps their next move is not, however well it scores on keywords — and the pay band is
the tell. When both apply, say both, and say which one the user should weight. Do not average
them into a single number: the average hides the thing they need to decide about.

## Stage 5: Verify — blocking

Nothing gets packaged without a current verification record. `scripts/verify_one.py` writes them;
`scripts/gate.py` enforces.

```
python3 scripts/verify_one.py --platform greenhouse --board acme --req 4056789
```

It prints the requirements and records the role as **unread**. Read them, then re-run with
`--requirements-reviewed`. The two-step is the point: a script cannot judge whether someone meets
a requirement, so it refuses to claim it did.

| Check | Why |
|---|---|
| Identity is the **requisition id**, never the title | Boards carry duplicate titles. One board returned three postings called "Account Executive, Enterprise" under different ids; matching on text certifies whichever is first. Fuzzy matching is worse still -- a 0.72 similarity once accepted "Principal PM, Medicare Advantage" as "Principal PM, Core AI". |
| Full pagination before concluding absence | Checking the first 100 of 705 postings reported live roles as gone. |
| **Location, from the posting body** | Platform metadata lies. One ATS reports `isRemote: true` on roles requiring three days a week in a specific office. The check compares onsite language against the profile's acceptable metros. |
| Requirements actually read by a human or model, bound to the text | Nothing else can tell whether the user clears the bar. The attestation is tied to a fingerprint of the posting body, so if the text changes between the read and the confirmation, the earlier read no longer counts. |
| **The apply link resolves** | A live API record is not proof the user can apply. One employer's published link contained an unfilled template placeholder and every variant 404'd while the posting looked healthy. |

**Unknown is not a pass, in either direction.** Silence about location is not permission: a
posting that never says where the work happens has not said it is remote. Affirmative evidence
is required — matching metro, or explicit remote language the profile accepts. Everything else
is unresolved, and the gate stays shut.

**A failed recheck invalidates the previous success.** An unreachable board does not mean nothing
changed -- it means nobody knows, and packaging stops until someone does.

Records expire in three days. That is not arbitrary: a four-day-old snapshot has been observed
with three dead roles in its top ten.

## Stage 6: Package

For a verified role, generate three documents with `scripts/docgen/`:

**Resume** — tailored summary, headline and skills; employment history unchanged. Facts stay
fixed; emphasis moves.

**Cover letter** — only if the application accepts one. Check first. Greenhouse exposes this at
`?questions=true`, which also reveals whether it is a file upload or a text box, and whether a
portfolio URL field exists. Writing a letter no form will accept wastes the user's time.

**Fit summary, not for submission** — the requirements table, gaps with the plain sentence to say
about each, stories to lead with, questions to ask, and a pre-submit checklist. This is the
document the user actually reads before an interview, and it is where honesty lives. If a gap is
disqualifying, say so and say do not apply.

```
node scripts/docgen/package.js <package-config.json> <output-dir>
```

One entry point, and it takes a requisition key. The gate runs before anything is written, and
the generators refuse individually too — a gate that is available but optional is not a gate.

Documents are built in a temporary directory and moved into place only once every assertion has
passed. A failed assertion used to leave its output behind, which is the one case where a bad
document is most likely to get sent anyway.

The resume config carries only the three things that move per role. Employment history comes
from `profile.resume.experience` and cannot be edited through the config, because a generator
that can rewrite history is a generator that can invent it.

Identity, contact details and the sections that must never be dropped all come from
`profile.json`. The generators refuse to run without it rather than falling back to a default,
because the default would put somebody else's name on the user's letter.

The config shape is documented in `references/schemas.md`. Write documents somewhere the user
chose, or `./applications/<company>-<role>/` if they have no preference — never into the state
directory, which is bookkeeping, and never into the skill.

**Keep em dashes out of generated documents.** `assertResume` rejects them and the package is
abandoned rather than written, so a letter full of natural prose dashes fails late and with
little explanation. Use commas, colons or a full stop. This applies to the .docx, not only to
ATS text boxes.

`scripts/docgen/check.js` asserts the output contains what it should, and `requireVerified()`
shells to the same gate the Python side uses. Generators fail silently — a stale one has dropped
an entire employment block without raising anything.

For manual entry into ATS text boxes, emit plain text: semicolons converted to sentence breaks,
straight apostrophes, no doubled spaces. Some forms reject punctuation outright.

## Stage 7: Track

Record every application in `applications.json`: company, role, ATS and requisition id, date,
status, follow-up due, outcome and reason.

This is not bookkeeping. It answers the question a job seeker usually cannot answer about
themselves: **where does my funnel actually break?** Someone convinced they "cannot get
interviews" may in fact be clearing screens and failing assessments — a completely different
problem with a completely different fix. Only the record shows it.

## How to talk to the user about fit

Be the person who tells them not to apply. That is the value.

- Lead with a verdict: strong match, partial, stretch, or overqualified. Do not bury it.
- Separate required qualifications from preferred. A gap in a required one is disqualifying; a gap
  in a preferred one usually is not.
- **Flag overqualification as seriously as underqualification.** Being too senior is a real
  rejection reason, not a compliment.
- Name where they would lose. Assume a strong competitor exists and say what that person has.
  Advancing several rounds and then losing is the most expensive outcome available.
- Quote the posting's exact language when it matters. Paraphrase hides gates.

## Reference files

- `references/onboarding-interview.md` — the interview, and why each question earns its place
- `references/ats-endpoints.md` — every platform, its endpoints, and the trap in each
- `references/gotchas.md` — good and bad patterns for pacing, honesty and tone
- `references/failure-modes.md` — mistakes this method has already made, and the fix for each

Read `failure-modes.md` before changing any script. Most of it was learned expensively.
