output "raw_bucket" {
  value       = aws_s3_bucket.raw.bucket
  description = "S3 bucket name for raw landing zone."
}

output "cleaned_bucket" {
  value       = aws_s3_bucket.cleaned.bucket
  description = "S3 bucket name for cleaned data zone."
}

output "curated_bucket" {
  value       = aws_s3_bucket.curated.bucket
  description = "S3 bucket name for curated analytics zone."
}

output "glue_database_name" {
  value       = aws_glue_catalog_database.regulated_db.name
  description = "Glue database used for regulated datasets."
}

output "athena_workgroup_name" {
  value       = aws_athena_workgroup.regulated_analytics.name
  description = "Athena workgroup for regulated data analytics."
}

output "eventbridge_rule_name" {
  value       = aws_cloudwatch_event_rule.regulated_events.name
  description = "EventBridge rule for regulated data compliance events."
}

output "sns_topic_arn" {
  value       = aws_sns_topic.compliance_alerts.arn
  description = "SNS topic ARN for compliance notifications."
}

output "kms_key_arn" {
  value       = aws_kms_key.data_lake.arn
  description = "KMS key ARN used for regulated data encryption."
}

output "cloudtrail_logs_bucket" {
  value       = var.enable_cloudtrail_data_events ? aws_s3_bucket.cloudtrail_logs[0].bucket : null
  description = "CloudTrail logs bucket when audit trail is enabled."
}

output "cloudtrail_trail_arn" {
  value       = var.enable_cloudtrail_data_events ? aws_cloudtrail.regulated[0].arn : null
  description = "CloudTrail ARN for management and S3 data events."
}
