# Terraform Dataset Collection (GitHub Crawl + Filter)

This folder contains a runnable pipeline for collecting and filtering Terraform projects from GitHub:

- `algorithm.tex`: LaTeX algorithm block for thesis usage.
- `dataset_output.schema.json`: JSON schema for output records.
- `crawl_filter_cli.py`: runnable CLI pipeline.
- `context_profiles.json`: behavioral context definitions (C1-C8).
- `query_profiles.json`: query presets for context coverage.
- `build_context_dataset.py`: assign contexts and export feature CSV.
- `generate_context_anomalies.py`: generate context-relative anomaly samples.
- `requirements.txt`: Python dependencies (none beyond standard library).

## Prerequisites

- Python 3.10+ (recommended)
- Terraform CLI installed and available in `PATH`
- GitHub token (recommended to avoid strict rate limits)

## Quick Start

1. Install Python dependencies:

```bash
pip install -r thesis_dataset_collection/requirements.txt
```

2. Set GitHub token:

```bash
set GITHUB_TOKEN=your_token_here
```

3. Run the pipeline:

```bash
python thesis_dataset_collection/crawl_filter_cli.py --keywords terraform aws aws_security_group aws_iam_policy --search-limit 100 --output thesis_dataset_collection/output/terraform_dataset.ndjson
```

### Dry-run mode (fast debug)

Use `--dry-run` to skip `terraform init/validate` and test filtering logic quickly:

```bash
python thesis_dataset_collection/crawl_filter_cli.py --keywords terraform aws --search-limit 30 --dry-run --output thesis_dataset_collection/output/terraform_dataset_dryrun.ndjson
```

If you hit GitHub rate limit (HTTP 403), reduce request volume:

```bash
python thesis_dataset_collection/crawl_filter_cli.py --keywords terraform aws --search-limit 50 --max-tf-files 20 --dry-run --output thesis_dataset_collection/output/terraform_dataset_dryrun.ndjson
```

## Main Filters

The pipeline applies:

1. Keyword exclusion
2. Project maturity thresholds
3. Terraform syntax validation (`terraform init`, `terraform validate`) - skipped when `--dry-run` is enabled
4. Structural validity checks
5. Behavior-based outlier filtering

## Output

- Dataset file: `thesis_dataset_collection/output/terraform_dataset.ndjson`
- Output schema: `thesis_dataset_collection/dataset_output.schema.json`

Each accepted record includes repository metadata, pinned commit SHA, Terraform file hashes (SHA-256), extracted features, and filter trace fields.

## Context dataset pipeline (C1-C8)

1. Crawl/filter normal samples (NDJSON):

```bash
python thesis_dataset_collection/crawl_filter_cli.py --keywords terraform aws --search-limit 80 --max-tf-files 20 --min-stars 1 --min-forks 0 --max-age-months 120 --forbidden-keywords vulnerable insecure --output thesis_dataset_collection/output/terraform_dataset.ndjson
```

2. Assign deployment context and export feature dataset:

```bash
python thesis_dataset_collection/build_context_dataset.py --input-ndjson thesis_dataset_collection/output/terraform_dataset.ndjson --output-csv thesis_dataset_collection/output/context_dataset.csv --output-manifest thesis_dataset_collection/output/context_dataset_manifest.json
```

3. Generate anomaly samples relative to each context:

```bash
python thesis_dataset_collection/generate_context_anomalies.py --input-csv thesis_dataset_collection/output/context_dataset.csv --per-sample 1 --output-ndjson thesis_dataset_collection/output/context_anomaly_dataset.ndjson
```

## Experiments pipeline (sanity + clustering + model)

1. Sanity check + plots:

```bash
python thesis_dataset_collection/sanity_check.py --input-csv thesis_dataset_collection/output/context_dataset.csv --out-dir thesis_dataset_collection/output/sanity
```

2. Context formation (clustering on features):

```bash
python thesis_dataset_collection/context_clustering.py --input-csv thesis_dataset_collection/output/context_dataset.csv --algo kmeans --k-min 4 --k-max 12 --output-csv thesis_dataset_collection/output/context_clustered.csv --output-metrics thesis_dataset_collection/output/clustering_metrics.json
```

3. Train unsupervised anomaly detector (train normal only, evaluate with anomalies):

```bash
python thesis_dataset_collection/train_eval_unsupervised.py --normal-csv thesis_dataset_collection/output/context_dataset.csv --anomaly-ndjson thesis_dataset_collection/output/context_anomaly_dataset.ndjson --out-dir thesis_dataset_collection/output/experiments
```

4. Generate a concise Markdown report:

```bash
python thesis_dataset_collection/report_generator.py --out-md thesis_dataset_collection/output/reports/experiment_report.md
```
