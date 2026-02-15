# Terraform Dataset Collection (GitHub Crawl + Filter)

This folder contains a runnable pipeline for collecting and filtering Terraform projects from GitHub:

- `algorithm.tex`: LaTeX algorithm block for thesis usage.
- `dataset_output.schema.json`: JSON schema for output records.
- `crawl_filter_cli.py`: runnable CLI pipeline.
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
