# Government / Regulated Data Analytics Infrastructure (Terraform IaC)

Thư mục này là folder thứ 2 cho use case dữ liệu quản lý nhà nước, y tế và thống kê dân số.
Phiên bản này được tăng cường theo hướng regulated: mã hóa bằng KMS, audit truy cập dữ liệu bằng CloudTrail data events, và guardrail bucket policy.

## Sơ đồ kiến trúc

Ảnh kiến trúc được đặt trong thư mục `government_regulated_infra/picture`:

![Architecture Diagram](./picture/architech.jpg)

## Kiến trúc logic

1. Dữ liệu vào `raw` landing zone (S3)  
2. Dữ liệu sau xử lý nghiệp vụ vào `cleaned` zone (S3)  
3. Dữ liệu phục vụ phân tích vào `curated` zone (S3)  
4. Glue Crawler cập nhật metadata vào Glue Data Catalog  
5. Athena Workgroup phục vụ truy vấn phân tích (kết quả query được mã hóa KMS)  
6. EventBridge nhận sự kiện vi phạm/chất lượng dữ liệu  
7. Lambda gửi cảnh báo compliance qua SNS và forward sự kiện audit  
8. CloudTrail ghi management events + S3 data events để phục vụ kiểm toán

## Thành phần được tạo

- 3 S3 bucket dữ liệu: `raw`, `cleaned`, `curated`
- 1 S3 bucket audit logs cho CloudTrail (tùy chọn qua biến)
- KMS CMK + alias cho dữ liệu regulated
- Bật `versioning`, `SSE-KMS`, và `block public access` cho bucket
- Bucket policy guardrail:
  - deny request không dùng TLS (`aws:SecureTransport=false`)
  - deny upload object không khai báo `aws:kms`
- SNS topic + email subscription (tùy chọn)
- 2 Lambda:
  - `compliance_alert` (publish SNS)
  - `pii_audit_forwarder` (placeholder forward sang SIEM/SOC)
- EventBridge rule + targets để route sự kiện compliance vào Lambda
- Glue database + 2 crawler (raw/curated)
- Athena workgroup cho phân tích
- CloudTrail trail cho management + S3 data events (tùy chọn)
- QuickSight namespace (tùy chọn, bật bằng biến)

## Cách dùng

```bash
cd government_regulated_infra
cp terraform.tfvars.example terraform.tfvars
# Chỉnh lại tên bucket để đảm bảo unique toàn cục
terraform init
terraform plan
terraform apply
```

## Lưu ý triển khai thực tế

- `event_pattern` hiện là mẫu (`source=custom.gov.data`) để bạn thay bằng nguồn sự kiện thật (CloudTrail, Lake Formation, DQ pipeline, ...).
- Khi bật `enable_cloudtrail_data_events = true`, cần khai báo `cloudtrail_logs_bucket_name`.
- Nên bổ sung Lake Formation permissions + IAM least privilege theo vai trò dữ liệu (hành chính, y tế, dân số).
