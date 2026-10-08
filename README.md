# ML Experiment Skills for Claude Code

A collection of [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) that help ML researchers plan, run, and document experiments in a structured, reproducible way.

## Skills

### `ml-experiment-planner`

Plans a machine learning experiment and writes two documents to `experiments/exp_<n>/`.

**Triggers on:** "experiment plan", "design an experiment", "ablation study", "how should I test", "benchmark X against Y", "compare these approaches", etc.

**Produces:**
- `DESIGN.md` — the research design: a falsifiable hypothesis, conditions (each with an id), metrics, and a decision rule fixed before any data exists
- `IMPLEMENTATION.md` — the build plan: a run matrix mapping each condition id to its config and command, the code changes needed, what every run must record, and a deviations log to fill in during execution
- A row in `experiments/INDEX.md` (the experiment registry)

Both are sized to the stakes: a **Lean** tier for an afternoon sanity check, **Standard** for anything you will act on, **Full** for paper-grade work.

**Does not:** write scripts or configs, or launch runs. You review both documents first; building the experiment follows your approval.

---

### `ml-experiment-reporter`

Reconciles what was designed, what was built, and what the runs produced, then writes `experiments/exp_<n>/reports/summary.md` — grounded strictly in evidence.

**Triggers on:** "write a report", "summarise my results", "write up exp_3", "my runs finished", "what did my experiment show", etc.

**Produces:**
- A report cross-referencing `DESIGN.md`, `IMPLEMENTATION.md`, and `results/`, sized to the design's tier
- `reports/inventory.json` — a machine-readable inventory of `results/` (per-seed values, means, paired comparisons, recorded commits) produced by a bundled script, so every number in the report has a source
- Separate callouts for coverage gaps (planned but not run), build deviations (run, but not as designed), and provenance gaps (missing, dirty, or mismatched commits)
- The final `Status` and `Verdict`, written to `DESIGN.md` and `INDEX.md`

**Does not:** infer missing metrics from logs, silently skip planned conditions, compute statistics without per-seed values, or describe figures that don't exist.

---

## Workflow

Each phase leaves files on disk; the next phase finds them by path.

```
planning                      execution                  reporting
ml-experiment-planner         (you, or Claude, build     ml-experiment-reporter
writes DESIGN.md           →   and run it)            →  writes reports/summary.md
     + IMPLEMENTATION.md       produces results/           + reports/inventory.json
     + INDEX.md row            logs deviations in          + sets Status and Verdict in
                               IMPLEMENTATION.md             DESIGN.md and INDEX.md
```

### Expected project layout

Both skills assume the following directory structure inside your ML project:

```
<YourProject>/
├── docs/  src/  data/
└── experiments/
    ├── INDEX.md                        ← registry, one row per experiment
    └── exp_<n>/
        ├── DESIGN.md                   ← what is tested and how it will be judged
        ├── IMPLEMENTATION.md           ← how it is built and run; deviations log
        ├── scripts/                    ← run scripts; configs in scripts/configs/
        ├── results/
        │   └── <condition_id>/         ← directory name = a condition id from DESIGN.md
        │       └── seed_<s>/           ← one directory per run
        │           ├── metrics.json    ← that run's final metrics
        │           ├── git_commit.txt  ← code version the run was launched from
        │           └── checkpoints/
        └── reports/
            ├── inventory.json
            ├── figures/
            └── summary.md
```

The planner scaffolds this structure if it doesn't exist yet, and writes a short description of it into `experiments/INDEX.md` so the project documents itself.

**Status** records how far execution got (Draft → In Progress → Complete / Partial / Failed). **Verdict** records what the results say about the hypothesis (✅ supported, ❌ refuted, ⚠️ inconclusive). They are independent: a hypothesis cleanly refuted by a full set of runs is Complete + ❌.

---

## Installation

Clone this repository, then copy the skill folders to a Claude Code skills directory.

```bash
git clone https://github.com/fagonzalezo/ml-experiment-skills.git
```

### Option A — User-level (available in all your projects)

```bash
mkdir -p ~/.claude/skills
cp -r ml-experiment-skills/skills/ml-experiment-planner ~/.claude/skills/
cp -r ml-experiment-skills/skills/ml-experiment-reporter ~/.claude/skills/
```

### Option B — Project-level (available only in one project)

Run this from your ML project root:

```bash
mkdir -p .claude/skills
cp -r /path/to/ml-experiment-skills/skills/ml-experiment-planner .claude/skills/
cp -r /path/to/ml-experiment-skills/skills/ml-experiment-reporter .claude/skills/
```

After copying, restart Claude Code (or start a new session) so it picks up the new skills. The reporter's inventory script needs Python 3.8+ and nothing beyond the standard library.

### Verify installation

Open Claude Code in your project and type:

```
/ml-experiment-planner
```

If the skill loads, it will start by asking about your experiment.

---

## Usage

### Plan a new experiment

```
I want to test whether focal loss improves F1 on my imbalanced dataset.
```

The planner asks one batch of clarifying questions if it needs them, picks a tier, looks at your existing code, and writes `experiments/exp_<n>/DESIGN.md` and `IMPLEMENTATION.md`. Review both before any code is written.

### Build and run it

Follow `IMPLEMENTATION.md` — yourself, or by asking Claude to implement it. Each run writes its own directory, and the run script records the commit at launch:

```bash
RUN_DIR=experiments/exp_<n>/results/<condition_id>/seed_<s>
git log -1 --format="%H %s" > "$RUN_DIR/git_commit.txt"
git diff --quiet HEAD || echo "DIRTY: uncommitted changes at launch" >> "$RUN_DIR/git_commit.txt"
```

When something departs from the plan — a changed hyperparameter, a dropped seed — add a row to the Deviations Log in `IMPLEMENTATION.md`.

### Report results

```
Write a report for exp_3.
```

The reporter reads `DESIGN.md` and `IMPLEMENTATION.md`, inventories `results/`, and writes `reports/summary.md`. It works on partial and failed experiments too; what is missing is listed rather than filled in.

---

## Repository structure

```
skills/
├── ml-experiment-planner/
│   └── SKILL.md
└── ml-experiment-reporter/
    ├── SKILL.md
    └── scripts/collect_results.py     ← results inventory and statistics (stdlib only)
evals/
├── evals.json                         ← test prompts and what each should produce
└── fixtures/                          ← small fake projects the prompts run against
tools/
└── check_contract.py                  ← checks the two skills agree on the layout
```

The `description:` frontmatter field of each `SKILL.md` is what Claude Code matches against your messages to decide whether to invoke the skill.

### Contributing

The two skills share a layout contract, and each `SKILL.md` carries its own copy between `<!-- contract:start -->` and `<!-- contract:end -->` (they are installed separately, so neither can point at a shared file). After editing either one:

```bash
python tools/check_contract.py          # fails if the two copies differ
python tools/check_contract.py --sync   # copy the planner's block into the reporter
```

`evals/evals.json` lists realistic prompts with checkable expectations. Run each against a fresh copy of its fixture project to see whether a change to a skill helped or hurt.
