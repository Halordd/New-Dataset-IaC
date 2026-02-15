# Experiments & Results (Auto-generated)

This report is generated from pipeline artifacts.

## Dataset Sanity Check

- Rows: `40`

- Num features: `18`

- Input: `thesis_dataset_collection\output\context_dataset.csv`

- Plots: `thesis_dataset_collection/output/sanity/plots/`


## Context Formation (Clustering)

- Algorithm: `kmeans`

- Best k: `12` (silhouette `0.16072021817391935`)

- Cluster counts: `{'0': 10, '3': 10, '2': 6, '7': 3, '1': 3, '11': 2, '8': 1, '4': 1, '6': 1, '5': 1, '10': 1, '9': 1}`


## Unsupervised Anomaly Detection

- Model: `isolation_forest`

- Train normal rows: `40`

- Test anomaly rows: `40`

- ROC-AUC: `0.5275`

- PR-AUC (Average Precision): `0.5301313152293174`

- Precision@k: `0.5` (k=`4`)

- Threshold (reporting only): `0.35609699960800584`


- Per-context metrics: `thesis_dataset_collection/output/experiments/per_context_metrics.csv`

- Top anomalies list: `thesis_dataset_collection/output/experiments/top_by_anomaly_score.csv`
