# job-search

A Claude Code skill for running a rigorous job search -- whether or not you know what role you
want.

**If you know what you are looking for:** it builds a profile by interview, finds the employers
hiring for it, reads their job boards directly, scores openings against what they actually
require, verifies every role is still live before you spend time on it, and writes the resume,
cover letter and interview prep.

**If you do not:** it works backwards from what you have actually done to the two or three role
families your record already supports, tells you what in your own history carries each one and
what you would be missing, and then runs the same search on whichever you pick.

You need a resume, or the ability to say what you have done and who paid you for it. That is
the whole entry requirement.

## Install

**New to Claude Code?** Follow the step-by-step guides, with screenshots and no terminal:
[install the Claude desktop app](https://www.thericardgroup.com/guides/install-claude-desktop),
[add this library](https://www.thericardgroup.com/guides/claude-plugin-marketplace),
[install Python](https://www.thericardgroup.com/guides/install-python), [install Node](https://www.thericardgroup.com/guides/install-node),
[install this skill](https://www.thericardgroup.com/guides/job-search-plugin) and [use it](https://www.thericardgroup.com/guides/using-job-search-plugin).

Already in Claude Code? Two lines:

```
/plugin marketplace add thericardgroup/agent-skills-library
```

```
/plugin install job-search@agent-skills-library
```

The skill installs its own packages the first time you use it. Python 3 and Node must already
be on your computer; see [Requires](#requires).

You only add the marketplace once. Any other skill in the library is a single install line
after that.

### Or without a GitHub account

Download the repository as a zip, unpack it, and copy
`plugins/job-search/skills/job-search` to `~/.claude/skills/job-search`. Claude Code picks it
up next time it starts.

Then just say what you need, in your own words:

- "help me find a job"
- "I got laid off and I don't know what I'm looking for"
- "am I a fit for this?" and paste a posting
- "tailor my resume for this role"
- "why am I not getting callbacks?"

You do not have to know which of those you are. The skill works it out.

You do not need to learn any commands. The skill works out where you are and picks up from there,
including if you stop partway through and come back days later.

## Requires

**Claude Code specifically.** The skill fetches live job boards, which claude.ai restricts and the
Claude API blocks entirely.

### You need Python 3 and Node installed

This is the honest version, and it is a real barrier. The skill runs scripts, so both have to
be on your computer before it can do anything past the opening conversation.

**Windows:** neither comes with the operating system. Install **Python 3** from the Microsoft
Store (search "Python 3" -- that version also provides the `python3` command, which the
python.org installer does not) and **Node** from [nodejs.org](https://nodejs.org).

**macOS:** Python 3 arrives with the Xcode command line tools, which you may already have. If
not, run `xcode-select --install` in Terminal. Node comes from [nodejs.org](https://nodejs.org).

**Linux:** both are in your package manager.

Step-by-step guides with screenshots: [install Python](https://www.thericardgroup.com/guides/install-python) and
[install Node](https://www.thericardgroup.com/guides/install-node). The skill needs Python 3.8 or newer; Node is only used to
build the resume and cover letter files.

An earlier version of this page said Python "comes with macOS and most Linux systems" and left
Windows unmentioned. That was wrong, and the first person to install this on Windows hit it.

PDF export is a bonus on macOS with Microsoft Word installed; otherwise you get .docx, which
every employer accepts.

## Runtime, measured

| Step | Time |
|---|---|
| Onboarding interview | ~20 min, once, and you can stop and resume |
| Company discovery | 20-25 min, once, then stable for months |
| Board sweep | 2-10 min depending on company count |
| Scoring | seconds |
| Verification | 15-25 s per role |
| **Reading a posting properly** | **1-3 min per role, and not skippable** |
| Document generation | ~10 s per role |

Scored candidate to submitted package: roughly 15-25 minutes per role.

## Whose job market this can actually see

Four applicant tracking systems are implemented: **Greenhouse, Ashby, Lever and
SmartRecruiters**. Those cover software, startups and a good deal of modern tech-adjacent
hiring well.

They do not cover **Workday, iCIMS, Taleo or SuccessFactors**, which is where most hospitals,
health systems, universities, government and large established employers post. If that is your
market, direct board enumeration will find close to nothing for you, and the skill falls back
to a remote-first aggregator that will miss onsite roles in your city entirely.

This is a real limitation, not a rough edge. It exists because the skill grew out of a search
run against tech employers, and the platforms that got written are the ones that search needed.
Workday and iCIMS are documented in `references/ats-endpoints.md` and not yet built.

Everything downstream of discovery — requirement-level fit analysis, the verification gate,
document generation — works the same regardless of industry. It is finding the openings that
is uneven.

## What it will not do

- Enumerate every opening, even on supported platforms.
- Guarantee a posting is live. It verifies, then expires that verification in three days.
- Tell you you are a great fit when the requirements say otherwise.

## Your data

**Saved on your computer.** What the skill saves about you (profile, scored roles, progress) is
written to `.claude/job-search/` in whatever directory you run it from. It never goes into the
skill's own folder, so updating the skill cannot touch it. Delete that folder and the skill's
saved data about you is gone.

**Sent to Anthropic.** Like any Claude conversation, what you share in the chat -- your resume,
your answers, postings you paste -- is sent to Anthropic so Claude can respond, and is handled
under your Claude account's privacy settings, not by this skill. The skill's own scripts contact
only the job boards they read.

`references/schemas.md` documents exactly what is stored in each file.

## Security

This skill runs scripts and fetches URLs. Read `scripts/` before installing. That advice applies
to every skill you install, including this one.

Maintainers: `tools/check_no_personal_data.py` at the repository root must pass before any
release. It fails the build if one person's identity has leaked into shipped code, which is how
this skill started life.
