#!/usr/bin/env python3
"""Inventory an experiment's results/ directory and aggregate its metrics.

Reads only what is on disk and prints one JSON document describing it, so the
report's numbers come from files rather than from mental arithmetic.

    python collect_results.py <exp_dir> \
        --primary test_f1_macro --baseline baseline_ce \
        --expect baseline_ce,focal_g2,focal_g2_no_reweight --seeds 3 \
        --out <exp_dir>/reports/inventory.json

Standard library only. Expected layout is results/<condition_id>/seed_<s>/
{metrics.json, git_commit.txt}; older flat layouts (metrics*.json directly in
the condition directory) are read too and tagged in the output.
"""
import argparse
import itertools
import json
import math
import random
import re
import statistics
import subprocess
import sys
from pathlib import Path

# Two-sided 95% Student-t critical values, indexed by degrees of freedom.
T_975 = [None, 12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262,
         2.228, 2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093,
         2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045,
         2.042]
AGGREGATE_HINTS = re.compile(r"(^|[._])(mean|std|stdev|stderr|sem|ci)($|[._])", re.I)
ENV_FILES = ["requirements.txt", "environment.yml", "environment.yaml", "pyproject.toml",
             "uv.lock", "poetry.lock", "conda-lock.yml", "Pipfile.lock"]


def tidy(obj):
    """Round floats to 10 significant digits so 0.024 doesn't print as 0.0239999…"""
    if isinstance(obj, float):
        return float(f"{obj:.10g}")
    if isinstance(obj, dict):
        return {k: tidy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [tidy(v) for v in obj]
    return obj


def flatten(obj, prefix=""):
    """Numeric leaves of a (possibly nested) dict, with dotted keys."""
    out = {}
    for key, value in obj.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, f"{name}."))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if math.isfinite(value):
                out[name] = value
    return out


def read_commit(*dirs):
    """First git_commit.txt found in dirs (run dir first, then condition dir)."""
    for d in dirs:
        f = d / "git_commit.txt"
        if not f.is_file():
            continue
        lines = [ln.strip() for ln in f.read_text(errors="replace").splitlines()
                 if ln.strip() and not ln.startswith("#")]
        if not lines:
            return {"file": str(f), "sha": None, "subject": None, "dirty": None,
                    "problem": "file is empty"}
        sha, _, subject = lines[0].partition(" ")
        valid = bool(re.fullmatch(r"[0-9a-f]{7,40}", sha))
        return {"file": str(f), "sha": sha if valid else None,
                "subject": subject.strip() or None,
                "dirty": any(ln.upper().startswith("DIRTY") for ln in lines[1:]),
                "problem": None if valid else "first line is not a commit hash"}
    return None


def make_run(name, metrics_file, raw, commit, ckpt_dir):
    run = {"run": name, "metrics_file": str(metrics_file) if metrics_file else None,
           "seed": None, "metrics": {}, "problem": None, "looks_pre_aggregated": False,
           "commit": commit,
           "has_checkpoints": bool(ckpt_dir and ckpt_dir.is_dir() and any(ckpt_dir.iterdir()))}
    if metrics_file is None:
        run["problem"] = "run directory has no metrics.json"
    elif not isinstance(raw, dict):
        run["problem"] = raw if isinstance(raw, str) else "metrics file is not a JSON object"
    else:
        run["metrics"] = flatten(raw)
        run["looks_pre_aggregated"] = any(AGGREGATE_HINTS.search(k) for k in run["metrics"])
        seed = raw.get("seed")
        run["seed"] = seed if isinstance(seed, (int, str)) and not isinstance(seed, bool) else None
    if run["seed"] is None:
        m = re.search(r"seed[_-]?(\w+)", name)
        if m:
            run["seed"] = int(m.group(1)) if m.group(1).isdigit() else m.group(1)
    return run


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return f"could not parse: {exc}"


def find_runs(cond):
    seed_dirs = sorted(d for d in cond.iterdir() if d.is_dir() and d.name.startswith("seed"))
    if seed_dirs:
        runs = []
        for d in seed_dirs:
            f = d / "metrics.json"
            runs.append(make_run(d.name, f if f.is_file() else None,
                                 load(f) if f.is_file() else None,
                                 read_commit(d, cond), d / "checkpoints"))
        return "seed_dirs", runs
    runs = []
    for f in sorted(cond.glob("metrics*.json")):
        raw = load(f)
        items = raw if isinstance(raw, list) else [raw]
        for i, item in enumerate(items):
            name = f.name if len(items) == 1 else f"{f.name}[{i}]"
            runs.append(make_run(name, f, item, read_commit(cond), cond / "checkpoints"))
    return ("flat_files" if runs else "none"), runs


def summarize(values):
    return {"n": len(values), "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else None,
            "min": min(values), "max": max(values)}


def sign_flip_p(diffs):
    """Two-sided paired sign-flip permutation p-value for mean(diffs) != 0."""
    observed = abs(sum(diffs))
    tol = 1e-12 * max(1.0, observed)
    if len(diffs) <= 16:
        flips = itertools.product((1, -1), repeat=len(diffs))
        totals = [abs(sum(s * d for s, d in zip(signs, diffs))) for signs in flips]
        return sum(t >= observed - tol for t in totals) / len(totals), "exact"
    rng = random.Random(0)
    n_draws = 100_000
    hits = sum(abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= observed - tol
               for _ in range(n_draws))
    return (hits + 1) / (n_draws + 1), "monte_carlo_100k"


def compare(base_runs, cond_runs, key):
    """Compare one condition to the baseline on the primary metric."""
    base = {r["seed"]: r["metrics"][key] for r in base_runs
            if key in r["metrics"] and r["seed"] is not None}
    cond = {r["seed"]: r["metrics"][key] for r in cond_runs
            if key in r["metrics"] and r["seed"] is not None}
    b_all = [r["metrics"][key] for r in base_runs if key in r["metrics"]]
    c_all = [r["metrics"][key] for r in cond_runs if key in r["metrics"]]
    if not b_all or not c_all:
        return {"problem": f"'{key}' missing on one side; no comparison possible"}
    out = {"delta_of_means": statistics.mean(c_all) - statistics.mean(b_all)}
    shared = sorted(set(base) & set(cond), key=str)
    diffs = [cond[s] - base[s] for s in shared]
    paired = {"shared_seeds": shared, "n_pairs": len(diffs), "per_seed_diff": diffs}
    if len(diffs) >= 2:
        mean_d, std_d = statistics.mean(diffs), statistics.stdev(diffs)
        df = len(diffs) - 1
        t = T_975[df] if df < len(T_975) else 1.96
        half = t * std_d / math.sqrt(len(diffs))
        p, method = sign_flip_p(diffs)
        paired.update({
            "mean_diff": mean_d, "std_diff": std_d,
            "ci95_mean_diff": [mean_d - half, mean_d + half],
            "ci95_excludes_zero": not (mean_d - half <= 0 <= mean_d + half),
            "ci_method": "paired t interval" + ("" if df < len(T_975) else " (normal approx.)"),
            "sign_flip_p_two_sided": p, "sign_flip_method": method,
            "min_achievable_p": 2 / 2 ** len(diffs),
        })
    else:
        paired["note"] = "fewer than 2 shared seeds; no paired statistics"
    out["paired"] = paired
    return out


def commit_in_repo(exp, sha):
    try:
        r = subprocess.run(["git", "-C", str(exp), "cat-file", "-e", f"{sha}^{{commit}}"],
                           capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode == 0:
        return True
    inside = subprocess.run(["git", "-C", str(exp), "rev-parse", "--git-dir"],
                            capture_output=True, timeout=10)
    return False if inside.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("exp_dir", type=Path, help="experiment folder, e.g. experiments/exp_3")
    ap.add_argument("--primary", help="primary metric key, exactly as named in DESIGN.md")
    ap.add_argument("--baseline", help="condition id to compare the others against")
    ap.add_argument("--expect", help="comma-separated condition ids planned in DESIGN.md")
    ap.add_argument("--seeds", type=int, help="seeds planned per condition")
    ap.add_argument("--out", type=Path, help="also write the JSON here")
    args = ap.parse_args()

    exp = args.exp_dir
    results = exp / "results"
    if not exp.is_dir():
        sys.exit(f"error: {exp} is not a directory")

    conditions = {}
    stray = []
    if results.is_dir():
        for entry in sorted(results.iterdir()):
            if entry.name.startswith("."):
                continue
            if not entry.is_dir():
                stray.append(entry.name)
                continue
            layout, runs = find_runs(entry)
            keys = sorted({k for r in runs for k in r["metrics"]})
            conditions[entry.name] = {
                "layout": layout, "n_runs": len(runs),
                "seeds": [r["seed"] for r in runs],
                "metric_keys": keys,
                "stats": {k: summarize([r["metrics"][k] for r in runs if k in r["metrics"]])
                          for k in keys if k != "seed"},
                "runs": runs,
            }

    primary = args.primary
    if primary:
        for cond in conditions.values():
            cond["primary"] = {
                "key": primary,
                "per_seed": {str(r["seed"] if r["seed"] is not None else r["run"]):
                             r["metrics"][primary] for r in cond["runs"] if primary in r["metrics"]},
                "runs_missing_key": [r["run"] for r in cond["runs"] if primary not in r["metrics"]],
            }

    comparisons = {}
    if primary and args.baseline:
        if args.baseline not in conditions:
            comparisons["problem"] = f"baseline '{args.baseline}' has no results directory"
        else:
            for name, cond in conditions.items():
                if name != args.baseline:
                    comparisons[name] = compare(conditions[args.baseline]["runs"],
                                                cond["runs"], primary)

    coverage = None
    if args.expect:
        expected = [c.strip() for c in args.expect.split(",") if c.strip()]
        coverage = {"planned": {}, "unplanned_conditions": sorted(set(conditions) - set(expected))}
        for cid in expected:
            runs = conditions.get(cid, {}).get("runs", [])
            usable = [r for r in runs if (primary in r["metrics"] if primary else r["metrics"])]
            coverage["planned"][cid] = {
                "has_results_dir": cid in conditions, "usable_runs": len(usable),
                "planned_seeds": args.seeds,
                "seeds_short": max(0, args.seeds - len(usable)) if args.seeds else None,
            }

    by_sha, missing, dirty, malformed = {}, [], [], []
    for name, cond in conditions.items():
        for r in cond["runs"]:
            label = f"{name}/{r['run']}"
            c = r["commit"]
            if c is None:
                missing.append(label)
            elif c["sha"] is None:
                malformed.append(label)
            else:
                by_sha.setdefault(c["sha"], []).append(label)
                if c["dirty"]:
                    dirty.append(label)
    provenance = {
        "runs_missing_git_commit": missing, "runs_with_malformed_git_commit": malformed,
        "runs_launched_dirty": dirty,
        "commits": {sha: {"runs": runs, "found_in_repo": commit_in_repo(exp, sha)}
                    for sha, runs in by_sha.items()},
        "all_runs_same_commit": len(by_sha) == 1 and not missing and not malformed,
    }

    root = exp.resolve().parent.parent
    design = next((n for n in ("DESIGN.md", "PLAN.md") if (exp / n).is_file()), None)
    figures = exp / "reports" / "figures"
    configs = exp / "scripts" / "configs"
    doc = {
        "experiment": str(exp),
        "files": {
            "design": design, "implementation": (exp / "IMPLEMENTATION.md").is_file(),
            "existing_report": (exp / "reports" / "summary.md").is_file(),
            "index": (exp.parent / "INDEX.md").is_file(),
            "configs": sorted(p.name for p in configs.iterdir()) if configs.is_dir() else [],
            "figures": sorted(p.name for p in figures.iterdir()) if figures.is_dir() else [],
            "environment_files": [str(p) for d in (root, root / "docs") for n in ENV_FILES
                                  for p in [d / n] if p.is_file()],
        },
        "results_dir_exists": results.is_dir(),
        "stray_files_in_results": stray,
        "conditions": conditions,
        "coverage": coverage,
        "comparisons_vs_baseline": comparisons or None,
        "provenance": provenance,
    }
    text = json.dumps(tidy(doc), indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
