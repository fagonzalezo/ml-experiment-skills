---
name: ml-experiment-planner
description: >
  Generates structured, rigorous experiment plans for machine learning research. Use this skill
  whenever a user wants to design, plan, or structure an ML experiment — including baseline
  comparisons, ablation studies, hyperparameter sweeps, architecture searches, data
  experiments, fine-tuning runs, or evaluation protocols. Trigger on phrases like "experiment
  plan", "research plan", "how should I test", "design an experiment", "ablation study",
  "benchmark this", "evaluate my model", "compare these approaches", or any request to
  systematically validate an ML idea or hypothesis. Also use for questions like "how do I
  know if X works better than Y" in an ML context. Produces a research-design plan (hypothesis,
  conditions, metrics, decision rules) — NOT a code-implementation plan. Implementation planning
  is a separate follow-up step, ideally run in plan mode after the experiment plan is accepted.
  Do NOT use for pure theory questions, math derivations, non-ML software engineering tasks,
  or for planning the code/scripts that implement an experiment (that is a separate
  implementation-planning step, ideally run in plan mode).
---

# ML Experiment Planner

Generates clear, actionable experiment plans for ML research — from quick ablations to
full research campaigns.

---

## What This Skill Produces (and What It Does Not)

**This skill produces an experiment plan** — a research-design document that captures:
- A falsifiable hypothesis
- Experimental conditions and baselines
- Evaluation metrics and decision rules
- Risks and reproducibility requirements

**It is NOT an implementation plan.** The experiment plan must not contain function-level code design, refactor steps, file-by-file edit lists, or task breakdowns for writing code.

**After the experiment plan is accepted by the user**, the natural next step is a separate **implementation plan** — covering which scripts to add or modify under `experiments/<exp_id>/scripts/`, what reusable code to add to `../../src/`, configs, and any data-pipeline changes. That implementation plan should be built in **Claude Code's plan mode** (or an equivalent review-before-edit flow) so the user can review and approve before any files are touched. Do not start editing implementation files from within this skill.

This skill does not *write* the implementation plan, but it owns the convention for where it lives: once approved, the implementation plan is saved as `experiments/<exp_id>/IMPLEMENTATION.md`, right next to `DESIGN.md`. Keeping the two together matters downstream — the reporter reads `IMPLEMENTATION.md` to map each condition to the config/script that produced it and to detect where the build diverged from the design. An implementation plan that lives only in a chat transcript is lost by report time.

---

## Project Structure

Experiments live inside a standardized project layout:

```
<Project>/
├── docs/          ← shared: documentation, references
├── src/           ← shared: model code, utilities, data loaders
├── data/          ← shared: raw and processed datasets
└── experiments/
    ├── INDEX.md        ← registry of all experiments (id, title, status, verdict)
    ├── exp_1/
    │   ├── DESIGN.md            ← experiment (research-design) plan — written by THIS skill
    │   ├── IMPLEMENTATION.md  ← implementation plan, saved after plan-mode approval
    │   ├── scripts/           ← run scripts, configs, sweep definitions
    │   ├── results/           ← model outputs, metrics, checkpoints
    │   └── reports/           ← figures, summaries, final write-ups
    ├── exp_2/
    │   └── ...
    └── exp_n/
        └── ...
```

These four phases each own an artifact, and the chain only works if each one is on disk:
`DESIGN.md` (planning) → `IMPLEMENTATION.md` (implementation planning, in plan mode) → `results/` (execution) → `reports/summary.md` (reporting). `experiments/INDEX.md` threads them together at the project level.

**Key conventions:**
- The design file is always named `DESIGN.md` at the **root of the experiment folder** (e.g., `experiments/exp_3/DESIGN.md`). The implementation plan, once approved, sits beside it as `IMPLEMENTATION.md`.
- `scripts/` holds run configs and training scripts that reference paths in `../../src/` and `../../data/`.
- `results/` holds raw outputs (metrics JSON, checkpoints). `reports/` holds polished summaries and figures.
- `experiments/INDEX.md` is the project's experiment registry **and** its self-documenting record of this layout — important because this skill is distributed standalone and the user's project won't carry external conventions docs. Create/update it at scaffold time (Step 0).
- If the project root or experiment folder doesn't exist yet, scaffold it (see Step 0 below).

---

## Core Workflow

### Step 0. Locate, Check, or Scaffold the Experiment Folder

Before writing the plan, figure out where it lives **and whether the project matches the layout this skill and the reporter depend on**. This check matters: the planner→reporter handoff only works because both skills look for files in the same places. A plan written into a structure that doesn't exist doesn't fail now — it resurfaces later as a confusing reporting failure when the reporter can't find `results/<condition>/`. Catching the mismatch here, with a question, is far cheaper.

Look at the project root for the expected markers — chiefly an `experiments/` directory (and, loosely, `src/` and `data/`). Three cases:

1. **Layout matches** (an `experiments/` dir is present and conforms): proceed silently — no need to narrate it. List `experiments/`, suggest the next available name (e.g. `exp_4` if `exp_1`–`exp_3` exist), and confirm the path.

2. **No project yet / empty directory**: ask for the project root and name, then scaffold the full structure (commands below).

3. **Project exists but doesn't match** (no `experiments/` dir, a flat repo, or results/code in differently-named folders like `outputs/` or `models/`): **don't silently write into it.** Warn the user and offer a choice, e.g.:
   > ⚠️ This project doesn't follow the experiment layout I expect (`experiments/exp_N/` with `DESIGN.md`, `results/<condition>/`, `reports/`). I can **create that structure alongside your existing files**, or **write the plan where you point me** and you manage the paths yourself. Which would you prefer?
   - **Scaffold** → create the standard tree *additively* (commands below). Only create new directories — never move, rename, or reorganize the user's existing files. If they actually want existing code relocated into the layout, that's a separate, explicitly-confirmed action, not something this skill does on its own (it's easy to break imports and hard to undo).
   - **Proceed as-is** → write `DESIGN.md` at the path they give and add a ⚠️ note in the plan that the layout is non-standard, so reporting may need paths pointed out explicitly.

4. **Always confirm** the experiment folder path with the user before creating files.

**Scaffold a new project:**
```bash
PROJECT=<project_name>
EXP=exp_1
mkdir -p $PROJECT/{docs,src,data,experiments/$EXP/{scripts,results,reports}}
```

**Add a new experiment to an existing project:**
```bash
PROJECT=<project_root>
EXP=exp_<n>   # next available number
mkdir -p $PROJECT/experiments/$EXP/{scripts,results,reports}
```

**Write the plan file** with the **Write tool**, not a bash heredoc. The plan is a long Markdown document containing its own code fences and tables; writing it through `cat << EOF` invites quoting and escaping breakage. Use `mkdir -p` (bash) to create folders, then `Write` to create `experiments/<exp_id>/DESIGN.md`.

**Create or update `experiments/INDEX.md`** (with the Write tool). If it doesn't exist, create it with a short header documenting the layout (so the project is self-describing — this skill ships without any external conventions file), then a registry table. If it exists, append a row for the new experiment. One row per experiment:

```markdown
# Experiments Index — <project_name>

Layout: each `exp_<n>/` holds `DESIGN.md` (research design) → `IMPLEMENTATION.md` (build plan)
→ `results/<condition>/` (runs) → `reports/summary.md` (write-up). See any `DESIGN.md` for detail.

| Exp | Title | Status | Hypothesis (1 line) | Verdict | Date |
|-----|-------|--------|---------------------|---------|------|
| [exp_1](exp_1/DESIGN.md) | Focal vs. CE on CheXpert | Draft | Focal loss improves macro-F1 ≥0.02 | — | 2026-05-23 |
```

The reporter updates the `Status` and `Verdict` of a row when it writes the report, so this stays the live campaign view.

**Backward compatibility.** An existing `INDEX.md` from an older project may link its rows to `PLAN.md` (e.g. `[exp_2](exp_2/PLAN.md)`) and carry a layout header that names `PLAN.md`. When you append a row, only add the new experiment's row — link it to `DESIGN.md`, since that's the file this skill now writes — and **leave the existing rows and their `PLAN.md` links untouched** (those files really are named `PLAN.md` on disk; rewriting the links would break them). Don't rewrite the header or migrate old rows. The result is a mixed index where legacy experiments point at `PLAN.md` and new ones point at `DESIGN.md`; the reporter handles both names.

---

### Step 1. Capture the Research Question

Before writing any plan, extract (from the conversation or by asking):

- **Hypothesis**: What specific claim is being tested? (e.g., "attention beats convolutions on this task")
- **Task & domain**: What ML task, dataset(s), modality?
- **Proposed method**: What is the new idea / intervention being evaluated?
- **Constraints**: Compute budget, time, available hardware, team size
- **Prior work**: What baselines already exist? Any published numbers to match?
- **Stakes**: Is this exploratory (sanity check) or high-stakes (paper submission)?

If the user gives a vague prompt like "I want to test my new loss function", ask 2–3 focused questions before writing the plan.

---

### Step 2. Pick the Tier First, Then the Structure

Before writing anything, decide how much plan the work actually warrants. A plan is a tool for the
researcher — its job is to make the experiment runnable and its result interpretable. A quick
sanity check answers a yes/no question in an afternoon; wrapping it in a file-layout diagram, a
baselines table, and a ten-item reproducibility checklist buries the one thing that matters and
signals a level of ceremony the work doesn't have. Match the plan to the stakes:

| Tier | When | Template to use |
|------|------|-----------------|
| **Lean** | Quick sanity check, "does X help at all", a single afternoon run | **Lean template** below (~4 short sections) |
| **Standard** | Ablation study, optimizer/method comparison, anything you'll act on | Full template, but drop sections that don't apply (e.g. no Ablations if there are none) |
| **Full** | Paper submission, large sweep, expensive benchmark | Full template, all sections, statistical testing |

When in doubt between two tiers, pick the smaller one — it's cheaper to add a section than to make
a reader wade through padding. The plan is written to `experiments/<exp_id>/DESIGN.md` — include the
experiment ID and project name in the header.

#### Lean template (sanity checks)

For a Lean-tier plan, **use exactly this skeleton — do not expand it into the full template.** No
file-layout diagram, no baselines table, no reproducibility checklist. A few sentences per section
is the right length.

```markdown
# Experiment Design: [Descriptive Title]
**Experiment**: experiments/<exp_id>/ · **Project**: <project_name> · **Date**: YYYY-MM-DD · **Status**: Draft

## Hypothesis
One falsifiable sentence. e.g. "Adding random-crop augmentation improves MNIST test accuracy."

## Setup
Dataset, model, the one thing that varies (baseline vs. the change), seeds. 3–5 bullets.

## Metric & Decision
Primary metric, and the threshold/comparison that decides yes/no. Record the git commit per run
(`git log -1 --format="%H %s" > results/<condition>/git_commit.txt`) so the result is traceable.

## Next Step
One line: accept this, then move to an implementation plan in plan mode.
```

#### Full template (standard / paper-grade)

This is the **maximal form**. For Standard-tier work, include the sections that apply and drop the
rest; for Full-tier, use all of them.

```markdown
# Experiment Design: [Descriptive Title]
**Experiment**: experiments/<exp_id>/  
**Project**: <project_name>  
**Date**: YYYY-MM-DD  
**Author**: <name or TBD>  
**Status**: Draft / In Progress / Complete

---

## 1. Hypothesis
A single falsifiable sentence. Example:
"Replacing cross-entropy with focal loss improves F1 on class-imbalanced splits by ≥2 points."

## 2. Experimental Setup
- **Dataset(s)**: name, version/hash, location (`../../data/<dataset>/`), split strategy, preprocessing
- **Model**: architecture, config file location (`scripts/<config>.yaml`)
- **Training**: optimizer, LR schedule, batch size, epochs/steps, seeds
- **Hardware**: GPU/TPU type, memory, estimated runtime per run

## 3. File Layout for This Experiment
```
experiments/<exp_id>/
├── DESIGN.md                  ← this file (experiment design only)
├── scripts/                 ← run scripts and configs (decided in the implementation plan)
├── results/
│   ├── <condition>/         ← metrics.json, checkpoints/
│   └── ...
└── reports/
    ├── figures/
    └── summary.md
```
Scripts and configs reference project-root-relative paths (e.g., `../../src/`, `../../data/`). Specific script names, configs, and code structure are decided in the **implementation plan**, not here.

## 4. Baselines
| Baseline | Config file | Expected metric range |
|----------|------------|----------------------|
| ...      | `scripts/configs/baseline.yaml` | ... |

## 5. Proposed Conditions
What varies across runs? Define each condition precisely, with its config file.

## 6. Ablation Studies
If applicable: list each ablation and what it isolates. Each ablation gets its own config.

## 7. Evaluation Protocol
- Primary metric(s) with thresholds for "success"
- Secondary metrics
- Statistical testing: number of seeds, confidence intervals, significance test if needed
- Results written to: `results/<condition>/metrics.json`
- Compute budget per run × number of runs = total cost estimate

## 8. Expected Results & Decision Rules
- If hypothesis holds → next steps
- If hypothesis fails → alternative explanations, follow-up runs
- Stopping criteria for expensive sweeps

## 9. Risks & Mitigations
List 2–4 specific risks (data leakage, unfair baselines, metric mismatch, etc.) with mitigations.

## 10. Reproducibility Checklist
- [ ] Random seeds fixed and logged
- [ ] Config YAML saved in `scripts/configs/`
- [ ] Dataset version / hash recorded in this file
- [ ] Model checkpoints saved to `results/<condition>/checkpoints/`
- [ ] Experiment tracker run linked (WandB / MLflow)
- [ ] Environment frozen (`../../docs/environment.yml` or `requirements.txt`)
- [ ] **Git commit hash recorded** — run `git log -1 --format="%H %s" > results/<condition>/git_commit.txt` before launching any run
- [ ] Working tree was clean at run time (no uncommitted changes) — verify with `git status`; commit or stash any changes first

## 11. Next Steps
1. Review and accept this experiment plan (hypothesis, conditions, metrics, decision rules).
2. Once accepted, produce an **implementation plan** (in Claude Code plan mode) covering the scripts, configs, and code changes needed to run the conditions in Sections 5–6. Do not begin editing any implementation files until that plan is approved.
```

---

### Step 3. Tier-Specific Emphasis

Within the tiers from Step 2, lean on the sections that carry the most weight for the work at hand:

- **Ablation study** (Standard): emphasize Baselines and Proposed Conditions — each ablation needs its own condition isolating one component.
- **Hyperparameter sweep** (Standard/Full): add the sweep strategy (grid / random / Bayesian) and the budget to the Evaluation Protocol.
- **Large-scale benchmark** (Full): include the compute-cost table and dataset provenance.
- **Paper experiment** (Full): statistical testing and the full reproducibility checklist are non-negotiable.

---

### Step 4. Evaluation Metrics — Quick Reference

Pick metrics appropriate to the task:

| Task | Primary metrics | Notes |
|------|----------------|-------|
| Classification | Accuracy, F1, AUROC | Use macro-F1 for class imbalance |
| Detection | mAP@50, mAP@50:95 | COCO-style |
| Segmentation | mIoU, Dice | |
| Generation (text) | Perplexity, BLEU, ROUGE, BERTScore | Human eval for final |
| Generation (image) | FID, IS, LPIPS | |
| Regression | MAE, RMSE, R² | |
| Ranking / Retrieval | MRR, NDCG, Recall@K | |
| RL | Episode return, sample efficiency | Report over N seeds |
| Efficiency | FLOPs, latency (ms), memory (GB), throughput | Always pair with quality |

---

### Step 5. Statistical Rigor Guidelines

- **Minimum seeds**: 3 for cheap experiments, 5+ for paper-quality claims
- **Report**: mean ± std (or 95% CI) across seeds, not just best run
- **Significance**: for small effect sizes, use paired t-test or Wilcoxon signed-rank
- **Avoid**: cherry-picking checkpoints, reporting val instead of test, tuning on test set

---

### Step 6. Compute Budget Estimation Helper

Prompt the user (or estimate) using:

```
total_cost = num_conditions × num_seeds × hours_per_run × GPU_cost_per_hour
```

Flag if total_cost > reasonable threshold and suggest:
- Reducing seeds for exploratory phase
- Using smaller proxy tasks first
- Early stopping / learning curve analysis

---

### Step 7. Git & Code Version Tracking

Every run must record the exact state of the codebase. Include the following instructions in the plan and in any generated run scripts.

**Before launching a run — mandatory checks:**
```bash
# 1. Ensure the working tree is clean (no uncommitted changes)
git status
# If dirty: commit your changes, or stash them: git stash

# 2. Record the commit hash into the results folder for this run
git log -1 --format="%H %s" > results/<condition>/git_commit.txt

# 3. Optionally tag the run for easy retrieval later
git tag exp_<n>_<condition>_run<seed>
```

**What to store in `results/<condition>/git_commit.txt`:**
```
<full 40-char SHA>  <commit message>
# Example:
a3f9c21d8e...  feat: switch loss to focal, adjust gamma=2.0
```

**If using an experiment tracker (WandB / MLflow):** log the commit hash as a run parameter:
```python
# WandB
import subprocess, wandb
commit = subprocess.check_output(["git", "log", "-1", "--format=%H"]).decode().strip()
wandb.config.update({"git_commit": commit})

# MLflow
import subprocess, mlflow
commit = subprocess.check_output(["git", "log", "-1", "--format=%H"]).decode().strip()
mlflow.log_param("git_commit", commit)
```

**Warn the user if:**
- `git status` shows uncommitted changes → ⚠️ results will not be reproducible from the recorded hash
- The repo has no commits yet → instruct them to initialise git and make an initial commit before running
- `src/` or `data/` preprocessing scripts are outside the repo → those must also be versioned or their hashes recorded separately

---

### Step 8. Common Pitfalls to Call Out

Always scan the user's proposed setup for:

- **Data leakage**: val/test statistics used in preprocessing
- **Unfair baselines**: baselines under-tuned vs. proposed method over-tuned
- **Metric mismatch**: optimizing one metric, reporting another
- **Missing ablations**: can't attribute gains to specific component
- **No reproducibility artifacts**: no seed, no config, no checkpoint, no commit hash recorded

If spotted, add a ⚠️ warning inline in the plan.

---

### Step 9. Output & File Writing

1. Generate the plan content at the depth the stakes call for (Step 2 / Step 3). Set the header **Status: Draft**.
2. Scaffold the experiment folder if it doesn't exist (see Step 0).
3. Write the plan to `experiments/<exp_id>/DESIGN.md` with the **Write tool**.
4. Create or update `experiments/INDEX.md` with a row for this experiment (see Step 0).
5. Confirm to the user: "Plan written to `experiments/<exp_id>/DESIGN.md`; indexed in `experiments/INDEX.md`."
6. Show a short summary in chat (hypothesis + next steps only — the full plan is in the file), then point to the implementation-planning handoff in Step 10.

**Formatting rules:**
- Markdown with clear headers matching the template
- Tables for baselines and conditions
- Bold key thresholds and decisions
- ⚠️ warnings for any detected pitfalls
- Keep it concise — a 2-week experiment shouldn't need a 10-page plan

---

### Step 10. Handoff to Implementation Planning

**Once the plan is accepted**, raise a few general operational suggestions before any code is written — these are decisions the plan assumes but doesn't lock down, and surfacing them now saves a re-run later. Phrase them as questions, not mandates, and skip any that the plan or conversation has already settled (don't ask about a tracker if the user already named one). For a Lean-tier sanity check, keep this light — one or two questions at most. Typical prompts:

- **Experiment tracking**: _"Do you want to log runs to an experiment tracker such as Weights & Biases or MLflow? If so, I'll have the implementation plan wire it in and record the git commit as a run parameter."_
- **Compute & scheduling**: _"Will these run locally, on a shared cluster, or via a job scheduler (e.g. Slurm)? That affects how the run scripts are structured."_
- **Result storage**: _"Are checkpoints and metrics staying under `results/<condition>/`, or do large artifacts need separate/remote storage?"_
- **Environment**: _"Should the implementation plan pin the environment (e.g. `requirements.txt` / `environment.yml`) so the runs are reproducible from the recorded commit?"_

Then point them to the next step: _"When you're ready to code this up, enter plan mode and ask for an implementation plan covering the scripts, configs, and code changes. **Once you approve that plan, save it as `experiments/<exp_id>/IMPLEMENTATION.md` (next to DESIGN.md) before editing files** — the reporter relies on it to map conditions to configs and to spot where the build diverged from the design."_ That implementation plan is a separate artifact (it covers `scripts/`, `../../src/` utilities, config layout, and data-pipeline steps) — it is not written into `DESIGN.md`, and this skill does not produce it. The only files this skill writes are `DESIGN.md` and the `experiments/INDEX.md` row.

**Status lifecycle.** The `Status` field tracks which phase the experiment is in, so anyone opening `DESIGN.md` or `INDEX.md` knows where it stands. The owners:
- This skill writes **Draft** when it creates the plan.
- Tell the user to flip it to **In Progress** (in both `DESIGN.md` and the `INDEX.md` row) once runs are launched.
- The reporter sets the terminal state (**Complete / Partial / Failed**) and the verdict when it writes `summary.md`.

---

## Example Invocations

- "I want to test whether data augmentation helps my image classifier" → exploratory plan, 1 dataset, 2–3 augmentation conditions
- "Design an ablation study for my new attention mechanism" → full ablation plan isolating each component
- "How should I benchmark my new optimizer against Adam?" → fair comparison plan with matched budgets and multiple tasks
- "I'm submitting to NeurIPS, help me plan my experiments" → high-stakes plan with statistical testing and reproducibility checklist
