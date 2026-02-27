# New-Dataset-IaC

Repository này phục vụ đồ án về xây dựng dataset và hạ tầng mẫu cho các bài toán phân tích dữ liệu trên AWS bằng Terraform.

## Cấu trúc chính

- `context_infra`: Hạ tầng mẫu ingest/processing/analytics cho luồng dữ liệu IoT/operational.
- `government_regulated_infra`: Hạ tầng mẫu cho dữ liệu regulated (hành chính công, y tế, thống kê dân số) với lớp bảo mật/audit nâng cao.
- `thesis_dataset_collection`: Bộ script thu thập, chuẩn hóa, sinh ngữ cảnh/anomaly và đánh giá dữ liệu phục vụ thí nghiệm.

## Bắt đầu nhanh

### 1) Hạ tầng Terraform

Chạy trong từng thư mục hạ tầng:

```bash
cd context_infra
# hoặc: cd government_regulated_infra
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

### 2) Dataset pipeline

```bash
cd thesis_dataset_collection
pip install -r requirements.txt
python build_context_dataset.py
python generate_context_anomalies.py
python train_eval_unsupervised.py
```

## Chi tiết `thesis_dataset_collection`

Folder này là pipeline dữ liệu cho luận văn, gồm 3 nhóm chính:

- **Thu thập + lọc project Terraform từ GitHub**
  - Script chính: `crawl_filter_cli.py`
  - Đầu ra: `output/terraform_dataset.ndjson`
  - Bộ lọc gồm: maturity, keyword exclusion, kiểm tra cú pháp/validate Terraform, kiểm tra cấu trúc, lọc outlier hành vi.

- **Xây dataset theo ngữ cảnh (C1-C8) + sinh anomaly**
  - `build_context_dataset.py`: gán context và xuất `output/context_dataset.csv`
  - `generate_context_anomalies.py`: sinh bất thường theo từng context, xuất `output/context_anomaly_dataset.ndjson`
  - Hồ sơ context/query: `context_profiles.json`, `query_profiles.json`

- **Thí nghiệm mô hình**
  - `sanity_check.py`: kiểm tra thống kê dữ liệu
  - `context_clustering.py`: tạo cụm ngữ cảnh, xuất `output/context_clustered.csv`
  - `train_eval_unsupervised.py`: train/eval mô hình unsupervised anomaly detection
  - `report_generator.py`: sinh báo cáo markdown tại `output/reports/experiment_report.md`

### Luồng chạy khuyến nghị

```bash
cd thesis_dataset_collection
pip install -r requirements.txt
python crawl_filter_cli.py --keywords terraform aws --search-limit 80 --max-tf-files 20 --min-stars 1 --output output/terraform_dataset.ndjson
python build_context_dataset.py --input-ndjson output/terraform_dataset.ndjson --output-csv output/context_dataset.csv --output-manifest output/context_dataset_manifest.json
python generate_context_anomalies.py --input-csv output/context_dataset.csv --per-sample 1 --output-ndjson output/context_anomaly_dataset.ndjson
python train_eval_unsupervised.py --normal-csv output/context_dataset.csv --anomaly-ndjson output/context_anomaly_dataset.ndjson --out-dir output/experiments
python report_generator.py --out-md output/reports/experiment_report.md
```

## Ghi chú

- Nhớ đổi tên S3 bucket trong file `terraform.tfvars` để đảm bảo unique toàn cục.
- Với môi trường regulated thực tế, cần bổ sung IAM/Lake Formation permissions theo nguyên tắc least privilege.
