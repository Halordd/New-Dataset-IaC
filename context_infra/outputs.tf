output "kinesis_stream_name" {
  value       = aws_kinesis_stream.monitron_ingest.name
  description = "Kinesis stream receiving Monitron telemetry."
}

output "firehose_delivery_stream_name" {
  value       = aws_kinesis_firehose_delivery_stream.to_data_lake.name
  description = "Firehose stream delivering telemetry into S3 data lake."
}

output "data_lake_bucket" {
  value       = aws_s3_bucket.data_lake.bucket
  description = "S3 data lake bucket name."
}

output "eventbridge_rule_name" {
  value       = aws_cloudwatch_event_rule.iot_events.name
  description = "EventBridge rule for IoT events."
}

output "sns_topic_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "SNS topic ARN used for alerts."
}

output "glue_database_name" {
  value       = aws_glue_catalog_database.data_lake_db.name
  description = "Glue database for data lake metadata."
}

output "athena_workgroup_name" {
  value       = aws_athena_workgroup.analytics.name
  description = "Athena workgroup for analysis."
}

output "grafana_workspace_id" {
  value       = var.enable_managed_grafana ? aws_grafana_workspace.this[0].id : null
  description = "Managed Grafana workspace ID if enabled."
}
