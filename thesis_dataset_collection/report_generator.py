#!/usr/bin/env python3
"""Generate a concise experiment report (Markdown) from produced artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description="Generate report.md from sanity/clustering/metrics artifacts.")
    p.add_argument("--out-md", type=Path, default=Path("thesis_dataset_collection/output/reports/experiment_report.md"))
    p.add_argument("--sanity-summary", type=Path, default=Path("thesis_dataset_collection/output/sanity/sanity_summary.json"))
    p.add_argument("--clustering-metrics", type=Path, default=Path("thesis_dataset_collection/output/clustering_metrics.json"))
    p.add_argument("--metrics", type=Path, default=Path("thesis_dataset_collection/output/experiments/metrics.json"))
    args = p.parse_args()

    sanity = read_json(args.sanity_summary)
    clustering = read_json(args.clustering_metrics)
    metrics = read_json(args.metrics)

    lines = []
    lines.append("# Experiments & Results (Auto-generated)\n")
    lines.append("This report is generated from pipeline artifacts.\n")

    if sanity:
        lines.append("## Dataset Sanity Check\n")
        lines.append(f"- Rows: `{sanity.get('rows')}`\n")
        lines.append(f"- Num features: `{sanity.get('num_features')}`\n")
        lines.append(f"- Input: `{sanity.get('input_csv')}`\n")
        lines.append("- Plots: `thesis_dataset_collection/output/sanity/plots/`\n")
        lines.append("")

    if clustering:
        lines.append("## Context Formation (Clustering)\n")
        lines.append(f"- Algorithm: `{clustering.get('algorithm')}`\n")
        best = clustering.get("best")
        if isinstance(best, dict):
            lines.append(f"- Best k: `{best.get('k')}` (silhouette `{best.get('silhouette')}`)\n")
        cc = clustering.get("cluster_counts")
        if isinstance(cc, dict):
            lines.append(f"- Cluster counts: `{cc}`\n")
        lines.append("")

    if metrics:
        lines.append("## Unsupervised Anomaly Detection\n")
        lines.append(f"- Model: `{metrics.get('model')}`\n")
        lines.append(f"- Train normal rows: `{metrics.get('normal_rows')}`\n")
        lines.append(f"- Test anomaly rows: `{metrics.get('anomaly_rows')}`\n")
        lines.append(f"- ROC-AUC: `{metrics.get('roc_auc')}`\n")
        lines.append(f"- PR-AUC (Average Precision): `{metrics.get('average_precision')}`\n")
        lines.append(f"- Precision@k: `{metrics.get('precision_at_k')}` (k=`{metrics.get('k')}`)\n")
        lines.append(f"- Threshold (reporting only): `{metrics.get('suggested_threshold_for_reporting')}`\n")
        lines.append("")
        lines.append("- Per-context metrics: `thesis_dataset_collection/output/experiments/per_context_metrics.csv`\n")
        lines.append("- Top anomalies list: `thesis_dataset_collection/output/experiments/top_by_anomaly_score.csv`\n")
        lines.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Report written: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
