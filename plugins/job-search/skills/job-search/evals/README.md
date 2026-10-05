# Evaluating this skill

## The mistake this harness exists to prevent

Iteration 1 scored **100% with the skill against 72% without it**, and the skill's entire
execution layer was broken at the time. Verification self-certified, scoring ranked for the
author rather than the user, the document generators could not be imported, and state was
written where the gate could not read it.

The harness missed all of it because **every assertion was about what the model said.** The
graded personas had a conversation, the conversation read well, and nothing ever ran. A skill
can describe a rigorous process fluently while doing none of it, and prose assertions cannot
tell the difference.

So assertions here come in two kinds, and an eval that only has the first kind is not finished.

## Two kinds of assertion

**`transcript`** — judged by reading the output. Tone, pacing, whether it asked one question or
five, whether it exposed machinery. These need human or model judgment and there is no
substitute.

**`artifact`** — checked by `check_artifacts.py`, which reads the state directory and the
generated files. Did a profile get written? Does it describe this user or the author? Do the
postings carry requisition ids? Did the gate actually refuse something? Is the name on the
.docx the right name?

Artifact checks are the ones that catch a skill that talks well and does nothing.

## Running the checks

```bash
python3 evals/check_artifacts.py --list

python3 evals/check_artifacts.py \
  --state <run's JOB_SEARCH_STATE> \
  --outputs <where documents were written> \
  --skill . \
  --persona-terms "product designer,san francisco"
```

Output matches the `expectations` shape the viewer expects (`text`, `passed`, `evidence`), so
`--json` can be written straight into a run's `grading.json`.

Give each subagent run its own state directory so runs cannot contaminate each other:

```bash
export JOB_SEARCH_STATE=$(mktemp -d)
```

This also matters for a reason iteration 1 learned the hard way: one baseline run inherited the
real working directory, found actual search data, and refused for that reason rather than
because of any gate. The comparison was meaningless.

### Negated checks

For a refusal eval, success is that nothing was produced:

```bash
python3 evals/check_artifacts.py --state <dir> \
  --checks documents_generated --negate documents_generated
```

### Not applicable

A check with nothing to inspect reports `n/a` rather than passing. A guard that passes on an
empty directory is exactly the non-discriminating assertion that produced the false 100%.

## Calibration

The checker is only useful if it separates the two cases. It is verified against both:

| Run | Score |
|---|---|
| Conversation only, nothing executed | **0/9**, 3 n/a |
| Full pipeline, live boards | **12/12** |

Re-run that comparison after changing any check. A check that passes in both columns is
measuring nothing.

## Adding a check

Add a function to `check_artifacts.py` decorated with `@check("name")`, returning
`(passed, evidence)`. Return `None` for passed when there is nothing to inspect. Evidence is
written into the grading output, so say what was actually on disk — `"3 of 165 postings lack a
requisition id"` is useful where `False` is not.
