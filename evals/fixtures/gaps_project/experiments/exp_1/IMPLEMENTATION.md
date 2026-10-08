# Implementation Plan: Focal Loss vs. Cross-Entropy on CheXpert
**Experiment**: experiments/exp_1/  
**Design**: [DESIGN.md](DESIGN.md)  
**Date**: 2026-09-01

## Run Matrix
| Condition id | Config | Command | Seeds | Writes to |
|--------------|--------|---------|-------|-----------|
| baseline_ce | `scripts/configs/baseline_ce.yaml` | `python scripts/train.py --config scripts/configs/baseline_ce.yaml --seed $SEED` | 0 1 2 | `results/baseline_ce/seed_$SEED/` |
| focal_g2 | `scripts/configs/focal_g2.yaml` | `python scripts/train.py --config scripts/configs/focal_g2.yaml --seed $SEED` | 0 1 2 | `results/focal_g2/seed_$SEED/` |
| focal_g2_no_reweight | `scripts/configs/focal_g2_no_reweight.yaml` | `python scripts/train.py --config scripts/configs/focal_g2_no_reweight.yaml --seed $SEED` | 0 1 2 | `results/focal_g2_no_reweight/seed_$SEED/` |

## What Every Run Records
Each run writes `metrics.json` (`seed`, `test_f1_macro`, `test_auroc`, `epochs_completed`, `train_time_hours`) and `git_commit.txt` into its run directory.

## Deviations Log
| Date | What changed | Why | Conditions affected |
|------|--------------|-----|---------------------|
| 2026-09-04 | Batch size 64 → 32 | Out-of-memory on the shared GPU | focal_g2 |
