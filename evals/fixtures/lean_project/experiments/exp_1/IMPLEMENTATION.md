# Implementation Plan: Random-Crop Augmentation Sanity Check
**Experiment**: experiments/exp_1/ · **Design**: [DESIGN.md](DESIGN.md) · **Date**: 2026-09-20

## Run Matrix
| Condition id | Command | Seeds | Writes to |
|--------------|---------|-------|-----------|
| baseline | `python ../../src/train.py --out results/baseline/seed_$SEED --seed $SEED` | 0 | `results/baseline/seed_$SEED/` |
| random_crop | `python ../../src/train.py --out results/random_crop/seed_$SEED --seed $SEED --augment random_crop` | 0 | `results/random_crop/seed_$SEED/` |

No code changes: `src/train.py` already supports `--augment random_crop`.

## What Every Run Records
`metrics.json` with `seed` and `test_acc`, and `git_commit.txt`.

## Deviations Log
| Date | What changed | Why | Conditions affected |
|------|--------------|-----|---------------------|
| — | None so far | | |
