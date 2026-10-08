# Experiments Index — chexpert-imbalance

Each `exp_<n>/` folder holds:
- `DESIGN.md` — what is tested and how it will be judged
- `IMPLEMENTATION.md` — how it is built and run, plus a deviations log
- `results/<condition_id>/seed_<s>/` — one directory per run, with `metrics.json` and `git_commit.txt`
- `reports/summary.md` — the write-up

**Status** is how far execution got: Draft → In Progress → Complete / Partial / Failed.
**Verdict** is what the results say about the hypothesis: ✅ supported, ❌ refuted, ⚠️ inconclusive.

| Exp | Title | Status | Hypothesis (1 line) | Verdict | Date |
|-----|-------|--------|---------------------|---------|------|
| [exp_1](exp_1/DESIGN.md) | Focal vs. CE on CheXpert | In Progress | Focal loss improves macro-F1 by ≥0.02 | — | 2026-09-01 |
