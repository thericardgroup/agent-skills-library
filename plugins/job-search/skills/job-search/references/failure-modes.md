# Failure modes

Every one of these cost real time in the Sept 2026 search. They are the reason this folder exists.

## Scoring failures

**Surface-keyword matching produces confident garbage.**
Ranked Truv #4 because "mortgage and income verification" read as real estate domain. The actual
job is document parsing, OCR, fraud signal layers, and SLA ownership, with a required qualification
of "owning a data-intensive product at meaningful scale." Wrong on the core.
Same error flagged "real estate domain" on vCluster Labs, Guidewire, and S&P Global because the
regex matched the word *property* in infrastructure contexts.
**Fix: score against the requirements block, not the whole posting, and read the top N by hand.**

**One matching sentence is not a match.**
Called Vanta "best fit on the board" on the strength of a single unusual line about building with
AI tools, plus the pay. Of nine stated criteria it met seven — and the two misses, developer-facing
products and developer-community relationships, were the spine of the job.
**Fix: count met vs unmet against every stated criterion before ranking.**

**Penalty detectors must run or they are decoration.**
Adding dev-platform, SQL, and ML-depth gates changed the top 5 completely and disqualified Smarsh,
which had been ranked #1. Across 451 roles: 35 required SQL, 12 were developer-platform roles, 26
had specialist domain gates. None were being detected.
**Fix: after adding any gate, print the distribution. If almost nothing fires, it is broken.**

**Silent filter changes.**
An edit intended to add the location gate also dropped `Director` from the title pattern, removing
91 roles without any log line. The count fell 451 to 347 and the location gate accounted for 5 of
those.
**Fix: log every filter's removal count separately and diff against the prior run.**

## Location failures

**`isRemote` lies.** Ashby returns `isRemote: true` on NYC-hybrid roles. Aggregators report
"United States" for roles requiring three days in a Manhattan office.
**Fix: grep the JD body for "N days per week in office", "hybrid schedule", "must be located/reside
in", "commuting distance", "relocation required". Then check the surrounding text for which city.**

**"Live" and "still qualifies" are different checks.** PermitFlow was re-verified as live two days
before being caught as NYC hybrid. The verification confirmed the role existed and nothing else.
**Fix: re-verification must re-check location and requirements, not just existence.**

**Titles duplicate across locations.** ServiceNow posts the same title as both REMOTE and New York.
Zscaler has three identical "Principal Product Manager" postings, one remote and two in San Jose.
**Fix: match on id, never on title. Confirm the specific id before applying.**

## Verification failures

**Fuzzy title matching passes wrong roles.** A 0.72 similarity threshold accepted "Principal PM,
Medicare Advantage" as a match for "Principal PM, Core AI" and reported a dead role as live.
**Fix: require exact normalized title match. Fall back to fuzzy only above ~0.80 and print what
matched so it can be eyeballed.**

**Partial pagination produces false negatives.** Checking only ServiceNow's first 100 of 705
postings reported both target roles as gone.
**Fix: paginate to `totalFound` before concluding anything is missing.**

**Cached listings decay in days, not weeks.** A Sept 25 snapshot had three dead roles in its top
ten by Sept 29. A six-role live check on Sept 29 returned zero usable: one failed requirements,
two were gone, three had unreachable boards.
**Fix: never recommend from cache. The cache generates candidates; the live board confirms them.**

## Document failures

**Regenerating from a stale generator silently drops content.** The scratchpad copy of the resume
generator reverted to a pre-patch version with no `cfg.earlier` support. Regenerating would have
dropped the Earlier Experience block — the Redfin, Coldwell Banker, and Target history — with no
error. This happened once before with a Zillow PDF.
**Fix: after generating, assert that known-required strings are present in the output.**

**Copying from PDF corrupts text.** Doubled spaces at line-wrap points, dropped semicolons, and
bullet markers merged into the preceding sentence — which silently swallowed an entire bullet.
**Fix: copy from .docx or emit plain text. Verify bullet count after pasting.**

**ATS form fields reject punctuation.** One rejected semicolons outright: "This field cannot
contain following characters: ;". Smart quotes are the next most common rejection.
**Fix: for manual entry, emit text with semicolons converted to sentence breaks with the next word
capitalized, straight apostrophes, and collapsed whitespace.**

**Word AppleScript export needs POSIX paths.** HFS-style paths return "missing value doesn't
understand the save as message" with zero documents open.
**Fix: `POSIX file` for source, POSIX string for destination, and reference `document 1` rather
than `active document`.**

## Shell

**zsh does not word-split unquoted variables.** A `for` loop with `set -- $x` silently passed the
whole string as `$1`, producing three identical failed API calls.
**Fix: use explicit arrays or a function with positional args.**

## Process

**The single highest-value discipline: pull the live JD and read the stated requirements before
recommending anything.** Every bad recommendation this month — Smarsh, Vanta's ranking, Truv,
Toast Data Governance, PermitFlow, Entrata — would have been caught by it. Nothing else came close
in value, including any amount of scoring sophistication.
