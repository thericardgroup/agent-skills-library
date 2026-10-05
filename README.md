# Agent Skills Library

Free, open skills for [Claude Code](https://claude.com/claude-code), from
[The Ricard Group](https://thericardgroup.com).

## Install

Add the library once:

```
/plugin marketplace add thericardgroup/agent-skills-library
```

Then install whichever skills you want:

```
/plugin install job-search@agent-skills-library
```

## Skills

| Skill | What it does |
|---|---|
| [job-search](plugins/job-search) | A job search that works whether or not you know what you want. Knows? Profile by interview, read employer job boards directly, score against stated requirements, verify every role is live, generate tailored documents. Doesn't know? Work backwards from what you have done to the role families your record supports, with the evidence, then search those. |

## What these are built around

Each skill here is a workflow that was run by hand long enough to learn where it goes wrong,
then written down. The failure notes in each skill's `references/` are the useful part — they
are what the instructions exist to prevent, and most of them cost a real afternoon.

Two rules apply to everything in this repository:

**Nothing ships with one person's data in it.** `tools/check_no_personal_data.py` runs across
every plugin and fails the build on a phone number, an email, a hardcoded employer list or any
other identity baked into shipped code. These skills grew out of tooling built for one person,
so this is enforced mechanically rather than promised.

**Your data stays yours.** Skills write to `.claude/` in whatever directory you run them from,
never into the installed skill. Updating a skill cannot touch your data, and deleting that
folder is a complete erase.

## Requires

**Claude Code specifically.** These skills fetch live data from the open web, which claude.ai
restricts and the Claude API blocks entirely.

## Contributing and reporting

Issues and pull requests are welcome. If a skill gives you a bad recommendation, the most
useful thing you can send is the input that produced it.

## Security

These skills run scripts and fetch URLs. Read the `scripts/` directory before installing. That
advice applies to every skill you install anywhere, including these.

## License

MIT. See [LICENSE](LICENSE).
