#!/usr/bin/env python3
"""Train unsupervised anomaly detector on normal data and evaluate with anomalies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

np = None  # filled in main()
pd = None  # filled in main()
IsolationForest = None  # filled in main()
average_precision_score = None  # filled in main()
precision_recall_curve = None  # filled in main()
roc_auc_score = None  # filled in main()
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


def load_anomaly_ndjson(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
    return rows


def feature_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if c not in META_COLS]


def df_to_matrix(df: pd.DataFrame, feat_cols: List[str]) -> np.ndarray:
    x = df[feat_cols].copy()
    for c in feat_cols:
        x[c] = pd.to_numeric(x[c], errors="coerce").fillna(0.0).astype(float)
    return x.to_numpy(dtype=float)


def anomalies_to_matrix(rows: List[dict], feat_cols: List[str]) -> Tuple[np.ndarray, List[str], List[str]]:
    x = np.zeros((len(rows), len(feat_cols)), dtype=float)
    sample_ids: List[str] = []
    context_ids: List[str] = []
    for i, row in enumerate(rows):
        sample_ids.append(str(row.get("sample_id", f"anomaly_{i}")))
        context_ids.append(str(row.get("context_id", "UNASSIGNED")))
        fv = row.get("feature_vector", {}) or {}
        for j, c in enumerate(feat_cols):
            try:
                x[i, j] = float(fv.get(c, 0.0))
            except Exception:
                x[i, j] = 0.0
    return x, sample_ids, context_ids


def precision_at_k(y_true: np.ndarray, anomaly_score: np.ndarray, k: int) -> float:
    idx = np.argsort(-anomaly_score)[:k]
    return float(y_true[idx].mean()) if k > 0 else 0.0


def main() -> int:
    p = argparse.ArgumentParser(description="Train unsupervised anomaly detector and evaluate.")
    p.add_argument("--normal-csv", type=Path, required=True, help="Normal feature dataset CSV.")
    p.add_argument("--anomaly-ndjson", type=Path, required=True, help="Anomaly NDJSON from generator.")
    p.add_argument("--out-dir", type=Path, default=Path("thesis_dataset_collection/output/experiments"))
    p.add_argument("--model", choices=["isolation_forest"], default="isolation_forest")
    p.add_argument("--if-contamination", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--precision-k-frac", type=float, default=0.05, help="k = frac * N for Precision@k.")

    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        p.print_help()
        return 0

    try:
        import numpy as _np  # type: ignore
        import pandas as _pd  # type: ignore
        from sklearn.ensemble import IsolationForest as _IsolationForest  # type: ignore
        from sklearn.metrics import (  # type: ignore
            average_precision_score as _average_precision_score,
            precision_recall_curve as _precision_recall_curve,
            roc_auc_score as _roc_auc_score,
        )
        from sklearn.preprocessing import StandardScaler as _StandardScaler  # type: ignore
    except ModuleNotFoundError as exc:
        missing = getattr(exc, "name", "a required package")
        raise SystemExit(
            f"Missing dependency: {missing}. Install requirements first:\n"
            f"  pip install -r thesis_dataset_collection/requirements.txt"
        ) from exc

    global np, pd, IsolationForest, average_precision_score, precision_recall_curve, roc_auc_score, StandardScaler
    np, pd = _np, _pd
    IsolationForest = _IsolationForest
    average_precision_score = _average_precision_score
    precision_recall_curve = _precision_recall_curve
    roc_auc_score = _roc_auc_score
    StandardScaler = _StandardScaler

    args = p.parse_args()

    df_n = pd.read_csv(args.normal_csv)
    feat_cols = feature_columns(df_n)
    x_n = df_to_matrix(df_n, feat_cols)
    ctx_n = df_n["context_id"].astype(str).tolist() if "context_id" in df_n.columns else ["UNASSIGNED"] * len(df_n)

    anomalies = load_anomaly_ndjson(args.anomaly_ndjson)
    x_a, anomaly_ids, ctx_a = anomalies_to_matrix(anomalies, feat_cols)

    scaler = StandardScaler()
    x_n_s = scaler.fit_transform(x_n)
    x_a_s = scaler.transform(x_a)

    if args.model == "isolation_forest":
        model = IsolationForest(
            n_estimators=300,
            contamination=args.if_contamination,
            random_state=args.seed,
            n_jobs=-1,
        )
        model.fit(x_n_s)
        # Higher => more anomalous
        score_n = -model.score_samples(x_n_s)
        score_a = -model.score_samples(x_a_s)
    else:
        raise RuntimeError("Unsupported model.")

    y_true = np.concatenate([np.zeros(len(score_n)), np.ones(len(score_a))]).astype(int)
    scores = np.concatenate([score_n, score_a]).astype(float)
    contexts = ctx_n + ctx_a
    sample_ids = df_n["sample_id"].astype(str).tolist() + anomaly_ids

    roc = float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) == 2 else 0.0
    ap = float(average_precision_score(y_true, scores)) if len(np.unique(y_true)) == 2 else 0.0

    k = max(1, int(round(args.precision_k_frac * len(y_true))))
    p_at_k = precision_at_k(y_true, scores, k=k)

    # Threshold suggestion for reporting only: choose point maximizing F1 on PR curve.
    prec, rec, thr = precision_recall_curve(y_true, scores)
    f1 = (2 * prec * rec) / (prec + rec + 1e-12)
    best_idx = int(np.argmax(f1))
    suggested_threshold = float(thr[best_idx]) if best_idx < len(thr) else float(scores.max())

    args.out_dir.mkdir(parents=True, exist_ok=True)
    metrics = {
        "normal_rows": int(len(score_n)),
        "anomaly_rows": int(len(score_a)),
        "num_features": int(len(feat_cols)),
        "model": args.model,
        "roc_auc": roc,
        "average_precision": ap,
        "precision_at_k": float(p_at_k),
        "k": int(k),
        "suggested_threshold_for_reporting": suggested_threshold,
        "notes": "Train uses normal only. Anomaly labels are used only for evaluation.",
    }
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # Per-context metrics (AUC requires both classes present).
    per_ctx_rows: List[Dict[str, object]] = []
    unique_ctx = sorted(set(contexts))
    for ctx in unique_ctx:
        idx = [i for i, c in enumerate(contexts) if c == ctx]
        if not idx:
            continue
        y_c = y_true[idx]
        s_c = scores[idx]
        if len(np.unique(y_c)) < 2:
            per_ctx_rows.append({"context_id": ctx, "n": int(len(idx)), "roc_auc": None, "average_precision": None})
            continue
        per_ctx_rows.append(
            {
                "context_id": ctx,
                "n": int(len(idx)),
                "roc_auc": float(roc_auc_score(y_c, s_c)),
                "average_precision": float(average_precision_score(y_c, s_c)),
            }
        )
    pd.DataFrame(per_ctx_rows).to_csv(args.out_dir / "per_context_metrics.csv", index=False)

    # Top anomalies list for case studies.
    combined = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "context_id": contexts,
            "label": y_true,
            "anomaly_score": scores,
        }
    ).sort_values("anomaly_score", ascending=False)
    combined.head(50).to_csv(args.out_dir / "top_by_anomaly_score.csv", index=False)

    print(f"Metrics: {args.out_dir / 'metrics.json'}")
    print(f"Per-context: {args.out_dir / 'per_context_metrics.csv'}")
    print(f"Top list: {args.out_dir / 'top_by_anomaly_score.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
