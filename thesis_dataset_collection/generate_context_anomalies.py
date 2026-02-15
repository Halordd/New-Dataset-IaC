#!/usr/bin/env python3
"""Generate context-relative anomaly samples from feature dataset CSV."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from typing import Dict, List


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def mutate_features(row: Dict[str, str], context_id: str, rng: random.Random) -> Dict[str, float]:
    keys = [k for k in row.keys() if k not in {"sample_id", "repo_id", "repo_full_name", "commit_sha", "context_id", "context_score"}]
    fv = {k: to_float(row[k]) for k in keys}

    # Context-relative perturbations (behavioral drift), not static rule violations.
    if context_id == "C1":
        fv["public_ingress_count"] = fv.get("public_ingress_count", 0) + rng.uniform(1, 4)
    elif context_id == "C2":
        fv["public_ip_signal_count"] = fv.get("public_ip_signal_count", 0) + rng.uniform(1, 3)
    elif context_id == "C3":
        fv["ec2_count"] = fv.get("ec2_count", 0) + rng.uniform(1, 3)
    elif context_id == "C4":
        fv["public_ingress_count"] = fv.get("public_ingress_count", 0) + rng.uniform(1, 2)
    elif context_id == "C5":
        fv["public_ip_signal_count"] = fv.get("public_ip_signal_count", 0) + rng.uniform(1, 2)
    elif context_id == "C6":
        fv["iam_count"] = max(0.0, fv.get("iam_count", 0) - rng.uniform(1, 3))
        fv["ec2_count"] = fv.get("ec2_count", 0) + rng.uniform(2, 4)
    elif context_id == "C7":
        fv["public_ingress_count"] = fv.get("public_ingress_count", 0) + rng.uniform(1, 3)
    elif context_id == "C8":
        fv["num_resources"] = fv.get("num_resources", 0) + rng.uniform(5, 12)
        fv["public_ip_signal_count"] = fv.get("public_ip_signal_count", 0) + rng.uniform(1, 2)
    else:
        fv["public_ingress_count"] = fv.get("public_ingress_count", 0) + rng.uniform(1, 2)

    # Slight random noise across all features to avoid deterministic patterns.
    for k in list(fv.keys()):
        fv[k] = max(0.0, fv[k] + rng.uniform(-0.15, 0.15))
    return fv


def main() -> int:
    p = argparse.ArgumentParser(description="Generate synthetic context-relative anomaly feature samples.")
    p.add_argument("--input-csv", type=Path, required=True, help="Context dataset CSV.")
    p.add_argument(
        "--output-ndjson",
        type=Path,
        default=Path("thesis_dataset_collection/output/context_anomaly_dataset.ndjson"),
    )
    p.add_argument("--per-sample", type=int, default=1, help="Number of anomaly samples per normal row.")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    rng = random.Random(args.seed)
    rows = read_csv(args.input_csv)

    out: List[dict] = []
    for row in rows:
        context_id = row.get("context_id", "UNASSIGNED")
        for idx in range(args.per_sample):
            fv = mutate_features(row, context_id, rng)
            out.append(
                {
                    "sample_id": f"{row.get('sample_id', 'unknown')}::anomaly::{idx}",
                    "source_sample_id": row.get("sample_id", ""),
                    "context_id": context_id,
                    "label": "anomalous_behavior",
                    "feature_vector": fv,
                    "generation_method": "context_relative_behavioral_shift"
                }
            )

    args.output_ndjson.parent.mkdir(parents=True, exist_ok=True)
    with args.output_ndjson.open("w", encoding="utf-8") as f:
        for item in out:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Generated anomaly rows: {len(out)}")
    print(f"Output: {args.output_ndjson}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
