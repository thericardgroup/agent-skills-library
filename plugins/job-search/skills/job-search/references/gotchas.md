# Gotchas

## Gotcha: Interviewing before proving anything

**Why it matters:** A stranger will not answer twenty minutes of questions for a tool that has
not yet done anything for them. The fit analysis on a posting they already care about is what
earns the interview. Skip it and completion collapses.

### ✗ Bad

> "Great, let's get you set up. First I need to build your profile — what kind of role are you
> looking for?"

Twenty minutes of questions before any value. Most people leave here.

### ✓ Good

> "Before we do anything else — is there a job you're already looking at? Paste it in and I'll
> tell you straight whether it's worth your time."
>
> *[reads the posting, gives an honest verdict including the parts that do not fit]*
>
> "That's the kind of read you'd get on every role. To do it properly I need about fifteen
> minutes of questions. Want to keep going?"

---

## Gotcha: Asking all five questions at once

**Why it matters:** Five questions in one message is a form, not a conversation. People
skim-answer or drop off, and skim answers produce a profile that recommends the wrong jobs for
months.

### ✗ Bad

> "To build your profile: (1) target role? (2) location? (3) gaps? (4) compensation? (5) a
> quantified win?"

### ✓ Good

Ask one. Wait for the whole answer. Ask the next. Under time pressure, compress to role,
location and gaps — never fewer than those three.

---

## Gotcha: Letting a soft number into the profile

**Why it matters:** An unverifiable achievement is worse than none, because it survives the
resume and then collapses in the interview, in front of the person deciding.

### ✗ Bad

> **User:** "I improved our support response times a lot."
> **Claude:** "Great — I'll note significant improvement to support response times."

### ✓ Good

> **User:** "I improved our support response times a lot."
> **Claude:** "How do you know? Was there a number you were watching, or a before and after you
> could point to?"
> **User:** "Honestly I just know it got better, people stopped complaining."
> **Claude:** "That's worth saying, just not as a headline. I'll record it as directional and we
> won't lead with it. If you can still get into the old dashboard, a real number would make it
> one of your strongest lines."

---

## Gotcha: Treating the gap question as optional

**Why it matters:** The gap inventory is what generates the disqualifying filters. Without it the
skill recommends roles the person cannot get and tells them they are a great fit. That is the
single worst failure mode available here, because it costs months rather than minutes.

### ✗ Bad

Skipping it because it feels awkward, or accepting "I think I'm pretty well rounded" and moving
on.

### ✓ Good

> "This one's uncomfortable but it's the most useful question I'll ask. What do these postings
> keep wanting that you don't actually have? Not what you're weak at — what you've genuinely
> never done."
>
> *(If they deflect)* "The reason I push on this: if you tell me you've never written SQL, I can
> keep thirty roles off your list that would have wasted a month each. If you don't, I'll
> recommend them and they'll all end the same way."

---

## Gotcha: Saving the profile without showing it

**Why it matters:** Silent writes remove the chance to correct something misheard, and reading
the profile back routinely surfaces a correction the person would never have volunteered.

### ✗ Bad

> "Got it — profile saved!"

### ✓ Good

> "Here's what I've got. Tell me what's wrong with it:
>
> **Going after:** Senior Product Manager, ideally AI or platform
> **Location:** Remote US only — cannot relocate
> **Gaps:** Never written SQL · no experience with developer-facing products
> **Target:** $170K, would consider lower for the right team
> **Proof point:** Cut voicemail rate 45% to 4%, verified against carrier records
>
> Look right? I'll save it once you confirm, and you can change it any time."

---

## Gotcha: Showing the machinery

**Why it matters:** Someone new to Claude Code does not know what a skill is, what a JSON file
is, or that anything is being written on their behalf. Every mention of the plumbing is a moment
they feel out of their depth, and people who feel out of their depth stop.

### ✗ Bad

> "I've written your profile to `.claude/job-search/profile.json` and initialized the state
> directory. Next I'll run the discovery stage to populate `companies.json`."

### ✓ Good

> "Saved. Next I'll work out which companies actually hire for this, which takes twenty minutes
> or so — want me to start now or come back to it?"

---

## Gotcha: Recommending a role without reading it

**Why it matters:** Scoring matches keywords. Requirements are sentences. Every bad
recommendation this method has produced came from trusting a score instead of reading the
posting — including roles that were already filled, roles requiring credentials the person did
not have, and roles that were quietly on-site in another city.

### ✗ Bad

> "Here are your top ten matches this week."

Where the ranking came from a cached sweep and nobody opened a single posting.

### ✓ Good

Score to get a shortlist, then open each one, read the stated requirements, check the location
language in the body text, and confirm the posting is still live. Recommend only what survives.
Five verified beats twenty scored, every time.
