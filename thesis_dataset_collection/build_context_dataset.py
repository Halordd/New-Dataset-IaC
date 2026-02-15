#!/usr/bin/env python3
"""Assign behavioral contexts (C1-C8) and export feature dataset."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


def load_ndjson(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
    return rows


def load_profiles(path: Path) -> List[dict]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj["contexts"]


def feature_value(features: Dict[str, float], key: str) -> float:
    raw = features.get(key, 0)
    try:
        return float(raw)
    except Exception:
        return 0.0


def context_score(features: Dict[str, float], profile: dict) -> float:
    score = 0.0
    weights = profile.get("weights", {})
    for key, weight in weights.items():
        score += feature_value(features, key) * float(weight)
    for key in profile.get("required_positive", []):
        if feature_value(features, key) <= 0:
            return -10_000.0
    for key in profile.get("preferred_positive", []):
        if feature_value(features, key) > 0:
            score += 1.0
    for key in profile.get("preferred_negative", []):
        if feature_value(features, key) == 0:
            score += 1.0
    return score


def assign_context(features: Dict[str, float], profiles: List[dict]) -> Tuple[str, float]:
    best_id = "UNASSIGNED"
    best_score = -10_000.0
    for profile in profiles:
        score = context_score(features, profile)
        if score > best_score:
            best_score = score
            best_id = profile["context_id"]
    return best_id, best_score


def enforce_max_per_context(rows: List[dict], max_per_context: int) -> List[dict]:
    kept: List[dict] = []
    bucket_counts: Dict[str, int] = {}
    for row in rows:
        ctx = row["context_id"]
        cnt = bucket_counts.get(ctx, 0)
        if cnt >= max_per_context:
            continue
        bucket_counts[ctx] = cnt + 1
        kept.append(row)
    return kept


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_feature_keys = sorted(
        {k for row in rows for k in row["feature_vector"].keys()}
    )
    base_fields = [
        "sample_id",
        "repo_id",
        "repo_full_name",
        "commit_sha",
        "context_id",
        "context_score",
    ]
    fieldnames = base_fields + all_feature_keys
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {
                "sample_id": row["sample_id"],
                "repo_id": row["repo_id"],
                "repo_full_name": row["repo_full_name"],
                "commit_sha": row["commit_sha"],
                "context_id": row["context_id"],
                "context_score": row["context_score"],
            }
            for key in all_feature_keys:
                out[key] = row["feature_vector"].get(key, 0)
            writer.writerow(out)


def write_manifest(path: Path, rows: List[dict]) -> None:
    counts: Dict[str, int] = {}
    for row in rows:
        ctx = row["context_id"]
        counts[ctx] = counts.get(ctx, 0) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"context_counts": counts, "total": len(rows)}, indent=2), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Build context-balanced feature dataset.")
    p.add_argument("--input-ndjson", type=Path, required=True, help="Accepted dataset NDJSON.")
    p.add_argument(
        "--context-profiles",
        type=Path,
        default=Path("thesis_dataset_collection/context_profiles.json"),
        help="Context profile config path.",
    )
    p.add_argument("--max-per-context", type=int, default=200, help="Cap samples per context.")
    p.add_argument(
        "--output-csv",
        type=Path,
        default=Path("thesis_dataset_collection/output/context_dataset.csv"),
    )
    p.add_argument(
        "--output-manifest",
        type=Path,
        default=Path("thesis_dataset_collection/output/context_dataset_manifest.json"),
    )
    args = p.parse_args()

    samples = load_ndjson(args.input_ndjson)
    profiles = load_profiles(args.context_profiles)

    enriched: List[dict] = []
    for sample in samples:
        fv = sample.get("feature_vector", {})
        context_id, score = assign_context(fv, profiles)
        sample["context_id"] = context_id
        sample["context_score"] = score
        enriched.append(sample)

    enriched.sort(key=lambda x: (x["context_id"], -float(x["context_score"])))
    final_rows = enforce_max_per_context(enriched, args.max_per_context)
    write_csv(args.output_csv, final_rows)
    write_manifest(args.output_manifest, final_rows)
    print(f"Context dataset rows: {len(final_rows)}")
    print(f"CSV: {args.output_csv}")
    print(f"Manifest: {args.output_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
