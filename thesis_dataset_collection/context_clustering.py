#!/usr/bin/env python3
"""Form deployment contexts via clustering on feature vectors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

np = None  # filled in main()
pd = None  # filled in main()
DBSCAN = None  # filled in main()
KMeans = None  # filled in main()
silhouette_score = None  # filled in main()
StandardScaler = None  # filled in main()


META_COLS = {
    "sample_id",
    "repo_id",
    "repo_full_name",
    "commit_sha",
    "context_id",
    "context_score",
    "cluster_id",
}


def feature_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if c not in META_COLS]


def to_matrix(df: pd.DataFrame, cols: List[str]) -> np.ndarray:
    x = df[cols].copy()
    for c in cols:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0.0).astype(float)
    return x.to_numpy(dtype=float)


def run_kmeans(
    x_scaled: np.ndarray, k_min: int, k_max: int, seed: int
) -> Tuple[np.ndarray, Dict[str, object]]:
    best = {"k": None, "silhouette": -1.0, "inertia": None}
    best_labels: np.ndarray | None = None

    for k in range(k_min, k_max + 1):
        model = KMeans(n_clusters=k, n_init="auto", random_state=seed)
        labels = model.fit_predict(x_scaled)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(x_scaled, labels)
        if score > float(best["silhouette"]):
            best = {"k": k, "silhouette": float(score), "inertia": float(model.inertia_)}
            best_labels = labels

    if best_labels is None:
        raise RuntimeError("KMeans failed to produce >=2 clusters.")
    return best_labels, {"algorithm": "kmeans", "best": best}


def run_dbscan(x_scaled: np.ndarray, eps: float, min_samples: int) -> Tuple[np.ndarray, Dict[str, object]]:
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(x_scaled)
    n_clusters = len({x for x in labels if x != -1})
    metrics: Dict[str, object] = {"algorithm": "dbscan", "eps": eps, "min_samples": min_samples, "n_clusters": n_clusters}
    if n_clusters >= 2:
        # Compute silhouette excluding noise points.
        mask = labels != -1
        if int(mask.sum()) >= 2:
            metrics["silhouette_no_noise"] = float(silhouette_score(x_scaled[mask], labels[mask]))
    return labels, metrics


def main() -> int:
    p = argparse.ArgumentParser(description="Cluster contexts from feature dataset.")
    p.add_argument("--input-csv", type=Path, required=True)
    p.add_argument("--output-csv", type=Path, default=Path("thesis_dataset_collection/output/context_clustered.csv"))
    p.add_argument("--output-metrics", type=Path, default=Path("thesis_dataset_collection/output/clustering_metrics.json"))
    p.add_argument("--algo", choices=["kmeans", "dbscan"], default="kmeans")
    p.add_argument("--k-min", type=int, default=4)
    p.add_argument("--k-max", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dbscan-eps", type=float, default=1.2)
    p.add_argument("--dbscan-min-samples", type=int, default=6)

    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        p.print_help()
        return 0

    try:
        import numpy as _np  # type: ignore
        import pandas as _pd  # type: ignore
        from sklearn.cluster import DBSCAN as _DBSCAN, KMeans as _KMeans  # type: ignore
        from sklearn.metrics import silhouette_score as _silhouette_score  # type: ignore
        from sklearn.preprocessing import StandardScaler as _StandardScaler  # type: ignore
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", "a required package")
        raise SystemExit(
            f"Missing dependency: {missing}. Install requirements first:\n"
            f"  pip install -r thesis_dataset_collection/requirements.txt"
        ) from exc

    global np, pd, DBSCAN, KMeans, silhouette_score, StandardScaler
    np, pd = _np, _pd
    DBSCAN, KMeans = _DBSCAN, _KMeans
    silhouette_score, StandardScaler = _silhouette_score, _StandardScaler

    args = p.parse_args()

    df = pd.read_csv(args.input_csv)
    feats = feature_columns(df)
    x = to_matrix(df, feats)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    if args.algo == "kmeans":
        labels, metrics = run_kmeans(x_scaled, args.k_min, args.k_max, args.seed)
    else:
        labels, metrics = run_dbscan(x_scaled, args.dbscan_eps, args.dbscan_min_samples)

    df_out = df.copy()
    df_out["cluster_id"] = labels.astype(int)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(args.output_csv, index=False)

    # Optional: show distribution to help choose k/eps.
    counts = df_out["cluster_id"].value_counts(dropna=False).to_dict()
    metrics["cluster_counts"] = {str(k): int(v) for k, v in counts.items()}
    metrics["rows"] = int(df_out.shape[0])
    metrics["num_features"] = int(len(feats))

    args.output_metrics.parent.mkdir(parents=True, exist_ok=True)
    args.output_metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Clustered CSV: {args.output_csv}")
    print(f"Metrics: {args.output_metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
