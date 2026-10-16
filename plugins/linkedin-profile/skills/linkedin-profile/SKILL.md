---
name: linkedin-profile
description: Audit and rebuild a personal LinkedIn profile against the person's own resume and the roles they are actually targeting, then apply the approved changes and verify each one stuck. Checks the recruiter-facing settings that silently hide a profile from search before touching any wording, compares profile and resume line by line for the contradictions recruiters notice, rewrites the headline, About and experience sections, fixes role grouping and company naming, and repairs link previews including the Open Graph tags on the person's own site. Use whenever someone mentions their LinkedIn profile, asks why recruiters are not finding or contacting them, wants their headline or About section rewritten, is job hunting and wondering whether their profile is holding them back, has just been laid off and is updating their profile, says their profile feels out of date or does not reflect what they do now, or asks whether their profile matches their resume. Also when someone shares a profile link and asks what you think. Personal profiles only; this skill does not work on LinkedIn Company Pages.
---

# LinkedIn Profile

A profile fails in two ways that matter and one that mostly does not.

**It is invisible.** A single recruiter-facing preference, set wrong or never set, can exclude an
otherwise excellent profile from every search a recruiter runs. Nothing looks broken. There is no
warning and no notification. The person concludes their experience is the problem.

**It contradicts the resume.** A recruiter reading a profile usually has the resume open in
another tab. Comparing them is the job. Mismatched dates, titles that do not line up, an employer
on one document and not the other — each one is a small withdrawal from the same account.

**The writing is weak.** This is the one everybody fixes first. It matters least. Beautiful copy
on a profile nobody sees changes nothing, and beautiful copy that disagrees with the resume is
worse than what it replaced.

So: **settings before substance, substance before style.** Audit what is hiding them, then what
contradicts them, and only then write anything.

Read `reference/failure-modes.md` before touching a live profile. Everything in it is something
that already broke once and reported success while doing it.

`reference/platform-details.md` holds the settings locations and link-preview thresholds. Every
value in it decays; confirm against what is actually on screen.

## Before anything else

Work out which mode you are in, and say so plainly once.

**Full mode** needs a browser tool that can reach the person's signed-in LinkedIn. Check whether
browser tools are available in this session. If they are, you can read the live profile, apply
approved changes, and verify them.

**Review mode** is everything else — claude.ai, Cowork, any session without browser access. You
can still do the audit, the comparison, and the rewriting. The person supplies their profile by
pasting it or uploading the data export LinkedIn provides under Settings and Privacy, and applies
the changes themselves from copy you give them.

Review mode produces the same findings and the same words. What differs is who types, and what
can be verified at the end — see Stage 9, which has a separate branch for it. Do not apologise
for review mode or push the person toward installing anything.

Assume the person has never used a skill before. They should never see a file path, a tool name,
or anything about how this works internally. Talk about their profile, not the machinery.

## Where your work is kept

Before any change, this skill preserves the current state of whatever it is about to modify. Where
the session can write files, that is a snapshot in `.linkedin-profile/` in the directory it is run
from. Where it cannot, the person is given their original text and asked to save it themselves.
Either way, something recoverable exists before anything is overwritten — see Stage 7b.

Tell the person where it is, in plain words, the first time you write one. Never write inside the
skill's own folder — updating the skill must not touch their data.

## The shape of it

```
onboard ──→ read ──→ SUPPRESSION ──→ CONTRADICTION ──→ align ──→ rewrite ──→ structure
                     (settings)         ⛔ GATE                                   │
                                                                                  ▼
                                          verify ←── APPLY ←── SNAPSHOT ←── site links
                                        (mode-aware)  (full mode)  ⛔ before any write
```

Nothing after the gate runs until the contradiction audit is done and every conflict is either
resolved or deliberately accepted by the person.

## Stage 0: Onboard

Open warmly and briefly. Do not open with a disclaimer; open with what they get.

Something close to:

> I can go through your LinkedIn profile properly — not just the wording, but the settings that
> decide whether recruiters see you at all, and whether your profile and your resume tell the same
> story. Most people have never checked the second one, and recruiters check it every time.

Then, before any work starts, say these four things plainly and in your own words. They are not
boilerplate to be skipped.

1. **What this covers.** Their personal profile. Not a Company Page.
2. **It operates on their own account only.** You will work on the profile of the person running
   this, you will confirm which account that is before doing anything, and you will stop if it
   changes. You will not operate on someone else's profile and will not ask for anyone's password.
3. **AI gets things wrong.** Every suggested change is theirs to review, and nothing reaches their
   profile without them approving that specific change. They should read each one before saying
   yes. Their account, their words, their call.
4. **Automated interaction with LinkedIn sits under LinkedIn's terms of service.** They are
   choosing to use a tool that interacts with their account. Worth knowing before starting.

Get an explicit yes before continuing. If they hesitate, offer review mode: you audit and write,
they apply by hand. That removes the automation question entirely and loses nothing but typing.

### Three questions, one at a time

Ask them separately, not as a list.

- **Do you have a resume you want this to match?** Without it, the contradiction audit — the most
  valuable stage here — cannot run. Say so. Offer to continue without it and come back.
- **Are you targeting particular roles?** If they can share two or three real job postings they
  are pursuing, the rewrite aligns to language those employers actually use. Without targets, say
  the alignment stage is unavailable rather than substituting generic keywords.
- **Do you link to a portfolio or your own website from your profile?** Only if yes does the site
  layer run. Most people say no, and that is fine.

## Stage 1: Read

### Confirm whose account this is — before reading anything

Being signed in proves authentication, not ownership. A shared computer, a second profile, or a
session switched between browser tabs will all present as authenticated.

In full mode, read the signed-in account's name and profile URL and **show both to the person**:

> I can see an account signed in as [name], at [profile URL]. Is that you, and is that the profile
> you want me to work on?

Get a yes. **Record that name and URL.** They are the account binding, and every later write
checks against them.

If the person says no, stop. Do not offer to sign in as someone else, and do not continue on an
account they did not claim.

### Then read the profile

Headline, About, every experience entry with dates and employer names, education, skills,
Featured, and the custom URL.

**The activity feed will try to swallow the profile.** Posts and comments can dominate an
extraction so completely that whole sections never appear. If a section seems missing, say you
could not read it. Never tell someone something is absent from their profile on the strength of
one extraction.

In review mode, ask for the profile. Pasting it works. The data export LinkedIn provides is
better, because it is structured and complete — tell them where to request it and that it takes
about ten minutes to arrive, then offer to carry on with a paste in the meantime.

## Stage 2: Suppression audit

**Run this before anything cosmetic.** The settings layer determines whether the content layer is
ever seen.

Walk them through the recruiter-facing preferences one at a time. In full mode you can read these
directly. In review mode, describe where to look and ask what they see.

`reference/platform-details.md` lists what to check, where it lived, and why each one matters.
Those locations move; if something is not where the reference says, use what is on screen and say
the reference is stale.

**A setting you could not check is not a setting that passed.** Record it as unchecked and say so
in the summary.

Report what is suppressing them before you report anything about their writing. If something here
is wrong, it outranks every wording change in the rest of this skill.

## Stage 3: Contradiction audit ⛔ GATE

Compare the profile against the resume line by line. This is the stage nobody does for themselves
and every recruiter does automatically.

Look for:

- **Date conflicts.** Different start or end months, gaps on one document that the other fills,
  overlapping roles presented differently.
- **Title conflicts.** The same role under two names. This is often deliberate and reasonable —
  an internal title nobody outside the company would understand, rewritten for clarity. Say which
  you think it is rather than flagging it as a lie.
- **Employer name conflicts.** Legal entity on one, trading name on the other. Acquisitions
  described differently.
- **Claims on one and not the other.** A metric, a scope, a team size.
- **Seniority drift.** A profile that quietly promotes someone relative to their resume.

Separate real problems from normal curation. A resume tailored for one role will legitimately
emphasise different things than a profile written for everyone. That is not a contradiction. A
different end date is.

Present the conflicts and let the person resolve each one. **Do not write new copy until they
have.** A rewrite built on an unresolved contradiction propagates it into better prose.

### If there is no resume

The gate cannot run. Say that plainly, name what they are giving up, and get an explicit decision
to continue.

If they continue, **the evidence standard changes rather than disappearing.** Every factual claim
in the rewrite must then come from the existing profile, or from something the person states in
this session and confirms when you read it back to them. Nothing else. Record which facts came
from where, because you will need it in Stage 5.

## Stage 4: Align

Only runs if they gave you real target postings.

Read the stated requirements in each. Pull the language those employers actually use — the terms
that appear in requirements, not the terms a title suggests. Compare against what the profile
currently says.

The output is a short list: terms their targets ask for that their profile does not contain, and
terms their profile leads with that no target asks for. Both directions matter. A profile
optimised for roles the person is no longer pursuing is a common and invisible problem.

**Never invent keywords.** If a term is not in a real posting they gave you, it does not go on the
list.

## Stage 5: Rewrite

Now, and not before, write.

- **Headline.** The most-read line on the profile and the one that appears in search results. Lead
  with what they do and the proof, not with aspiration.
- **About.** First two lines are what shows before the fold. Everything that matters goes there.
- **Experience.** Outcomes with numbers where numbers exist.

Rules that hold throughout:

- **Every factual claim must trace to a source.** With a resume, that is the resume. Without one,
  it is the existing profile or a fact the person stated and confirmed in this session, per Stage
  3. If a claim traces to nothing, it does not go in.
- **When a resume exists**, anything new the person wants to add goes on both documents or
  neither, so the two cannot drift apart again. When there is no resume, that rule has nothing to
  apply to: take the confirmed fact and move on.
- **Specific beats impressive.** A measured result beats a confident adjective.
- **Match how they talk.** Read their existing writing first. A profile that sounds like a
  different person is a worse profile, however polished.
- Produce the exact text, ready to use. Not advice about what to write.

## Stage 6: Structure

The layer nobody touches, invisible when correct and conspicuous when wrong.

- **Role grouping.** Several roles at one employer read better as one entry with sub-roles than as
  separate records.
- **Company name matching.** An employer name that does not match LinkedIn's record for that
  company breaks grouping and leaves the logo blank. Pick the name from LinkedIn's own suggestions
  rather than typing a variant.
- **Date continuity.** Gaps that the resume explains and the profile does not.
- **Featured section.** What is there, whether it renders, whether it is current.

### Never delete an experience record ⛔

Role grouping on LinkedIn is driven by the company association on each record. The correct fix is
to **edit the company field on each existing record** so they match, which groups them while
keeping every record intact.

**Deleting records and recreating them as one consolidated entry is prohibited.** It destroys
dates, descriptions, media, attachments and any recommendations attached to those positions, and
Stage 8's field-level approval and verification cannot detect what was lost.

If grouping genuinely cannot be achieved by editing company fields, **stop.** Describe to the
person what would have to be deleted and what they would lose, and let them decide and do it
themselves. Do not perform a destructive regrouping on their behalf, with or without approval.

## Stage 7: Site links

Only if they said yes at onboarding.

A link in the Featured section renders as a card using tags on the destination page. When those
tags are missing or wrong, the link shows as a bare URL, which looks broken next to everything
else on the profile.

Check, on their site, whether the page declares a title, description and preview image for
sharing, and whether that image actually exists, is large enough, and is reachable at the URL in
the tag.

`reference/platform-details.md` carries the current known image threshold, how to force a
re-scrape, why the cache is keyed to the image URL rather than the page, and why a missing image
can return a success status. Confirm those values against the platform's own current guidance
before declaring the repair complete, and verify the rendered preview visually rather than
trusting that an accepted upload will display.

If their site needs changes they cannot make themselves, say so plainly and stop. Describe what
needs to happen. Do not guess at someone else's site.

## Stage 7b: Snapshot ⛔ before any write

**Nothing that overwrites anything happens until this gate is satisfied.** In full mode that means
Stage 8 does not start. **In review mode it means you do not tell the person to apply anything**,
and you do not move to Stage 9, until they confirm their original is saved. Stage 5 already handed
them replacement text; without this gate they can paste it over an original nobody kept.

### If this session can write files

Write the complete current state of every section you are about to change: headline, About, and
each experience entry in full, including dates, company names and descriptions.

**Filename must be unique.** Use `.linkedin-profile/snapshot-<UTC timestamp to the second>.md` in
the working directory. Never a date alone — two runs on one day would overwrite the first recovery
copy, and a second account's profile could silently replace another's. **If that filename already
exists, do not overwrite it.** Add a counter and use the next free name.

**Record inside the file:** the confirmed account name and profile URL from Stage 1, and the
capture time. A snapshot you cannot attribute to an account is not a recovery copy.

**Then verify it.** Read the file back and confirm it exists, parses, and contains every field you
intend to change. If the write failed, was truncated, or a section could not be read from the
profile in Stage 1, **the gate does not open.** Say what is missing and stop. Instructing yourself
to write a complete file does not make one exist.

Tell the person the file is there and where. That file is why a failed write is survivable.

### If this session cannot write files

Some sessions have no filesystem. Do not pretend otherwise and do not skip the protection.

Give the person their current text for every section about to change, in one message, clearly
labelled as their original, and **ask them to save it somewhere outside this conversation** before
you proceed. Wait for them to confirm they have.

A conversation can end, scroll away, or be lost. Their saved copy is the recovery path in this
mode, and they need to hold it themselves.

**If they decline, or do not answer, do not proceed to telling them how to apply the changes.**
Say what the risk is in one sentence and offer to wait. If they want to go ahead anyway, that is
their call to make explicitly — record that they made it, and say plainly that nothing can be
restored if a paste goes wrong.

## Stage 8: Apply — full mode only

Everything before this produced words. This stage changes their profile.

**One field at a time. Always.** Batch application hides which change failed.

**Re-check the account binding from Stage 1 immediately before every save**, not only before the
first one and not only when something looks different. An account switched in another tab changes
nothing visible in the editor you are looking at, and matching field content does not establish
identity. If the signed-in account or profile URL is not the one the person confirmed, stop and
tell them. Do not write to an account they did not claim.

For each field:

1. **Show the before and after.** Both, in full.
2. **Get approval for that specific field.** Not a blanket yes collected earlier.
3. **Re-read the field's current value immediately before typing.** If it no longer matches the
   "before" they approved, the content changed underneath you — another tab, another device, or a
   reordered list. **Stop. Show the new comparison and ask again.** Never apply approved text to
   content the person has not seen.
4. **Confirm you are on the right record.** For experience entries, match on employer, title and
   dates together, not position in the list. Lists reorder.
5. **Preserve the exact value you are about to overwrite.** Capture what is in the field at this
   moment, after any re-approval in step 3. The Stage 7b file holds the state from before the
   session; if a field changed and was re-approved since, that file no longer holds the value you
   are replacing.
   **Persist it the same way Stage 7b does, before continuing.** Append it to the snapshot file,
   read the file back, and confirm the new value is in it. If this session cannot write files,
   send the person the new original, ask them to save it, and wait for confirmation. A value held
   only in this conversation is not preserved. **Do not proceed to step 6 until it is.**
6. **Select the existing contents and replace them, then save.** Type as real keyboard input;
   never write values straight into the page, because a field set that way can display correctly,
   appear saved, and silently revert. Activate the save control explicitly and wait for it to
   complete. Appending to a field instead of replacing it corrupts the value.
7. **Reload the profile fresh and read the field back.** A plain navigate-away-and-return can
   restore an unsaved editor or a cached view and hand you back the text you just typed while the
   server still holds the old value. Close the editor, force a full reload, and read the saved
   profile.
8. **Report what is actually true:** applied and verified, failed, or applied but could not be
   verified. Those are three different outcomes and the third is not a success.

### When a write fails or cannot be verified

Do not continue to the next field. For either outcome:

- Say which outcome it was and what the field contains right now.
- Offer three choices: restore the previous value, retry this field, or leave it and move on.
- **Restoring is a write like any other.** It uses the value captured in step 5, it is shown and
  approved on its own, it re-checks the account binding, and it is verified by reload afterwards.
  Never treat restoration as automatically safe or automatically successful.
- **Never blind-retry.** Re-read the live value first. Repeating a write after a timeout or an
  interrupted save can duplicate content or overwrite a change that actually succeeded.
- If you cannot determine the current value, say so and stop. An unknown state is not a state to
  act on.

**Print the text alongside every change**, whether or not the write succeeds, so the person can
finish by hand from the conversation as well as from the snapshot.

Stop and ask if anything unexpected appears: a verification prompt, a changed layout, a warning,
a login screen. Do not click through something you did not anticipate on someone's account.

## Stage 9: Verify

### Full mode

Force a fresh reload and read the whole profile again, with no editor open. Do not rely on
anything read earlier in the session.

Report three lists: applied and confirmed, did not hold, still outstanding. Then the settings from
Stage 2, re-checked.

### Review mode

You cannot verify anything yourself. Do not imply otherwise.

Ask the person to paste the updated sections back, or to send a screenshot. Compare what they
send against what was supposed to change, and report on that basis.

**Treating "I did it" as verification is not verification.** Anything you could not see with your
own eyes is reported as unverified, with a note that they can confirm it themselves by reloading
the profile. That is an honest outcome, not a failure.

**Never summarise drafted work as done.** Drafted, applied, and verified are three states. Only
the third one counts, and in review mode the third one requires evidence from them.

## How to talk to the person about their profile

They are often doing this because something is not working, and they may have concluded it is
because they are not good enough. Usually it is a settings checkbox and a headline written for a
job they left.

- Lead with what is working. There is always something.
- Name problems plainly, once, without softening them into vagueness.
- Distinguish "this is hurting you" from "this could be better." Most findings are the second.
- When the cause is mechanical, say so clearly. Learning that a preference was hiding you is a
  relief, not a criticism.
- Do not tell them their experience is the problem. That is almost never what this skill finds.

## Reference files

- `reference/failure-modes.md` — what has already broken, and the fix for each. Read before
  writing anything to a live profile.
- `reference/platform-details.md` — settings locations and link-preview thresholds. Everything in
  it decays; confirm against the live page.
