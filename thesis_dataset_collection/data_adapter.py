#!/usr/bin/env python3
"""
ARC_DATA_ADAPTER // THE BRIDGE (DECISION SUPPORT EDITION)
Bổ sung Feature Drift và Repository URLs.
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Cấu hình đường dẫn
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
PORTAL_DATA_DIR = BASE_DIR.parent / "dashboard" / "public" / "data"
CONTEXT_PROFILE_PATH = BASE_DIR / "context_profiles.json"

def load_data():
    print("> Loading pipeline artifacts...")
    df_normal = pd.read_csv(OUTPUT_DIR / "context_dataset.csv")
    
    anomalies = []
    with open(OUTPUT_DIR / "context_anomaly_dataset.ndjson", 'r', encoding='utf-8') as f:
        for line in f:
            anomalies.append(json.loads(line))
    
    df_anomaly = pd.DataFrame([
        {**a['feature_vector'], 'sample_id': a['sample_id'], 'context_id': a['context_id'], 'label': 1} 
        for a in anomalies
    ])
    df_normal['label'] = 0
    
    # Load model scores và metadata gốc để lấy URL
    df_scores = pd.read_csv(OUTPUT_DIR / "experiments" / "top_by_anomaly_score.csv")
    score_map = dict(zip(df_scores['sample_id'], df_scores['anomaly_score']))
    
    # Map repo_url từ context_dataset.csv
    url_map = dict(zip(df_normal['sample_id'], df_normal.get('repo_url', [''] * len(df_normal))))
    if 'repo_url' not in df_normal.columns:
        # Nếu không có trong CSV, thử lấy từ NDJSON nếu cần (giả lập placeholder nếu thiếu)
        url_map = {sid: f"https://github.com/{name}" for sid, name in zip(df_normal['sample_id'], df_normal['repo_full_name'])}

    return df_normal, df_anomaly, score_map, url_map

def process_vector_space(df_combined):
    print("> Computing PCA for Visual Orbit...")
    feature_cols = [c for c in df_combined.columns if c not in ['sample_id', 'repo_id', 'repo_full_name', 'commit_sha', 'context_id', 'context_score', 'label', 'repo_url', 'pca_x', 'pca_y']]
    
    x = df_combined[feature_cols].values
    x_scaled = StandardScaler().fit_transform(x)
    
    pca = PCA(n_components=2)
    coords = pca.fit_transform(x_scaled)
    
    df_combined['pca_x'] = coords[:, 0]
    df_combined['pca_y'] = coords[:, 1]
    
    df_n = df_combined[df_combined['label'] == 0]
    baselines = df_n.groupby('context_id')[feature_cols].mean().to_dict('index')
    
    return df_combined, feature_cols, baselines

def main():
    if not PORTAL_DATA_DIR.exists():
        PORTAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df_n, df_a, score_map, url_map = load_data()
    df_combined = pd.concat([df_n, df_a], ignore_index=True).fillna(0)
    
    df_processed, feat_cols, baselines = process_vector_space(df_combined)
    
    nodes = []
    for _, row in df_processed.iterrows():
        sid = str(row['sample_id'])
        ctx_id = row['context_id']
        
        # Tính toán Drift cho từng feature so với baseline của context
        drift_data = {}
        baseline = baselines.get(ctx_id, {f: 0.0 for f in feat_cols})
        for f in feat_cols:
            val = float(row[f])
            base_val = float(baseline.get(f, 0.0))
            # Tính % lệch (giới hạn để tránh chia cho 0)
            diff = val - base_val
            drift_data[f] = diff

        nodes.append({
            "id": sid,
            "name": str(row.get('repo_full_name', sid)),
            "url": url_map.get(sid, url_map.get(sid.split('::')[0], "#")),
            "context": str(ctx_id),
            "label": "anomaly" if row['label'] == 1 else "normal",
            "score": float(score_map.get(sid, 0.5)),
            "x": float(row['pca_x']),
            "y": float(row['pca_y']),
            "features": {f: float(row[f]) for f in feat_cols},
            "drift": drift_data
        })

    with open(CONTEXT_PROFILE_PATH, 'r') as f:
        context_profiles = json.load(f)
        
    with open(OUTPUT_DIR / "experiments" / "metrics.json", 'r') as f:
        model_metrics = json.load(f)

    master_data = {
        "metadata": {
            "generated_at": pd.Timestamp.now().isoformat(),
            "total_samples": len(nodes),
            "model_metrics": model_metrics,
            "feature_groups": {
                "Compute": ["ec2_count", "lambda_count"],
                "Network": ["vpc_count", "subnet_count", "public_ingress_count", "public_ip_signal_count", "private_network_signal_count"],
                "Storage": ["s3_count", "rds_count"],
                "IAM": ["iam_count"],
                "Security": ["security_group_count"]
            }
        },
        "contexts": context_profiles['contexts'],
        "nodes": nodes
    }

    output_path = PORTAL_DATA_DIR / "arc_master_data.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2)
    
    print(f"SUCCESS: Decision Support Data exported to {output_path}")

if __name__ == "__main__":
    main()
