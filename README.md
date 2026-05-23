# ML Experiment Skills for Claude Code

A collection of [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) that help ML researchers plan, run, and document experiments in a structured, reproducible way.

## Skills

### `ml-experiment-planner`

Generates a structured research-design plan for a machine learning experiment and writes it to disk as `experiments/exp_<n>/PLAN.md`.

**Triggers on:** "experiment plan", "design an experiment", "ablation study", "how should I test", "benchmark this", "compare these approaches", etc.

**Produces:**
- A falsifiable hypothesis
- Experimental conditions and baselines
- Evaluation metrics and decision rules
- Reproducibility checklist (seeds, configs, git-commit tracking)
- An entry in `experiments/INDEX.md` (the experiment registry)

**Does not produce:** implementation plans, function signatures, or file-by-file edit lists. Implementation planning is a separate follow-up step, run in Claude Code plan mode.

---

### `ml-experiment-reporter`

Reads the experiment plan and result files, then writes a coherent `experiments/exp_<n>/reports/summary.md` that documents what was done, what was found, and what it means — grounded strictly in evidence.

**Triggers on:** "write a report", "summarise my results", "document what happened", "I finished running my experiment", "generate a summary of exp_N", etc.

**Produces:**
- A structured report cross-referencing `PLAN.md`, `IMPLEMENTATION.md`, and `results/`
- Explicit callouts for missing data, build deviations, and reproducibility gaps
- Updated `Status` and `Verdict` in `PLAN.md` and `INDEX.md`

**Does not:** infer missing metrics from logs, silently skip planned conditions, or invent figures.

---

## Workflow

The two skills form a four-phase pipeline. Each phase leaves a file on disk; the chain only works if each artifact is present.

```
planning                 implementation           execution        reporting
ml-experiment-planner    (Claude plan mode)       (you run it)     ml-experiment-reporter
writes PLAN.md        →  saves                 →  produces      →  writes reports/summary.md
+ INDEX.md row           IMPLEMENTATION.md        results/         + updates PLAN.md Status
                                                                   + updates INDEX.md row
```

### Expected project layout

Both skills assume the following directory structure inside your ML project:

```
<YourProject>/
├── docs/
├── src/
├── data/
└── experiments/
    ├── INDEX.md                         ← experiment registry (planner creates, reporter updates)
    └── exp_<n>/
        ├── PLAN.md                      ← research-design plan (planner writes)
        ├── IMPLEMENTATION.md            ← implementation plan (you save after plan-mode approval)
        ├── scripts/configs/             ← run scripts and config files
        ├── results/
        │   └── <condition>/
        │       ├── metrics.json
        │       └── git_commit.txt       ← mandatory: record the git commit before each run
        └── reports/
            ├── figures/
            └── summary.md              ← experiment report (reporter writes)
```

The planner will scaffold this structure for you if it doesn't exist yet.

---

## Installation

Clone this repository, then copy the skill folders to a Claude Code skills directory.

```bash
git clone https://github.com/<your-org>/ml-experiment-skills.git
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

After copying, restart Claude Code (or start a new session) so it picks up the new skills.

### Verify installation

Open Claude Code in your project and type:

```
/ml-experiment-planner
```

If the skill loads, you'll see it start asking about your experiment hypothesis.

---

## Usage

### Plan a new experiment

```
I want to test whether focal loss improves F1 on my imbalanced dataset.
```

The planner picks up the intent, asks clarifying questions if needed, chooses an appropriate plan tier (lean sanity check vs. full paper-grade), and writes `experiments/exp_<n>/PLAN.md`.

### Create an implementation plan

After accepting the experiment plan, enter Claude Code plan mode and ask for an implementation plan covering the scripts and configs. Save the approved plan as `experiments/exp_<n>/IMPLEMENTATION.md` before touching any files.

### Run your experiment

Follow the implementation plan. Before each run, record the git commit:

```bash
git log -1 --format="%H %s" > experiments/exp_<n>/results/<condition>/git_commit.txt
```

### Report results

```
Write a report for exp_3.
```

The reporter reads `PLAN.md`, `IMPLEMENTATION.md`, `results/`, and any figures in `reports/figures/`, then writes `reports/summary.md` and updates the status fields in `PLAN.md` and `INDEX.md`.

---

## Skill file structure

Each skill is a single `SKILL.md` file with YAML frontmatter and markdown instructions:

```
skills/
├── ml-experiment-planner/
│   └── SKILL.md
└── ml-experiment-reporter/
    └── SKILL.md
```

The `description:` frontmatter field is what Claude Code matches against your messages to decide whether to invoke the skill. To contribute or modify a skill, edit the prose in `SKILL.md` — there is no build step.
