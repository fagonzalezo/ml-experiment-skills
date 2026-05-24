---
name: ml-experiment-reporter
description: >
  Writes a structured report on ML experiment results, grounded in the experiment's DESIGN.md
  and the actual results files. Use this skill whenever a user wants to document, summarise,
  or communicate the outcome of a machine learning experiment — including phrases like "write
  a report", "summarise my results", "document what happened", "write up the experiment",
  "generate a summary of exp_N", "what did my experiment show", or "I finished running my
  experiment". Always use this skill when the user has completed (or partially completed)
  an experiment and wants a written record of findings. The report is written to
  experiments/exp_N/reports/summary.md. Do NOT use for planning new experiments
  (use ml-experiment-planner instead) or for pure data analysis without a write-up goal.
---

# ML Experiment Reporter

Reads the experiment plan and results, then writes a coherent `summary.md` report that
documents what was done, what was found, and what it means — grounded strictly in evidence.

---

## Project Structure (reminder)

```
<Project>/
├── docs/
├── src/
├── data/
└── experiments/
    ├── INDEX.md                         ← update: set this exp's Status + Verdict row
    └── exp_<n>/
        ├── DESIGN.md                      ← input: read this first (the research design)
        ├── IMPLEMENTATION.md            ← input: how it was built (condition→config map, deviations)
        ├── scripts/configs/             ← input: read relevant configs
        ├── results/
        │   └── <condition>/
        │       ├── metrics.json         ← input: primary results
        │       ├── git_commit.txt       ← input: code version
        │       └── checkpoints/
        └── reports/
            ├── figures/                 ← input: any plots already generated
            └── summary.md              ← OUTPUT: written here
```

The four experiment phases each leave an artifact — `DESIGN.md` (design) → `IMPLEMENTATION.md` (build) → `results/` (execution) → `summary.md` (this report). `DESIGN.md` says what was *intended*; `IMPLEMENTATION.md` says what was *built*; `results/` shows what *happened*. A faithful report reconciles all three.

---

## Core Workflow

### Step 0. Locate Inputs

1. Ask the user for the experiment folder path if not already provided (e.g., `myproject/experiments/exp_3`).
2. Read `DESIGN.md` from the experiment root — the ground truth for what was *intended*.
3. Read `IMPLEMENTATION.md` from the experiment root if present — the record of what was *built* (which config/script produced each condition, and any decisions that departed from the design). This is what lets §3 report build-level deviations rather than only "did this condition run." If it's absent, note that under caveats (§8) — the build can then only be inferred from configs and git.
4. Scan `results/` to discover which conditions were actually run:
   ```bash
   ls experiments/<exp_id>/results/
   # For each condition:
   cat experiments/<exp_id>/results/<condition>/metrics.json
   cat experiments/<exp_id>/results/<condition>/git_commit.txt
   ```
5. List any figures already in `reports/figures/`.
6. Read relevant configs from `scripts/configs/` if metric context is unclear.
7. Optionally read `experiments/INDEX.md` to find related experiments to reference in §9.

Before reading, sanity-check that the folder actually looks like a skill-managed experiment — it should contain a `DESIGN.md` (or a legacy `PLAN.md` — see below) and/or a `results/` directory. If it matches, proceed silently. If it clearly doesn't (no `results/` *and* no `DESIGN.md`/`PLAN.md`, or a flat project with metrics scattered elsewhere), don't guess and don't fabricate a report from a structure you can't locate. Tell the user:
> ⚠️ This folder doesn't match the layout I expect (`DESIGN.md` + `results/<condition>/`). Point me to where the plan and per-condition results actually live, or run the ml-experiment-planner skill first to set up the structure.

Then work only from the paths they give back.

**Backward compatibility.** Older experiments (created before this skill renamed the plan file) keep the research design in `PLAN.md` rather than `DESIGN.md`. If you find a `PLAN.md` at the experiment root and no `DESIGN.md`, treat that `PLAN.md` as the design file — read it as the ground truth, apply every `DESIGN.md §N` cross-reference below to it, and write the status update back into it. Don't rename the file or warn about its name; only fall through to the "missing" warning below when *neither* `DESIGN.md` nor `PLAN.md` exists.

If neither `DESIGN.md` nor a legacy `PLAN.md` is present but `results/` exists, warn the user:
> ⚠️ No DESIGN.md found. The report cannot be cross-referenced against a plan. Proceeding with results only — consider creating a plan retroactively with the ml-experiment-planner skill.

---

### Step 1. Reconcile Plan vs. Reality

Before writing, build a mental diff between what was planned and what was run:

| Check | How |
|-------|-----|
| All planned conditions run? | Compare DESIGN.md §5 conditions vs. `results/` subdirs |
| All planned baselines run? | Compare DESIGN.md §4 baselines vs. `results/` subdirs |
| All planned ablations run? | Compare DESIGN.md §6 vs. `results/` subdirs |
| Built as designed? | Compare `IMPLEMENTATION.md` (configs/scripts per condition) vs. DESIGN.md intent |
| Primary metric present? | Check `metrics.json` keys vs. DESIGN.md §7 |
| Expected seed count met? | Count seed entries per condition |
| Git commit recorded? | Check `git_commit.txt` exists per condition |

Flag any gap as a **"Missing Data"** note in the report — never silently skip a planned condition. There are two distinct kinds of divergence to keep separate: a *coverage* gap (a planned condition wasn't run) and a *build* deviation (a condition was run, but `IMPLEMENTATION.md` shows it was built differently than the design called for). The first goes in §8 Missing Data; the second goes in §3 Deviations.

---

### Step 2. Parse Metrics

Extract results from each `metrics.json`. Expected shape (flexible — adapt to what's present):

```json
{
  "seed": 42,
  "epoch": 50,
  "val_loss": 0.312,
  "test_f1_macro": 0.821,
  "test_auroc": 0.934,
  "train_time_hours": 2.7
}
```

Aggregate across seeds:
```python
import json, pathlib, statistics

conditions = {}
for p in pathlib.Path("results").iterdir():
    files = list(p.glob("metrics.json"))  # or metrics_seed*.json
    vals = [json.load(open(f)) for f in files]
    primary = [v["<primary_metric>"] for v in vals]
    conditions[p.name] = {
        "mean": statistics.mean(primary),
        "stdev": statistics.stdev(primary) if len(primary) > 1 else None,
        "n": len(primary)
    }
```

If metrics files use a different structure (e.g., CSV, YAML, per-epoch logs), adapt accordingly — read what's there.

---

### Step 3. Report Structure

Write to `experiments/<exp_id>/reports/summary.md` using this template:

```markdown
# Experiment Report: [Title from DESIGN.md]
**Experiment**: experiments/<exp_id>/  
**Project**: <project_name>  
**Report date**: YYYY-MM-DD  
**Plan date**: <date from DESIGN.md>  
**Author**: <name or TBD>  
**Status**: Complete / Partial / Failed

---

## 1. Summary
2–4 sentences. State the hypothesis, whether it was supported, and the key finding.
Write this for someone who won't read the rest of the report.

---

## 2. Hypothesis & Verdict
**Hypothesis (from plan):** _copy exact hypothesis sentence from DESIGN.md_

**Verdict:** ✅ Supported / ❌ Refuted / ⚠️ Inconclusive

**Evidence:** 1–2 sentences citing the primary metric delta and whether it crossed the
success threshold defined in the plan.

---

## 3. Experimental Setup (as run)
Describe what was actually built and run, drawing on `IMPLEMENTATION.md` and the configs. Note any deviation between the design (`DESIGN.md`) and the build (`IMPLEMENTATION.md` / configs). If nothing changed, write "As described in DESIGN.md." If there is no `IMPLEMENTATION.md`, say so — deviations can then only be inferred from configs and git, not confirmed.

- **Dataset**: <name, version, split>
- **Model**: <architecture, config>
- **Training**: <optimizer, LR, batch size, epochs actually run>
- **Hardware**: <GPU, actual runtime>
- **Deviations from plan**: <list any, or "None">

---

## 4. Code Version
| Condition | Git commit | Commit message |
|-----------|-----------|----------------|
| baseline  | `a3f9c21` | feat: initial baseline |
| proposed  | `d84e012` | feat: switch to focal loss |

⚠️ Flag any condition where `git_commit.txt` is missing.

---

## 5. Results

### 5.1 Primary Metric
| Condition | Mean ± Std | N seeds | vs. best baseline (Δ) |
|-----------|-----------|---------|----------------------|
| baseline_ce | 0.812 ± 0.008 | 5 | — |
| proposed_focal | 0.834 ± 0.006 | 5 | **+0.022** ✅ |

> Success threshold from plan: Δ ≥ 0.02. _Threshold [met / not met]._

### 5.2 Secondary Metrics
Table or prose for secondary metrics defined in DESIGN.md §7.

### 5.3 Ablation Results (if applicable)
| Ablation | Primary metric | Δ vs. full model | Interpretation |
|----------|---------------|-----------------|----------------|
| w/o projection head | 0.819 ± 0.010 | −0.015 | head contributes ~1.5 F1 pts |

### 5.4 Learning Curves (if figures available)
Reference figures: `reports/figures/<name>.png`  
Briefly describe what the curves show (convergence, overfitting, instability).

---

## 6. Statistical Analysis
- **Test used**: paired t-test / Wilcoxon signed-rank / none (state why)
- **p-value**: <value> (threshold: 0.05)
- **Confidence interval**: [low, high] at 95%
- **Conclusion**: result is / is not statistically significant

If N seeds < 3: ⚠️ note that statistical testing is unreliable.

A significance test needs the **per-seed values**, not just an aggregate. If the results files
only store a pre-computed mean ± std (no individual seed entries to recover), say so plainly —
"Per-seed values not available; cannot compute a significance test from aggregate stats alone" —
and do not invent a p-value or CI. This is the same evidence-grounded rule as everywhere else:
report what the files support, flag what they don't.

---

## 7. Comparison to Expected Results
Refer back to DESIGN.md §8 (Expected Results & Decision Rules).

| Expected | Observed | Match? |
|----------|----------|--------|
| Focal loss ≥ +2 F1 pts | +2.2 F1 pts | ✅ |
| No regression on AUROC | AUROC −0.003 | ✅ within noise |

---

## 8. Missing Data & Caveats
List every planned condition, ablation, or metric that was NOT completed, and why (if known).
If everything completed: "All planned runs completed."

---

## 9. Conclusions & Next Steps
- **What this experiment established** (1–2 bullets)
- **What remains uncertain** (1–2 bullets)
- **Recommended follow-up experiments** (reference existing experiment IDs from `INDEX.md` where relevant, or describe new ones). Each new experiment closes the loop back to planning: _"To set up `exp_<n+1>`, use the ml-experiment-planner skill."_

---

## 10. Reproducibility Record
| Item | Status |
|------|--------|
| Seeds logged | ✅ / ❌ |
| Configs versioned | ✅ / ❌ |
| Git commits recorded | ✅ / ❌ (see §4) |
| Checkpoints saved | ✅ / ❌ |
| Environment frozen | ✅ / ❌ |
| Experiment tracker linked | ✅ / ❌ (run URL if available) |
```

---

### Step 4. Writing Guidelines

**Tone and style:**
- Write for a technically literate reader who has not read the plan
- Be precise: always cite specific numbers, not vague qualitative claims
- Never claim success or failure beyond what the numbers support
- Use ✅ / ❌ / ⚠️ consistently for verdicts and status items

**On deviations from the plan:**
- Any deviation (different hyperparameters, fewer seeds, different dataset split) must be called out explicitly in §3 — never silently normalised
- If a deviation is significant, add a ⚠️ in the summary (§1)

**On missing results:**
- If a condition is missing, write `_Not run_` in the table — never omit the row
- If the primary metric is absent from results files, say so explicitly — do not infer it from logs or secondary metrics without flagging

**On figures:**
- Reference existing figures in `reports/figures/` by relative path
- Do not generate or describe figures that don't exist
- If useful figures are missing, add a "Suggested figures" note at the end of §5

---

### Step 5. File Writing

Write the report to `experiments/<exp_id>/reports/summary.md` with the **Write tool**, not a bash heredoc — the report is a long Markdown document with its own code fences and tables, which `cat << EOF` tends to mangle.

After writing the report, close out the experiment's lifecycle bookkeeping — this is the terminal state the planner's status lifecycle hands off to the reporter:
1. Confirm to the user: "Report written to `experiments/<exp_id>/reports/summary.md`."
2. **Update `DESIGN.md`'s `Status`** field to match the report (Complete / Partial / Failed) with an `Edit`. This is the one edit the reporter makes outside `reports/` — a single-field bookkeeping change so the plan reflects reality; do not rewrite any other part of `DESIGN.md`. (For a legacy experiment whose design lives in `PLAN.md`, edit the `Status` field there instead — same single-field change, in whichever file holds the design.)
3. **Update the experiment's row in `experiments/INDEX.md`** with the same Status and the verdict (✅ / ❌ / ⚠️), so the campaign view stays current. If `INDEX.md` doesn't exist, skip this (an older project may predate the convention).
4. Show the §1 Summary and §9 Conclusions in chat — the user should not need to open the file to get the key takeaways.

---

## Example Invocations

- "Write a report for exp_3" → read DESIGN.md + results/, write full summary.md
- "Summarise what happened in my contrastive loss experiment" → locate exp folder, write report
- "My experiment finished, document the results" → ask for exp path, then full report
- "Write up exp_2, we didn't finish all the ablations" → full report with §8 missing data noted
- "Generate a report, the results are in experiments/chexpert/exp_4" → use provided path directly
