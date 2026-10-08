# Experiment Design: Lion vs. Adam on CIFAR-100
**Experiment**: experiments/exp_1/  
**Project**: optimizer-bench  
**Date**: 2026-08-10  
**Tier**: Standard  
**Status**: In Progress

## Hypothesis
Lion reaches higher CIFAR-100 test accuracy than Adam at an equal tuning budget, by ≥0.5 points.

## Conditions
| id | Role | What differs from the baseline | What it isolates | Expected test accuracy |
|----|------|-------------------------------|------------------|------------------------|
| adam | baseline | — | reference point | ~76 |
| lion | proposed | Lion optimizer | the hypothesis | ≥ baseline + 0.5 |

## Evaluation Protocol
- **Primary metric**: test accuracy (%), key `test_acc`
- **Seeds**: 5 per condition (0–4), the same for every condition
- **Statistical analysis**: paired difference lion − adam with a 95% CI

## Decision Rules
- **Supported if** the mean paired difference is ≥ 0.5 and its 95% CI excludes 0
- **Refuted if** the mean paired difference is ≤ 0
- **Inconclusive if** anything else
