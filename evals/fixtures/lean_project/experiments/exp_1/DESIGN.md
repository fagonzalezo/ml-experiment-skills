# Experiment Design: Random-Crop Augmentation Sanity Check
**Experiment**: experiments/exp_1/ · **Project**: mnist-aug · **Date**: 2026-09-20 · **Tier**: Lean · **Status**: In Progress

## Hypothesis
Random-crop augmentation improves MNIST test accuracy.

## Setup
- MNIST, standard train/test split
- Small CNN from `src/train.py`, 5 epochs
- The only thing that varies is the augmentation

## Conditions
| id | Role | What it is |
|----|------|------------|
| baseline | baseline | no augmentation |
| random_crop | proposed | baseline + random-crop augmentation |

Seeds: 0, the same for every condition.

## Metric & Decision
Primary metric: test accuracy (`test_acc`). Supported if random_crop beats baseline by ≥ 0.2 points; refuted if it is lower; anything else is inconclusive.
