"""Train a small CNN on MNIST and write one run directory.

    python src/train.py --out experiments/exp_1/results/baseline/seed_0 --seed 0 [--augment random_crop]

Writes <out>/metrics.json with keys: seed, test_acc, epochs_completed.
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--augment", choices=["none", "random_crop"], default="none")
    ap.add_argument("--epochs", type=int, default=5)
    args = ap.parse_args()
    raise NotImplementedError("training loop elided in this fixture")


if __name__ == "__main__":
    main()
