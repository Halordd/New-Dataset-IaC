#!/usr/bin/env python3
"""Dataset sanity checks and basic visualizations for feature-based IaC dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

np = None  # filled in main()
pd = None  # filled in main()
sns = None  # filled in main()
plt = None  # filled in main()

META_COLS = {
    "sample_id",
    "repo_id",
    "repo_full_name",
    "commit_sha",
    "context_id",
    "context_score",
    "cluster_id",
}


def _feature_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if c not in META_COLS]


def compute_feature_stats(df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
    x = df[feature_cols].copy()
    for c in feature_cols:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0.0)

    rows: List[Dict[str, object]] = []
    for c in feature_cols:
        col = x[c].astype(float)
        rows.append(
            {
                "feature": c,
                "count": int(col.shape[0]),
                "zero_frac": float((col == 0).mean()),
                "mean": float(col.mean()),
                "std": float(col.std(ddof=0)),
                "min": float(col.min()),
                "p05": float(np.quantile(col, 0.05)),
                "p50": float(np.quantile(col, 0.50)),
                "p95": float(np.quantile(col, 0.95)),
                "max": float(col.max()),
            }
        )
    return pd.DataFrame(rows).sort_values(["zero_frac", "feature"], ascending=[False, True])


def save_histograms(df: pd.DataFrame, features: List[str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for feat in features:
        if feat not in df.columns:
            continue
        series = pd.to_numeric(df[feat], errors="coerce").fillna(0.0).astype(float)
        plt.figure(figsize=(7, 4))
        sns.histplot(series, bins=30, kde=False)
        plt.title(f"Histogram: {feat}")
        plt.xlabel(feat)
        plt.ylabel("count")
        plt.tight_layout()
        plt.savefig(out_dir / f"hist_{feat}.png", dpi=160)
        plt.close()


def save_boxplots_by_context(df: pd.DataFrame, features: List[str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if "context_id" not in df.columns:
        return
    for feat in features:
        if feat not in df.columns:
            continue
        plt.figure(figsize=(9, 4))
        tmp = df[["context_id", feat]].copy()
        tmp[feat] = pd.to_numeric(tmp[feat], errors="coerce").fillna(0.0).astype(float)
        sns.boxplot(data=tmp, x="context_id", y=feat)
        plt.title(f"Boxplot by context: {feat}")
        plt.tight_layout()
        plt.savefig(out_dir / f"box_{feat}_by_context.png", dpi=160)
        plt.close()


def save_corr_heatmap(df: pd.DataFrame, feature_cols: List[str], out_path: Path, max_features: int) -> None:
    x = df[feature_cols].copy()
    for c in feature_cols:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0.0).astype(float)

    # Keep top-N non-zero variance features to avoid unreadable heatmaps.
    var = x.var(axis=0)
    keep = var[var > 0].sort_values(ascending=False).head(max_features).index.tolist()
    if not keep:
        return

    corr = x[keep].corr()
    plt.figure(figsize=(11, 9))
    sns.heatmap(corr, cmap="coolwarm", center=0.0, square=True)
    plt.title("Feature correlation heatmap")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=180)
    plt.close()


def main() -> int:
    p = argparse.ArgumentParser(description="Sanity check and visualize feature dataset CSV.")
    p.add_argument("--input-csv", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("thesis_dataset_collection/output/sanity"))
    p.add_argument(
        "--plot-features",
        nargs="*",
        default=[
            "num_resources",
            "public_ingress_count",
            "public_ip_signal_count",
            "iam_count",
            "ec2_count",
            "s3_count",
            "rds_count",
            "lambda_count",
        ],
        help="Features to plot (hist + boxplot).",
    )
    p.add_argument("--corr-max-features", type=int, default=25)

    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        p.print_help()
        return 0

    try:
        import numpy as _np  # type: ignore
        import pandas as _pd  # type: ignore
        import seaborn as _sns  # type: ignore
        from matplotlib import pyplot as _plt  # type: ignore
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", "a required package")
        raise SystemExit(
            f"Missing dependency: {missing}. Install requirements first:\n"
            f"  pip install -r thesis_dataset_collection/requirements.txt"
        ) from exc

    global np, pd, sns, plt
    np, pd, sns, plt = _np, _pd, _sns, _plt

    args = p.parse_args()

    df = pd.read_csv(args.input_csv)
    feature_cols = _feature_columns(df)
    stats = compute_feature_stats(df, feature_cols)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stats_path = args.out_dir / "feature_stats.csv"
    stats.to_csv(stats_path, index=False)

    summary = {
        "rows": int(df.shape[0]),
        "num_features": int(len(feature_cols)),
        "input_csv": str(args.input_csv),
        "outputs": {
            "feature_stats_csv": str(stats_path),
        },
    }
    (args.out_dir / "sanity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    plots_dir = args.out_dir / "plots"
    save_histograms(df, args.plot_features, plots_dir)
    save_boxplots_by_context(df, args.plot_features, plots_dir)
    save_corr_heatmap(df, feature_cols, plots_dir / "corr_heatmap.png", max_features=args.corr_max_features)

    print(f"Sanity outputs written to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
