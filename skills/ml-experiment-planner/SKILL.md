---
name: ml-experiment-planner
description: >
  Plans a machine learning experiment and writes two files: DESIGN.md (the research design —
  falsifiable hypothesis, conditions, metrics, decision rule) and IMPLEMENTATION.md (the build
  plan — run matrix, configs, code changes, what every run must record). Use this skill whenever
  a user wants to design, plan, or structure an ML experiment before running it: baseline
  comparisons, ablations, hyperparameter sweeps, architecture or data experiments, fine-tuning
  runs. Trigger on "experiment plan", "research plan", "design an
  experiment", "ablation study", "how should I test", "benchmark X against Y", "compare these
  approaches", "how do I know if X works better than Y", or any request to systematically
  validate an ML idea, even if the user never says "plan". It plans; it does not write scripts
  or launch runs. Do NOT use for writing up existing results (use ml-experiment-reporter), for
  running or debugging an existing evaluation, for pure theory or math questions, or for non-ML
  software engineering.
---

# ML Experiment Planner

Turns a research question into two documents on disk, sized to the stakes — from an afternoon
sanity check to a paper-grade campaign.

## What This Skill Writes

| File | Answers | Contains |
|------|---------|----------|
| `experiments/<exp_id>/DESIGN.md` | What are we testing, and how will we know? | Hypothesis, conditions, metrics, decision rule, risks |
| `experiments/<exp_id>/IMPLEMENTATION.md` | What do we build and run to test it? | Run matrix, configs, code changes, what each run records, deviations log |
| `experiments/INDEX.md` | Where does this sit in the campaign? | One registry row per experiment |

The two plans are separate files because they change for different reasons and the reporter
compares them: `DESIGN.md` is what was *intended*, `IMPLEMENTATION.md` is what was *built*, and
`results/` is what *happened*. So keep code-level detail (file names, configs, commands) out of
`DESIGN.md` — a design that names scripts goes stale the first time the build changes, and the
research claim gets buried under plumbing.

The skill stops at the documents. It does not write scripts or configs and does not launch runs:
the user reviews both files first, and building the experiment is ordinary coding work that
follows their approval.

<!-- contract:start (this block is byte-identical in ml-experiment-planner and ml-experiment-reporter) -->
## Shared Layout Contract

The planner and the reporter never talk to each other; they find each other's work by path. Both
therefore assume this layout inside the user's project:

```
<Project>/
├── docs/  src/  data/                  ← shared across experiments
└── experiments/
    ├── INDEX.md                        ← registry, one row per experiment (planner adds, reporter updates)
    └── exp_<n>/
        ├── DESIGN.md                   ← planner: what is tested and how it will be judged
        ├── IMPLEMENTATION.md           ← planner: how it is built and run; deviations are logged here
        ├── scripts/                    ← run scripts; configs in scripts/configs/
        ├── results/
        │   └── <condition_id>/         ← directory name = a condition id from DESIGN.md
        │       └── seed_<s>/           ← one directory per run
        │           ├── metrics.json    ← that run's final metrics
        │           ├── git_commit.txt  ← code version the run was launched from
        │           └── checkpoints/
        └── reports/
            ├── inventory.json          ← reporter: machine-readable inventory of results/
            ├── figures/
            └── summary.md              ← reporter: the report
```

- **Condition ids.** Every condition in `DESIGN.md` has a short id (`lowercase_with_underscores`)
  and its runs live in `results/<that id>/`. Matching by id is what lets the reporter tell "not
  run" from "named differently".
- **One directory per run.** `seed_<s>/metrics.json` is a flat JSON object holding that run's
  final metrics, including `seed` and the primary metric under the exact key `DESIGN.md` names.
  Per-seed files are what make a spread or a significance test computable; a pre-averaged number
  is not enough.
- **`git_commit.txt`, one per run.** Line 1 is `<full sha> <subject>`. A second line starting
  with `DIRTY` records that tracked files had uncommitted changes at launch:
  ```bash
  git log -1 --format="%H %s" > "$RUN_DIR/git_commit.txt"
  git diff --quiet HEAD || echo "DIRTY: uncommitted changes at launch" >> "$RUN_DIR/git_commit.txt"
  ```
- **Status** says how far *execution* got: `Draft` (planner) → `In Progress` (set when the first
  run launches — a step in `IMPLEMENTATION.md`) → `Complete` / `Partial` / `Failed` (reporter).
  Complete: every planned run produced the primary metric. Partial: some planned runs are
  missing, but at least one planned comparison can be made. Failed: no planned comparison can be
  made.
- **Verdict** says what the results mean for the *hypothesis*: ✅ Supported / ❌ Refuted /
  ⚠️ Inconclusive, decided by the decision rule in `DESIGN.md`. The two are independent — a
  hypothesis cleanly refuted by a full set of runs is `Complete` + ❌, not `Failed`.
- **Both fields live in two places**, the `DESIGN.md` header and the experiment's `INDEX.md` row,
  and must agree.
- **Older experiments** may have `PLAN.md` instead of `DESIGN.md`, no `IMPLEMENTATION.md`, or
  metrics directly in `results/<condition_id>/`. Read them as they are; don't rename or migrate
  them.
<!-- contract:end -->

---

## Workflow

### 1. Understand the question

Pull what you can from the conversation before asking anything:

- **Hypothesis** — the specific claim being tested
- **Task and data** — ML task, dataset(s), modality
- **Intervention** — the new idea, and what it is being compared against
- **Prior numbers** — existing baselines or published results to match
- **Constraints and stakes** — compute budget, deadline, exploratory check vs. paper claim
- **Where it runs** — local, shared cluster, job scheduler; experiment tracker; where large
  artifacts go; how the environment is pinned

Then ask **once**, in a single batch of two to four questions, for whatever is still missing
*and* would change the design or the build. A vague prompt like "I want to test my new loss
function" needs that round; a detailed one may need none. Anything with a sensible default is
not worth a question — pick the default and record it under "Assumptions & Open Questions" in
`IMPLEMENTATION.md`, where the user will see it at review. Planning an afternoon's experiment
should not take three rounds of interview.

### 2. Locate the experiment folder

Check the project root for an `experiments/` directory (and, loosely, `src/` and `data/`). The
reporter will later look for results at exact paths, so a plan written into a layout that isn't
there doesn't fail now — it resurfaces as a confusing reporting failure. Three cases:

1. **Layout matches.** Take the next free id (`exp_4` if `exp_1`–`exp_3` exist), say which path
   you are using, and carry on. No confirmation round is needed.
2. **No project yet.** Ask for the project root and name (fold this into the question batch
   above), then scaffold.
3. **Project exists but doesn't match** — no `experiments/`, a flat repo, results in `outputs/`
   or `runs/`. Don't silently write into it. Say what you found and offer the choice:
   > ⚠️ This project doesn't follow the layout I expect (`experiments/exp_N/` with `DESIGN.md`,
   > `results/<condition_id>/seed_<s>/`, `reports/`). I can **create that structure alongside
   > your existing files**, or **write the plan where you point me** and you manage the paths
   > yourself. Which do you prefer?
   - *Create alongside* → add new directories only. Never move, rename, or reorganise existing
     files: relocating code breaks imports and is hard to undo, so it needs its own explicit
     request.
   - *Write where pointed* → write both plans at the path given and put a ⚠️ note at the top of
     each saying the layout is non-standard, so the reporter will need paths pointed out.

```bash
# New project
mkdir -p <project>/{docs,src,data,experiments/exp_1/{scripts/configs,results,reports/figures}}
# New experiment in an existing project
mkdir -p <project>/experiments/exp_<n>/{scripts/configs,results,reports/figures}
```

### 3. Pick the tier

Decide how much plan the work warrants before writing any of it. A plan exists to make the
experiment runnable and its result interpretable; wrapping a yes/no sanity check in a risk
register and a compute table buries the one thing that matters.

| Tier | When | Shape |
|------|------|-------|
| **Lean** | Sanity check, "does X help at all", a single afternoon | Lean templates, a few sentences per section |
| **Standard** | Ablation, method comparison, anything you will act on | Full templates; drop sections that don't apply |
| **Full** | Paper submission, large sweep, expensive benchmark | Full templates, every section |

Between two tiers, pick the smaller — adding a section later is cheaper than making a reader
wade through padding. Write the tier into the `DESIGN.md` header; the reporter reads it to size
the report to match.

### 4. Look at the code before planning the build

Read enough of `src/` and of earlier experiments' `scripts/` to know what already exists: the
training entry point, the config format, how metrics get written. `IMPLEMENTATION.md` should
name real files and reuse them — a plan that proposes a new `train.py` beside a working one, or
flags the existing CLI doesn't have, costs the user a rewrite. If there is no code yet, say so
and mark everything as new. Keep this proportional: a glance for Lean, a proper read for Full.

### 5. Write `DESIGN.md`

Use the Write tool (the documents contain tables and code fences that a shell heredoc mangles).
Write a single value in `Status` — `Draft` — because the reporter later replaces that one word.

**Lean:**

```markdown
# Experiment Design: [Descriptive Title]
**Experiment**: experiments/<exp_id>/ · **Project**: <project_name> · **Date**: YYYY-MM-DD · **Tier**: Lean · **Status**: Draft

## Hypothesis
One falsifiable sentence, e.g. "Random-crop augmentation improves MNIST test accuracy."

## Setup
Dataset, model, and the one thing that varies. 3–5 bullets.

## Conditions
| id | Role | What it is |
|----|------|------------|
| baseline | baseline | ... |
| random_crop | proposed | baseline + random-crop augmentation |

Seeds: <list>, the same for every condition.

## Metric & Decision
Primary metric: <name> (`<key in metrics.json>`). Supported if <threshold>; refuted if <...>;
anything else is inconclusive.
```

**Standard / Full** (the maximal form — for Standard, drop what doesn't apply, but keep the
section names, since the reporter looks sections up by name):

```markdown
# Experiment Design: [Descriptive Title]
**Experiment**: experiments/<exp_id>/  
**Project**: <project_name>  
**Date**: YYYY-MM-DD  
**Author**: <name or TBD>  
**Tier**: Standard  
**Status**: Draft

## Hypothesis
A single falsifiable sentence, e.g. "Replacing cross-entropy with focal loss improves macro-F1
on the imbalanced split by ≥0.02."

## Setup
- **Dataset(s)**: name, version or hash, split strategy, preprocessing
- **Model**: architecture and size
- **Training**: optimizer, schedule, batch size, budget in epochs or steps
- **Tuning budget**: how much hyperparameter search each condition gets — equal across
  conditions, or the reason it isn't

## Conditions
| id | Role | What differs from the baseline | What it isolates | Expected <primary metric> |
|----|------|-------------------------------|------------------|---------------------------|
| baseline_ce | baseline | — | reference point | 0.80–0.82 (prior run) |
| focal_g2 | proposed | focal loss, γ=2 | the hypothesis | ≥ baseline + 0.02 |
| focal_g2_no_reweight | ablation | focal loss without class reweighting | whether the gain is the loss or the reweighting | — |

Role is one of baseline / proposed / ablation. For a sweep, give the search strategy (grid,
random, Bayesian), the ranges, and the id pattern (e.g. `lr_<value>`).

## Evaluation Protocol
- **Primary metric**: name, exact key in `metrics.json`, and the split it is computed on
- **Secondary metrics**: names and keys
- **Seeds**: how many and which, the same for every condition so comparisons can be paired
- **Checkpoint selection**: which checkpoint's number is reported (e.g. best validation
  checkpoint, evaluated on test once)
- **Statistical analysis**: the one primary comparison, and what will be computed for it

## Decision Rules
- **Supported if** …
- **Refuted if** …
- **Inconclusive if** … (the zone between the two, or fewer seeds than planned)
- **Then what**: the next step under each outcome
- **Stopping criteria** for expensive sweeps

## Compute Budget
conditions × seeds = runs; × hours per run = GPU-hours, set against the available budget.

## Risks & Mitigations
Two to four specific risks, each with its mitigation.

## Reproducibility Requirements
What must hold for every run (the commands that achieve it are in IMPLEMENTATION.md):
- Seeds fixed and written to `metrics.json`
- Dataset version or hash recorded in Setup above
- Code version recorded per run in `git_commit.txt`, launched from a committed tree
- Environment pinned
- One saved config per condition
```

### 6. Write `IMPLEMENTATION.md`

This is the file that travels with the experiment into execution, so it has to be usable by
someone (or some later session) that has not seen this conversation. Its run matrix must carry
exactly the condition ids from `DESIGN.md` — no extras, none dropped.

**Lean:**

````markdown
# Implementation Plan: [Same Title as DESIGN.md]
**Experiment**: experiments/<exp_id>/ · **Design**: [DESIGN.md](DESIGN.md) · **Date**: YYYY-MM-DD

## Run Matrix
| Condition id | Command | Seeds | Writes to |
|--------------|---------|-------|-----------|
| baseline | `python scripts/train.py --seed $SEED` | 0 | `results/baseline/seed_$SEED/` |
| random_crop | `python scripts/train.py --augment random_crop --seed $SEED` | 0 | `results/random_crop/seed_$SEED/` |

Code to add or change: one or two lines, naming the files.

## What Every Run Records
In `results/<condition_id>/seed_<s>/`: `metrics.json` with `seed` and `<primary key>`, and
`git_commit.txt`, written by the run script at launch:
```bash
git log -1 --format="%H %s" > "$RUN_DIR/git_commit.txt"
git diff --quiet HEAD || echo "DIRTY: uncommitted changes at launch" >> "$RUN_DIR/git_commit.txt"
```
When the first run launches, set **Status** to `In Progress` in DESIGN.md and its INDEX.md row.

## Deviations Log
Append a row whenever what is built or run departs from this plan or from DESIGN.md.

| Date | What changed | Why | Conditions affected |
|------|--------------|-----|---------------------|
| — | None so far | | |
````

**Standard / Full:**

````markdown
# Implementation Plan: [Same Title as DESIGN.md]
**Experiment**: experiments/<exp_id>/  
**Design**: [DESIGN.md](DESIGN.md)  
**Date**: YYYY-MM-DD

## Run Matrix
One row per condition id in DESIGN.md.

| Condition id | Config | Command | Seeds | Writes to |
|--------------|--------|---------|-------|-----------|
| baseline_ce | `scripts/configs/baseline_ce.yaml` | `python scripts/train.py --config scripts/configs/baseline_ce.yaml --seed $SEED` | 0 1 2 | `results/baseline_ce/seed_$SEED/` |

## Code Changes
Paths are relative to the experiment folder; shared code is `../../src/...`.

| File | New / modify | What and why |
|------|--------------|--------------|
| `scripts/train.py` | new | entry point: loads a config, trains, writes the run directory |
| `../../src/losses.py` | modify | add focal loss next to the existing cross-entropy wrapper |

## What Every Run Records
Each run writes into `results/<condition_id>/seed_<s>/`:
- `metrics.json` — flat JSON with `seed`, `<primary key>`, `<secondary keys>`, plus
  `epochs_completed` and `train_time_hours`, so the report can state what actually ran rather
  than what was planned
- `git_commit.txt` — written by the run script at launch, not by hand:
  ```bash
  git log -1 --format="%H %s" > "$RUN_DIR/git_commit.txt"
  git diff --quiet HEAD || echo "DIRTY: uncommitted changes at launch" >> "$RUN_DIR/git_commit.txt"
  ```
- `checkpoints/` — add `experiments/*/results/**/checkpoints/` to `.gitignore`; do commit
  `metrics.json` and `git_commit.txt`
- Tracker, if one is used: log the commit hash and the condition id as run parameters

## Execution Order
1. Make the code changes and commit them, so every condition launches from the same commit.
2. Smoke-test one condition with one seed for a few steps; check the run directory holds the
   files above with the right keys, then delete it.
3. Set **Status** to `In Progress` in DESIGN.md and in its INDEX.md row.
4. Launch the run matrix (order, parallelism, scheduler details).
5. When the runs finish — or you stop early — ask for the report; the ml-experiment-reporter
   skill reads this folder.

## Assumptions & Open Questions
Defaults chosen without asking, and anything the user should confirm before building.

## Deviations Log
Append a row whenever what is built or run departs from this plan or from DESIGN.md — a changed
hyperparameter, a dropped seed, a condition cut for budget. The reporter reads this table; a
change that isn't logged here shows up at report time as an unexplained discrepancy.

| Date | What changed | Why | Conditions affected |
|------|--------------|-----|---------------------|
| — | None so far | | |
````

### 7. Register the experiment in `INDEX.md`

If `experiments/INDEX.md` doesn't exist, create it from the template below. The header is the
project's own record of this layout — the skills are installed separately from the project, so
without it nothing on disk explains where things go. If it exists, append one row with the Edit
tool and leave everything else alone, including older rows that link to `PLAN.md`.

```markdown
# Experiments Index — <project_name>

Each `exp_<n>/` folder holds:
- `DESIGN.md` — what is tested and how it will be judged
- `IMPLEMENTATION.md` — how it is built and run, plus a deviations log
- `results/<condition_id>/seed_<s>/` — one directory per run, with `metrics.json` and `git_commit.txt`
- `reports/summary.md` — the write-up

**Status** is how far execution got: Draft → In Progress → Complete / Partial / Failed.
**Verdict** is what the results say about the hypothesis: ✅ supported, ❌ refuted, ⚠️ inconclusive.

| Exp | Title | Status | Hypothesis (1 line) | Verdict | Date |
|-----|-------|--------|---------------------|---------|------|
| [exp_1](exp_1/DESIGN.md) | Focal vs. CE on CheXpert | Draft | Focal loss improves macro-F1 by ≥0.02 | — | 2026-05-23 |
```

### 8. Hand both plans back for review

Tell the user where the files are, then give a short summary in chat — the full text is on disk:

- the hypothesis and the decision rule
- the size of the run matrix and the compute estimate
- the assumptions you made that they should confirm

Ask them to review both documents, and wait for that before writing any scripts or configs. The
review is the checkpoint that keeps a wrong assumption from turning into a week of wrong runs.

---

## What Makes a Design Hold Up

Use these to shape the plan, and add a ⚠️ note inline wherever the user's proposed setup runs
into one.

- **Write the decision rule before the data exists.** Name the threshold for *supported*, the
  one for *refuted*, and call everything between them *inconclusive*. Without the middle zone,
  a +0.3-point wobble gets read as a win after the fact.
- **Pair the seeds.** Use the same seed list for every condition so each comparison is paired;
  it removes seed-to-seed variance from the difference. Three seeds is the floor for anything
  that will be acted on, five or more for a paper claim.
- **Match the test to the seed count.** A paired rank or permutation test over *n* seeds cannot
  produce a two-sided p below 2/2ⁿ — 0.25 at three seeds, 0.0625 at five — so "p < 0.05" is
  unreachable below six seeds whatever the data. With fewer, plan to report the per-seed
  differences, mean ± std, and a confidence interval on the paired difference, and phrase the
  decision rule as an effect size relative to seed noise.
- **Name one primary comparison.** With several conditions against one baseline, some
  difference will look significant by chance. Pre-specify the comparison the hypothesis rests
  on; treat the rest as exploratory or correct for multiplicity (Holm).
- **Fix checkpoint selection in advance.** Reporting the best test-set checkpoint is tuning on
  test. Select on validation, evaluate on test once.
- **Give baselines the same tuning budget.** An under-tuned baseline is the most common way a
  method "wins".
- **Check the budget against what was stated.** conditions × seeds × hours per run, compared
  with the budget from step 1. If it doesn't fit, cut seeds for an exploratory pass, use a
  smaller proxy task first, or drop conditions — in the design, not silently mid-run.
- **Look for the usual confounds**: validation or test statistics leaking into preprocessing,
  optimising one metric while reporting another, a gain that can't be attributed because no
  ablation separates its components, conditions launched from different commits.

---

## Example Invocations

- "I want to test whether data augmentation helps my image classifier" → Lean: two conditions,
  short DESIGN.md and IMPLEMENTATION.md
- "Design an ablation study for my new attention mechanism" → Standard: one condition per
  removed component, each with an id and a row in the run matrix
- "How should I benchmark my new optimizer against Adam?" → Standard: matched tuning budgets,
  paired seeds
- "I'm submitting to NeurIPS, help me plan my experiments" → Full: every section, six or more
  seeds if a significance claim is wanted
