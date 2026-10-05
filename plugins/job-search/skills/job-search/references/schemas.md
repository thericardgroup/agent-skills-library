# State file schemas

Five files, one directory, resolved only by `scripts/statepath.py`. Default root is
`.claude/job-search/` under the working directory; `$JOB_SEARCH_STATE` overrides it.

Nothing here is written into the skill's own folder. Updating the skill must never touch a
user's data.

| File | Written by | Read by |
|---|---|---|
| `profile.json` | onboarding interview | everything |
| `companies.json` | `resolve_ats.py` | `sweep_ats.py` |
| `postings.json` | `sweep_ats.py`, `sweep_aggregator.py` | `score.py` |
| `verified.json` | `verify_one.py` | `gate.py`, `docgen/check.js` |
| `applications.json` | tracking stage | `score.py` (already-applied filter) |

---

## profile.json

The only source of what this user wants. Every filter, weight and threshold in the pipeline
reads from here, which is what keeps the skill from ranking for whoever wrote it.

```jsonc
{
  "identity": {
    "name": "Dana Okonkwo",              // required for document generation
    "email": "dana@example.com",         // required
    "phone": "(312) 555-0147",
    "location": "Chicago, IL",
    "signature": "Dana Okonkwo",         // defaults to name
    "links": [{ "text": "linkedin.com/in/example", "url": "https://..." }]
  },

  "titles": {
    "target":  ["ux research", "user research", "design research"],  // regex, required
    "exclude": ["intern", "engineer", "recruiter"],

    "source": "derived",               // "stated" | "derived" -- how these got here
    "derived_from": [                  // required when source is "derived"
      { "family": "UX research",
        "evidence": "Seven years running usability sessions in clinical settings" }
    ]
  },

  "location": {
    "remote_ok": false,
    "country": "united states",
    "acceptable_metros": ["chicago", "evanston"],   // substring match, lowercase
    "metro_aliases": ["chicagoland"],
    "reject_metros": ["new york", "san francisco"]  // explicit no, drops the posting
  },

  "pay": { "floor": 95000, "target": 130000 },      // floor never leaves this file

  "constraints": {                     // asked in the interview, used by scoring
    "travel_ceiling_pct": 20,          // null if they did not say
    "will_relocate": false,
    "onsite_days_max": 2,              // per week; 0 means remote only
    "visa_sponsorship_needed": false,
    "notes": "cannot travel during school terms"   // free text, never filtered on
  },

  "seniority": {
    "at_level":    ["\\bsenior\\b", "\\bsr\\.?\\b"],
    "above_level": ["director", "head of", "\\bvp\\b"],
    "below_level": ["associate", "junior"],
    "at_level_bonus": 12, "above_level_penalty": -8, "below_level_penalty": -6
  },

  "interests": [                                     // what pulls a role up
    { "name": "healthcare", "patterns": ["patient", "clinical"],
      "title_weight": 30, "body_weight": 12 }
  ],

  "gaps": [                                          // what pushes it down, or kills it
    { "name": "quant depth", "patterns": ["regression analysis"], "penalty": 12 },
    { "name": "security clearance", "patterns": ["TS/SCI"], "hard": true }
  ],

  "resume": {
    "required_sections": ["EDUCATION", "EXPERIENCE"],  // must survive generation
    "never_drop_employers": [],
    "min_chars": 3000,            // guard against silent truncation: set it just
                                  // under the real resume's length, not above it
    "experience": [                                    // fixed history, never tailored
      { "title": "Senior UX Researcher", "employer": "Lakeshore Health",
        "dates": "2021 - present", "scope": "optional one-line scope",
        "bullets": ["Measured outcome, and how it was measured."] }
    ],
    "earlier_experience": ["Research Coordinator, Midwest Health (2014 - 2016)"],
    "education": ["MS Human-Computer Interaction, example university"]
  },

  "max_posting_age_days": 60
}
```

**`source` records who decided.** `stated` means the user named these targets; `derived` means
they were worked out from their history because they could not. A derived target is a
hypothesis the first ranking is allowed to revise, and `derived_from` carries the evidence
behind each family so the user can argue with it. A profile with neither is accepted and warned
about -- the provenance is simply unknown.

**`hard: true` disqualifies rather than penalizes.** Reserve it for stated minimums a user
genuinely cannot clear today — a licence, a clearance, a credential. Everything else is a
penalty, because a pipeline that disqualifies on soft gaps returns an empty list and teaches the
user nothing.

**Patterns are regular expressions, matched case-insensitively.** `score.py` applies interest
patterns to the title and the body separately, and gap patterns only to the requirements block —
a technology mentioned in a company blurb is not a requirement.

---

## package-config.json

Not state — the input to `scripts/docgen/package.js`. Any of `resume`, `letter` and `fit` may
be omitted; `key` never can.

```jsonc
{
  "key": "greenhouse::acme::4056789",   // must currently clear the gate

  "resume": {                            // per-role tailoring ONLY; employment
    "headline": "Senior UX Researcher",  // history comes from profile.resume
    "summary": "One or two sentences.",
    "skills": ["Usability testing", "Diary studies"]
  },

  "letter": {
    "date": "October 1, 2026", "title": "Senior UX Researcher",
    "company": "Northstar Health",
    "letter": ["First paragraph.", "Second paragraph."]   // no em dashes
  },

  "fit": {
    "title": "Senior UX Researcher", "company": "Northstar Health",
    "verdict": "apply",                  // apply | stretch | no
    "verdict_because": "One or two sentences on why.",
    "apply_url": "https://...",          // defaults to the verified record's
    "requirements": [
      { "text": "5+ years research", "status": "yes",     // yes | partial | no
        "required": true, "note": "7 years" }
    ],
    "gaps":      [{ "name": "Quant depth", "say": "What to say in the room." }],
    "stories":   ["Task failure 31% to 9%"],
    "questions": ["Who owns quant research today?"],
    "checklist": ["..."]                 // optional; a sensible default is used
  }
}
```

**Em dashes fail the resume assertion** and the whole package is abandoned rather than
half-written. Use commas or full stops.

---

## package-manifest.json

Written beside the documents, never into the state directory. It is what makes a delivered
package auditable after the fact.

```jsonc
{
  "schema": "job-search/package-manifest@1",
  "key": "greenhouse::acme::4056789",
  "generated_at": 1759536000.0,
  "files": [
    { "name": "resume.docx", "bytes": 9888, "sha256": "sha256:cf83ad74..." }
  ],
  "approval": {                       // a snapshot, not a pointer
    "status": "verified", "verified_at": 1759535900.0,
    "title_matched": "Product Manager", "company": "Acme",
    "apply_url": "https://...", "apply_url_ok": true,
    "location_ok": true, "requirements_read": true,
    "body_fingerprint": "a1b2c3d4e5f60718", "profile_rev": "9f8e7d6c5b4a3210"
  },
  "profile_rev": "9f8e7d6c5b4a3210",
  "preexisting_files": ["old-letter.docx"]   // already there; not part of this package
}
```

**The approval is copied, not referenced.** `verified.json` is overwritten on every recheck, so
a package pointing at it cannot be audited once the role is re-verified or expires. Whether
that approval is *still* current is a separate question from whether it was valid when the
documents were made, and the two are answered separately.

---

## companies.json

```jsonc
{
  "Northstar Health": { "platform": "greenhouse", "board": "northstar",
                        "postings_seen": 42, "confirmed": true,
                        "board_owner": "Northstar Health",
                        "evidence": "board identifies itself as 'Northstar Health'" },
  "Beacon Labs":      { "platform": "lever", "board": "beacon", "confirmed": false,
                        "board_owner": "Beacon Analytics",
                        "note": "board exists but identifies itself as 'Beacon Analytics'" },
  "Private Co":       { "confirmed": false, "note": "no board found by name guessing" }
}
```

Only `confirmed: true` entries are swept. A board found by guessing but not corroborated is a
candidate, because a slug trimmed from a longer name lands on other companies' boards and every
posting then carries the wrong employer.

Unconfirmed entries are kept deliberately. They are the honest record of what the tool cannot
see, and roughly a third of employers land here.

---

## postings.json

An array. The first three fields are the posting's identity and must survive every later stage.

```jsonc
[{
  "platform": "greenhouse", "board": "figma", "requisition_id": "5426468004",
  "companyName": "Figma", "title": "Product Manager", "description": "plain text",
  "locationRestrictions": ["United States"], "applicationLink": "https://...",
  "pubDate": 1727654400, "minSalary": 150000, "maxSalary": 190000,
  "salaryPeriod": "yearly"
}]
```

`pubDate` is epoch seconds, and an unparseable date becomes `0`, never "now" — dating a stale
posting to today is how a dead role reaches the top of a ranking.

---

## verified.json

Keyed `platform::board::requisition_id`. Never by title: boards carry duplicate titles, and
certifying one under the other's name is how the wrong role gets packaged.

```jsonc
{
  "greenhouse::figma::5426468004": {
    "status": "verified",            // verified | failed
    "checked_at": 1727654400.0,      // expires after 3 days
    "live": true,
    "location_ok": true,             // false if it fails OR is unresolved
    "apply_url_ok": true,            // the link was fetched and resolved
    "requirements_read": true,       // only true when set explicitly
    "body_fingerprint": "a1b2c3d4e5f60718",  // binds the attestation to the text read
    "apply_url": "https://...",
    "title_matched": "Product Manager",
    "notes": "location: no onsite language in the posting body"
  },
  "greenhouse::acme::999": {
    "status": "failed", "reason": "HTTP 404", "checked_at": 1727654400.0,
    "live": false, "location_ok": false, "requirements_read": false,
    "superseded_verified_at": 1727568000.0   // what this failure invalidated
  }
}
```

A `failed` record overwrites an earlier success on purpose. Not knowing is not the same as
nothing having changed.

---

## applications.json

Keyed `Company::Role`. `score.py` reads the company half to stop re-surfacing roles already
applied to — which is why that filter is state rather than a list in the code.

```jsonc
{
  "Northstar Health::Senior UX Researcher": {
    "platform": "greenhouse", "board": "northstar", "requisition_id": "1001",
    "applied_at": 1727654400.0, "status": "submitted",
    "follow_up_due": 1728864000.0, "outcome": null, "notes": ""
  }
}
```
