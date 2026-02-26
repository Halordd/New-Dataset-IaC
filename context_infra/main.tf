locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "data_lake" {
  bucket = var.data_lake_bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_kinesis_stream" "monitron_ingest" {
  name             = "${local.name_prefix}-monitron-stream"
  shard_count      = var.kinesis_shard_count
  retention_period = 24

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = local.common_tags
}

data "aws_iam_policy_document" "firehose_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "firehose_role" {
  name               = "${local.name_prefix}-firehose-role"
  assume_role_policy = data.aws_iam_policy_document.firehose_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "firehose_policy" {
  statement {
    sid    = "ReadFromKinesis"
    effect = "Allow"
    actions = [
      "kinesis:DescribeStream",
      "kinesis:DescribeStreamSummary",
      "kinesis:GetShardIterator",
      "kinesis:GetRecords",
      "kinesis:ListShards"
    ]
    resources = [aws_kinesis_stream.monitron_ingest.arn]
  }

  statement {
    sid    = "WriteToS3"
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject"
    ]
    resources = [
      aws_s3_bucket.data_lake.arn,
      "${aws_s3_bucket.data_lake.arn}/*"
    ]
  }

  statement {
    sid    = "FirehoseLogging"
    effect = "Allow"
    actions = [
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "firehose_policy" {
  name   = "${local.name_prefix}-firehose-policy"
  role   = aws_iam_role.firehose_role.id
  policy = data.aws_iam_policy_document.firehose_policy.json
}

resource "aws_kinesis_firehose_delivery_stream" "to_data_lake" {
  name        = "${local.name_prefix}-firehose"
  destination = "extended_s3"

  kinesis_source_configuration {
    kinesis_stream_arn = aws_kinesis_stream.monitron_ingest.arn
    role_arn           = aws_iam_role.firehose_role.arn
  }

  extended_s3_configuration {
    role_arn           = aws_iam_role.firehose_role.arn
    bucket_arn         = aws_s3_bucket.data_lake.arn
    prefix             = "raw/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/"
    buffering_interval = 60
    buffering_size     = 5
    compression_format = "GZIP"
  }

  tags = local.common_tags
}

resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "email_alert" {
  count     = var.alert_email != null && var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${local.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid    = "LambdaBasicLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "PublishAlerts"
    effect = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [aws_sns_topic.alerts.arn]
  }
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${local.name_prefix}-lambda-policy"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

data "archive_file" "erp_forwarder_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/erp_forwarder.py"
  output_path = "${path.module}/build/erp_forwarder.zip"
}

data "archive_file" "alert_notifier_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/alert_notifier.py"
  output_path = "${path.module}/build/alert_notifier.zip"
}

resource "aws_lambda_function" "erp_forwarder" {
  function_name    = "${local.name_prefix}-erp-forwarder"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.11"
  handler          = "erp_forwarder.lambda_handler"
  filename         = data.archive_file.erp_forwarder_zip.output_path
  source_code_hash = data.archive_file.erp_forwarder_zip.output_base64sha256
  timeout          = 30
  tags             = local.common_tags
}

resource "aws_lambda_function" "alert_notifier" {
  function_name    = "${local.name_prefix}-alert-notifier"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.11"
  handler          = "alert_notifier.lambda_handler"
  filename         = data.archive_file.alert_notifier_zip.output_path
  source_code_hash = data.archive_file.alert_notifier_zip.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.alerts.arn
    }
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_event_rule" "iot_events" {
  name        = "${local.name_prefix}-iot-events"
  description = "Routes IoT/Monitron events for processing."
  event_pattern = jsonencode({
    source      = ["custom.iot.events"]
    detail-type = ["MonitronTelemetry"]
  })
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "erp_lambda_target" {
  rule      = aws_cloudwatch_event_rule.iot_events.name
  target_id = "erp-forwarder"
  arn       = aws_lambda_function.erp_forwarder.arn
}

resource "aws_cloudwatch_event_target" "alert_lambda_target" {
  rule      = aws_cloudwatch_event_rule.iot_events.name
  target_id = "alert-notifier"
  arn       = aws_lambda_function.alert_notifier.arn
}

resource "aws_lambda_permission" "allow_eventbridge_erp" {
  statement_id  = "AllowExecutionFromEventBridgeErp"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.erp_forwarder.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.iot_events.arn
}

resource "aws_lambda_permission" "allow_eventbridge_alert" {
  statement_id  = "AllowExecutionFromEventBridgeAlert"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert_notifier.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.iot_events.arn
}

data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "glue_role" {
  name               = "${local.name_prefix}-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "glue_policy" {
  statement {
    sid    = "GlueS3Access"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.data_lake.arn,
      "${aws_s3_bucket.data_lake.arn}/*"
    ]
  }

  statement {
    sid    = "GlueLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "glue_policy" {
  name   = "${local.name_prefix}-glue-policy"
  role   = aws_iam_role.glue_role.id
  policy = data.aws_iam_policy_document.glue_policy.json
}

resource "aws_glue_catalog_database" "data_lake_db" {
  name = replace("${local.name_prefix}_lake_db", "-", "_")
}

resource "aws_glue_crawler" "data_lake_raw" {
  name          = "${local.name_prefix}-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.data_lake_db.name
  table_prefix  = "raw_"
  schedule      = "cron(0 * * * ? *)"

  s3_target {
    path = "s3://${aws_s3_bucket.data_lake.bucket}/raw/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  tags = local.common_tags
}

resource "aws_athena_workgroup" "analytics" {
  name = "${local.name_prefix}-athena-wg"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_lake.bucket}/athena-results/"
    }
  }

  tags = local.common_tags
}

resource "aws_grafana_workspace" "this" {
  count                     = var.enable_managed_grafana ? 1 : 0
  name                      = "${local.name_prefix}-grafana"
  account_access_type       = "CURRENT_ACCOUNT"
  authentication_providers  = ["AWS_SSO"]
  permission_type           = "SERVICE_MANAGED"
  data_sources              = ["ATHENA", "CLOUDWATCH"]
  notification_destinations = ["SNS"]
  tags                      = local.common_tags
}
