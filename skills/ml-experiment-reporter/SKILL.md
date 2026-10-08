---
name: ml-experiment-reporter
description: >
  Writes an evidence-grounded report on a machine learning experiment by reconciling what was
  designed (DESIGN.md), what was built (IMPLEMENTATION.md) and what the runs produced (results/).
  Use this skill whenever a user wants to document, summarise, or write up the outcome of an ML
  experiment — phrases like "write a report", "summarise my results", "write up exp_3",
  "document what happened", "what did my experiment show", "my runs finished", or "we only got
  through half the ablations, write up what we have". Use it for finished, partial and failed
  experiments alike. It writes experiments/exp_N/reports/summary.md, flags missing runs, build
  deviations and unrecorded code versions instead of smoothing them over, and sets the
  experiment's final Status and Verdict. Do NOT use for planning a new experiment (use
  ml-experiment-planner), for exploratory data analysis with no write-up, or for drafting a
  paper section from several experiments at once.
---

# ML Experiment Reporter

Reads an experiment's design, its build plan, and the results on disk, and writes
`reports/summary.md`: what was done, what was found, and what it means.

One principle runs through everything below: **every claim in the report traces to a file.** The
people who read a report mostly never open `results/`, so a plausible number that isn't in the
files does more damage than a visible gap. When the evidence is missing, the report says it is
missing.

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

### 1. Locate the experiment

Use the experiment folder the user names (e.g. `experiments/exp_3`), or ask for it. Before
reading further, check it looks like an experiment folder — a `DESIGN.md` (or an older
`PLAN.md`) and/or a `results/` directory.

- **Neither is there**, or the metrics are scattered through a flat project: don't guess and
  don't assemble a report from a structure you can't locate. Say so and work only from the paths
  the user gives back:
  > ⚠️ This folder doesn't match the layout I expect (`DESIGN.md` + `results/<condition_id>/seed_<s>/`).
  > Point me to where the design and the per-run results live, or run the ml-experiment-planner
  > skill first to set up the structure.
- **Results but no design file**: warn that there is nothing to cross-reference against, then
  report the results alone. With no pre-specified decision rule the verdict is ⚠️ Inconclusive,
  and the report says that is the reason.

### 2. Read the plans

From `DESIGN.md`, take: the **tier**, the hypothesis sentence, the **Conditions** table (ids and
roles), the primary metric and its `metrics.json` key, the planned seeds, and the decision rule.
From `IMPLEMENTATION.md`, take: the run matrix (which config and command produced each
condition), what every run was meant to record, and the **Deviations Log**.

If `IMPLEMENTATION.md` is absent, carry on and note it under caveats — build deviations can then
only be inferred from configs and git, not confirmed.

Older designs may have numbered sections, no tier, and conditions described in prose without
ids. Treat a missing tier as Standard, map each described condition to a `results/` directory by
your best reading, and print that mapping in the report so the reader can check it.

### 3. Inventory the results

Run the bundled script — `scripts/collect_results.py`, in the same directory as this SKILL.md —
with the values you just read from the design:

```bash
python <skill_dir>/scripts/collect_results.py experiments/<exp_id> \
    --primary <primary metric key> --baseline <baseline condition id> \
    --expect <id1>,<id2>,<id3> --seeds <planned seeds per condition> \
    --out experiments/<exp_id>/reports/inventory.json
```

It reads only what is on disk and returns, as JSON: every condition directory and run it found;
per-metric mean, std and n; the per-seed values of the primary metric; coverage against the
planned conditions and seed count; each condition's paired comparison with the baseline; and the
recorded commit of every run, including which runs have none, which were launched dirty, and
whether all runs share one commit. It also lists the configs, figures and environment files
that exist.

Take the report's numbers from this output rather than recomputing them, and round only for
display. Saving it as `reports/inventory.json` gives every number in the report a source someone
can open. A few things the script can't settle for you:

- A run flagged `looks_pre_aggregated` holds a mean/std rather than one run's values. Report it
  as given, with n unknown, and do no statistics on it.
- Metrics stored as CSV, YAML or per-epoch logs are invisible to the script. Read them directly
  and say in the report which files the numbers came from.
- If Python isn't available, do the same inventory by reading the files, and say so.

### 4. Reconcile design, build and results

Three kinds of divergence come out of the comparison. They mean different things to a reader,
so they go to different places in the report:

| Kind | What it looks like | Where it goes |
|------|--------------------|---------------|
| **Coverage gap** | A planned condition has no results, fewer seeds than planned, or no primary metric | *Missing Data & Caveats*; its row stays in the results tables marked _Not run_ |
| **Build deviation** | A condition ran, but not as designed — an entry in the Deviations Log, or a config that disagrees with `DESIGN.md` | *Setup As Run → Deviations* |
| **Provenance gap** | A run has no `git_commit.txt`, was launched `DIRTY`, or compared conditions ran from different commits | *Code Version* |

To find build deviations, read the config of each condition (the run matrix says which) and
check the settings `DESIGN.md` actually specifies. Don't rely on the Deviations Log alone — it
only holds what someone remembered to write down.

When compared conditions come from different commits, the difference between them may not be
only the intended intervention. If the repository is at hand, `git diff --stat <sha_a> <sha_b>`
shows what else changed; report what the diff shows, and if a commit isn't in the repository,
report that instead.

### 5. Decide Status and Verdict

**Status** follows from coverage, using the contract's definitions: Complete, Partial or Failed.

**Verdict** is the design's decision rule applied as written — not a fresh judgement made after
seeing the numbers. It is ⚠️ Inconclusive whenever the rule cannot be applied as pre-specified:

- the result falls between the *supported* and *refuted* thresholds;
- the primary comparison is missing a side, or has fewer seeds than the rule assumed;
- the threshold is met on the means but the statistical criterion the design named is not;
- a deviation or provenance gap undercuts the comparison itself (for example the proposed
  condition ran from a different, or dirty, tree than the baseline) — say which one;
- the design has no decision rule.

### 6. Write the report

Write `experiments/<exp_id>/reports/summary.md` with the Write tool. Size it to the design's
tier: a Lean design gets the Lean report, since a ten-section write-up of a two-run sanity check
hides the answer. If a `summary.md` already exists, read it first; the new report replaces it
and carries a line under the header saying what it supersedes and why (e.g. "Supersedes the
report of 2026-05-30: two more conditions finished").

**Lean report:**

```markdown
# Experiment Report: [Title from DESIGN.md]
**Experiment**: experiments/<exp_id>/ · **Report date**: YYYY-MM-DD · **Status**: <status> · **Verdict**: <verdict>

## Summary
Two or three sentences: the hypothesis, whether it held, the number that decides it.

## Results
| Condition id | <primary metric> per seed | Mean ± std | Δ vs. baseline | Commit |
|--------------|---------------------------|------------|----------------|--------|

Decision rule (from the design): "<quoted>" → met / not met / cannot be evaluated because <…>.

## Deviations & Missing Data
Deviations Log entries, config mismatches, runs that didn't finish, missing or dirty
`git_commit.txt` — or "None: ran as planned."

## Next Step
One or two lines.
```

**Standard / Full report:**

```markdown
# Experiment Report: [Title from DESIGN.md]
**Experiment**: experiments/<exp_id>/  
**Project**: <project_name>  
**Report date**: YYYY-MM-DD  
**Design date**: <date from DESIGN.md>  
**Author**: <name or TBD>  
**Status**: <Complete | Partial | Failed>  
**Verdict**: <✅ Supported | ❌ Refuted | ⚠️ Inconclusive>

## 1. Summary
Two to four sentences for someone who reads nothing else: the hypothesis, whether it was
supported, the key number. If a deviation or gap materially limits the conclusion, flag it here
with ⚠️.

## 2. Hypothesis & Verdict
**Hypothesis (from the design):** _the exact sentence_

**Verdict:** <verdict>

**Evidence:** one or two sentences — the primary-metric difference, and how it sits against the
decision rule.

## 3. Setup As Run
What was actually built and run, from the configs and run artifacts.

- **Dataset**: <name, version, split>
- **Model**: <architecture>
- **Training**: <optimizer, LR, batch size; epochs completed>
- **Hardware / runtime**: <from run artifacts, or "not recorded">
- **Deviations from the design**: <each Deviations Log entry and each config mismatch, with the
  conditions affected — or "None found">

## 4. Code Version
| Condition id | Commit(s) | Subject | Clean tree? | Runs without a recorded commit |
|--------------|-----------|---------|-------------|--------------------------------|

One line on whether every compared condition ran from the same commit, and if not, what differs.

## 5. Results

### 5.1 Primary metric: <name> (`<key>`)
| Condition id | Role | Mean ± std | n seeds | Δ vs. <baseline id> |
|--------------|------|------------|---------|---------------------|

Every planned condition has a row; one that didn't run reads _Not run_.

### 5.2 Secondary metrics
### 5.3 Ablations (if any)
| Condition id | What it removes | Primary metric | Δ vs. full method | Reading |
|--------------|-----------------|----------------|-------------------|---------|

### 5.4 Figures
Existing files in `reports/figures/`, by relative path, each with a sentence on what it shows.
Then, if useful ones are missing: "Suggested figures: …".

## 6. Statistical Analysis
Primary comparison: <proposed id> vs. <baseline id> on `<key>`, paired over <n> shared seeds.
- **Per-seed differences**: …
- **Mean difference**: … (95% CI [low, high], paired t interval)
- **Sign-flip permutation test**: p = … (smallest p reachable with <n> pairs: …)
- **Reading**: …

Other comparisons are exploratory unless the design pre-specified them.

## 7. Comparison to Decision Rules
| Rule from the design | Observed | Met? |
|----------------------|----------|------|

## 8. Missing Data & Caveats
| Condition id | Planned seeds | Runs with the primary metric | Gap |
|--------------|---------------|------------------------------|-----|

Then, in prose: each planned condition, seed or metric that is missing and why (if known);
conditions found in `results/` that the design never planned; whether `IMPLEMENTATION.md` was
available. If nothing is missing: "All planned runs completed."

## 9. Conclusions & Next Steps
- **What this experiment established**
- **What remains uncertain**
- **Recommended follow-ups** — refer to existing experiments in `INDEX.md` by id where relevant;
  a new one starts with the ml-experiment-planner skill.

## 10. Reproducibility Record
| Item | Status | Evidence |
|------|--------|----------|
| Seeds logged | | `seed` in each metrics.json |
| Configs saved | | files in scripts/configs/ |
| Git commit per run | | see §4 |
| Launched from a clean tree | | no DIRTY lines |
| Checkpoints saved | | |
| Environment pinned | | path of the lock/requirements file |
| Tracker linked | | run URL |
```

**Rules of evidence** — the reasons behind the template's shape:

- **Numbers come from files.** Each one is in `inventory.json` or in a file the report names.
- **"As run" means observed.** Epochs completed, runtime and hardware come from run artifacts
  or configs. If only the plan states a value, write it as "planned: … (not recorded by the
  run)". Copying the design into *Setup As Run* turns an intention into a false record.
- **A ✅ needs a path.** In the Reproducibility Record, mark ✅ only where the Evidence column
  can cite a file, ❌ where the evidence shows it is absent, and "unverified" otherwise.
- **Missing is stated, not filled in.** A planned condition that didn't run keeps its row,
  marked _Not run_. If the primary metric is absent from the results files, say so; don't
  reconstruct it from logs or stand a secondary metric in for it.
- **No statistics without per-seed values.** With fewer than two shared seeds, or with only
  pre-aggregated numbers, write "Per-seed values not available; no test computed" and give no
  p-value or interval. Below six pairs a permutation p cannot go under 0.05 whatever the data,
  so lean on the interval and the per-seed differences and say why. If the design called for a
  test the script doesn't compute, run it in code and show the command, or say it was not
  computed.
- **Figures that exist.** Reference files in `reports/figures/`; don't describe plots that
  aren't there.
- **Write for a reader who hasn't seen the design.** Specific numbers over adjectives, and no
  claim of success or failure beyond what the numbers carry. Use ✅ / ❌ / ⚠️ consistently.

### 7. Close out the experiment

1. Set the `Status` field in `DESIGN.md` to the report's status with a one-word Edit (in
   `PLAN.md` for an older experiment). Leave the rest of the file alone — it is the record of
   what was intended, and rewriting it after the fact would erase that.
2. In the experiment's `experiments/INDEX.md` row, set the same Status and the Verdict, linking
   the verdict to the report: `[✅](exp_3/reports/summary.md)`. If there is no `INDEX.md`, skip
   this.
3. Tell the user where the report is, and show the Summary and the Conclusions in chat so they
   get the takeaways without opening the file.

Those two edits and the files under `reports/` are everything this skill writes. It does not
touch `IMPLEMENTATION.md`, the configs, or anything in `results/`.

---

## Example Invocations

- "Write a report for exp_3" → read both plans, inventory `results/`, write the report
- "My experiment finished, document the results" → ask which experiment, then report
- "Write up exp_2, we didn't finish all the ablations" → Partial; the missing ablations keep
  their rows and are listed under Missing Data
- "What did the augmentation sanity check show?" → Lean design, Lean report
- "The runs all crashed after epoch 2, write up what we have" → Failed; verdict Inconclusive
