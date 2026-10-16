# linkedin-profile

A Claude Code skill that audits and rebuilds a personal LinkedIn profile -- settings first,
contradictions second, wording third.

Most advice about LinkedIn starts with your About section. That is the part that matters least.

**A profile fails two ways that count.** It is invisible, because a recruiter-facing preference
is set wrong and there is no warning that it is happening. Or it contradicts your resume, which
the recruiter has open in another tab, because comparing them is their job.

This skill checks both before it writes a single word.

## What it does

1. **Suppression audit.** Your open-to-work preferences, visibility, location, industry, custom
   URL. The settings that decide whether anyone sees the profile at all.
2. **Contradiction audit.** Your profile against your resume, line by line -- dates, titles,
   employers, claims. It separates real conflicts from normal curation. Runs without a resume if
   you do not have one, on a stricter evidence rule it will explain.
3. **Target alignment.** Against real postings you are pursuing, using the language those
   employers actually use. Not guessed keywords.
4. **Rewrite.** Headline, About, experience. Exact text, ready to use.
5. **Structure.** Role grouping, company-name matching so logos render and roles group properly.
6. **Link previews.** Including the tags on your own site, if you link to one.
7. **Apply and verify.** Each change approved individually, then read back to confirm it held.

## Install

New to Claude Code? Two lines. Open Claude Code and type:

```
/plugin marketplace add thericardgroup/agent-skills-library
```

```
/plugin install linkedin-profile@agent-skills-library
```

You only add the marketplace once.

### Or without a GitHub account

Download the repository as a zip, unpack it, and copy
`plugins/linkedin-profile/skills/linkedin-profile` to `~/.claude/skills/linkedin-profile`.
Claude Code picks it up next time it starts.

Then say what you need, in your own words:

- "audit my LinkedIn profile"
- "why aren't recruiters finding me?"
- "rewrite my headline and About section"
- "does my LinkedIn match my resume?"
- "I just got laid off and my profile is three years out of date"

## Two modes

**Full mode** needs a browser tool that can reach your signed-in LinkedIn. It reads your live
profile, applies approved changes, and verifies each one.

**Review mode** is everything else. It does the same audit and writes the same words; you paste
your profile in or upload the data export LinkedIn provides, and you apply the changes yourself.

The findings and the wording are identical. Two things differ: you do the typing, and at the end
the skill can only confirm what you show it. Anything it cannot see for itself is reported as
unverified rather than assumed done.

## What you need

A resume, if you want the contradiction audit -- which is the most valuable part and the one
nobody does for themselves. The skill will run without one and will tell you what you are giving
up.

Two or three real job postings you are actually pursuing, if you want target alignment. Without
them that stage is skipped rather than filled in with guesses.

## What it will not do

- **Work on Company Pages.** Personal profiles only.
- **Touch anyone's profile but yours.** It works on the account you are signed into. It will not
  ask for a password, and it will not drive a session that is not yours.
- **Tell you that your experience is the problem.** That is almost never what the audit finds.
- **Promise recruiters will call.** It fixes visibility and presentation. It cannot add experience
  you do not have, and it has no access to whether anyone actually searched for you.
- **Apply anything you have not approved.** Every change is shown before and after, one field at
  a time, and the field is re-read immediately before writing in case it changed under you.
- **Delete an experience entry.** Regrouping roles is done by editing company names, never by
  deleting and recreating records. If grouping cannot be done without deleting something, the
  skill stops and tells you what you would lose.

## Honest limitations

**LinkedIn changes.** Layouts move and flows change without notice. When something does not look
the way the skill expects, it stops and tells you rather than clicking through.

**Writes can silently fail.** A field can appear to save and revert. The skill types changes as
real input and reads every field back afterward, and it reports applied, failed, and
applied-but-unverified as three different outcomes. The third is not a success.

**You always get the text, and a preserved original.** Before anything is changed, your current
profile is saved to a file, or handed to you to save if the session cannot write files. Whether or
not a write succeeds, the exact wording is also printed. A broken write costs you a copy-paste,
not your profile.

**Automated interaction with LinkedIn sits under LinkedIn's terms of service.** You are choosing
to use a tool that acts on your account. The skill says so before it starts. Decide knowingly.

## Your data

**Where it goes.** Applying a change sends that text to LinkedIn -- that is the point of the
skill, and it only happens for changes you have approved one at a time. Everything you give the
skill also passes through the AI session you are running it in, under whatever terms that
provider and your plan set. This skill does not control that and does not claim to.

If you link to your own site and ask for the link-preview check, the skill fetches pages from
that site. Nothing is written to it.

**What is written to disk.** Where the session can write files, the skill saves a snapshot of your
current profile to `.linkedin-profile/` before changing anything. That is your restore path if a
write goes wrong. It contains your profile text, so treat it like any other copy of your resume.

Some sessions have no filesystem. There the skill hands you your original text and asks you to save
it somewhere yourself before it goes any further. Either way something recoverable exists before
anything is overwritten -- it is just held by you rather than on disk.

Nothing is written inside the skill's own folder, so updating the skill cannot touch your
snapshots. Delete `.linkedin-profile/` when you no longer want them. Note that deleting it also
removes your ability to restore.

## Security

This skill reads and, in full mode, writes to a live account you own. Read the skill before you
install it. That advice applies to every skill you install, including this one.

Maintainers: `tools/check_no_personal_data.py` at the repository root must pass before any
release.

## The useful file

`skills/linkedin-profile/reference/failure-modes.md` is a list of things that have already gone
wrong on a real profile and what each one costs: fields that revert without error, previews that
refuse to generate because of a trailing slash, images cached against a URL so replacing them
changes nothing, an activity feed that hides the entire Experience section from a reader.

That file is what the instructions exist to prevent.
