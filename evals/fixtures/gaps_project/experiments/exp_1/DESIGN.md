# Experiment Design: Focal Loss vs. Cross-Entropy on CheXpert
**Experiment**: experiments/exp_1/  
**Project**: chexpert-imbalance  
**Date**: 2026-09-01  
**Author**: TBD  
**Tier**: Standard  
**Status**: In Progress

## Hypothesis
Replacing cross-entropy with focal loss (γ=2) improves test macro-F1 on the imbalanced CheXpert split by ≥0.02.

## Setup
- **Dataset(s)**: CheXpert-small v1.0, official train/valid split, 10% of train held out as test
- **Model**: DenseNet-121, ImageNet-pretrained
- **Training**: Adam, learning rate 1e-3 for every condition, batch size 64, 10 epochs
- **Tuning budget**: none; all conditions use the same fixed hyperparameters

## Conditions
| id | Role | What differs from the baseline | What it isolates | Expected test macro-F1 |
|----|------|-------------------------------|------------------|------------------------|
| baseline_ce | baseline | — | reference point | 0.80–0.82 |
| focal_g2 | proposed | focal loss, γ=2, with class reweighting | the hypothesis | ≥ baseline + 0.02 |
| focal_g2_no_reweight | ablation | focal loss, γ=2, no class reweighting | whether the gain comes from the loss or the reweighting | — |

## Evaluation Protocol
- **Primary metric**: test macro-F1, key `test_f1_macro`, computed on the held-out test split
- **Secondary metrics**: test AUROC (`test_auroc`)
- **Seeds**: 3 per condition (0, 1, 2), the same for every condition
- **Checkpoint selection**: best validation macro-F1, evaluated on test once
- **Statistical analysis**: paired difference focal_g2 − baseline_ce over the three seeds, with a 95% CI

## Decision Rules
- **Supported if** the mean paired difference is ≥ 0.02 and its 95% CI excludes 0
- **Refuted if** the mean paired difference is ≤ 0
- **Inconclusive if** anything else, or if fewer than 3 paired seeds are available
- **Then what**: if supported, run the γ sweep; if refuted, drop focal loss

## Compute Budget
3 conditions × 3 seeds = 9 runs × 2.5 h = 22.5 GPU-hours (budget: 40).

## Risks & Mitigations
- Class reweighting confounds the loss change → the `focal_g2_no_reweight` ablation separates them.

## Reproducibility Requirements
- Seeds fixed and written to `metrics.json`
- Code version recorded per run in `git_commit.txt`, launched from a committed tree
- One saved config per condition
