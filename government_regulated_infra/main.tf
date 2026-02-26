locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Domain      = "government-regulated-data"
    ManagedBy   = "terraform"
  }
}

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "data_lake" {
  description             = "CMK for regulated data zones and audit logs."
  deletion_window_in_days = var.kms_deletion_window_in_days
  enable_key_rotation     = true
  tags                    = local.common_tags
}

resource "aws_kms_alias" "data_lake" {
  name          = "alias/${local.name_prefix}-regulated-data"
  target_key_id = aws_kms_key.data_lake.key_id
}

resource "aws_s3_bucket" "raw" {
  bucket = var.raw_bucket_name
  tags   = merge(local.common_tags, { DataZone = "raw" })
}

resource "aws_s3_bucket" "cleaned" {
  bucket = var.cleaned_bucket_name
  tags   = merge(local.common_tags, { DataZone = "cleaned" })
}

resource "aws_s3_bucket" "curated" {
  bucket = var.curated_bucket_name
  tags   = merge(local.common_tags, { DataZone = "curated" })
}

resource "aws_s3_bucket" "cloudtrail_logs" {
  count  = var.enable_cloudtrail_data_events ? 1 : 0
  bucket = var.cloudtrail_logs_bucket_name
  tags   = merge(local.common_tags, { DataZone = "audit" })
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "cleaned" {
  bucket = aws_s3_bucket.cleaned.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "curated" {
  bucket = aws_s3_bucket.curated.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "cloudtrail_logs" {
  count  = var.enable_cloudtrail_data_events ? 1 : 0
  bucket = aws_s3_bucket.cloudtrail_logs[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_lake.arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cleaned" {
  bucket = aws_s3_bucket.cleaned.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_lake.arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "curated" {
  bucket = aws_s3_bucket.curated.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_lake.arn
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail_logs" {
  count  = var.enable_cloudtrail_data_events ? 1 : 0
  bucket = aws_s3_bucket.cloudtrail_logs[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_lake.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "cleaned" {
  bucket                  = aws_s3_bucket.cleaned.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "curated" {
  bucket                  = aws_s3_bucket.curated.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "cloudtrail_logs" {
  count                   = var.enable_cloudtrail_data_events ? 1 : 0
  bucket                  = aws_s3_bucket.cloudtrail_logs[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "raw_bucket_policy" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.raw.arn, "${aws_s3_bucket.raw.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid       = "DenyUnencryptedObjectUploads"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.raw.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }
}

data "aws_iam_policy_document" "cleaned_bucket_policy" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.cleaned.arn, "${aws_s3_bucket.cleaned.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid       = "DenyUnencryptedObjectUploads"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.cleaned.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }
}

data "aws_iam_policy_document" "curated_bucket_policy" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.curated.arn, "${aws_s3_bucket.curated.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    sid       = "DenyUnencryptedObjectUploads"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.curated.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEquals"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }
}

resource "aws_s3_bucket_policy" "raw" {
  bucket = aws_s3_bucket.raw.id
  policy = data.aws_iam_policy_document.raw_bucket_policy.json
}

resource "aws_s3_bucket_policy" "cleaned" {
  bucket = aws_s3_bucket.cleaned.id
  policy = data.aws_iam_policy_document.cleaned_bucket_policy.json
}

resource "aws_s3_bucket_policy" "curated" {
  bucket = aws_s3_bucket.curated.id
  policy = data.aws_iam_policy_document.curated_bucket_policy.json
}

resource "aws_sns_topic" "compliance_alerts" {
  name = "${local.name_prefix}-compliance-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "email_alert" {
  count     = var.alert_email != null && var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.compliance_alerts.arn
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
    sid    = "PublishComplianceAlerts"
    effect = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [aws_sns_topic.compliance_alerts.arn]
  }
}

resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${local.name_prefix}-lambda-policy"
  role   = aws_iam_role.lambda_role.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

data "archive_file" "compliance_alert_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/compliance_alert.py"
  output_path = "${path.module}/build/compliance_alert.zip"
}

data "archive_file" "pii_audit_forwarder_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/pii_audit_forwarder.py"
  output_path = "${path.module}/build/pii_audit_forwarder.zip"
}

resource "aws_lambda_function" "compliance_alert" {
  function_name    = "${local.name_prefix}-compliance-alert"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.11"
  handler          = "compliance_alert.lambda_handler"
  filename         = data.archive_file.compliance_alert_zip.output_path
  source_code_hash = data.archive_file.compliance_alert_zip.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.compliance_alerts.arn
    }
  }

  tags = local.common_tags
}

resource "aws_lambda_function" "pii_audit_forwarder" {
  function_name    = "${local.name_prefix}-pii-audit-forwarder"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.11"
  handler          = "pii_audit_forwarder.lambda_handler"
  filename         = data.archive_file.pii_audit_forwarder_zip.output_path
  source_code_hash = data.archive_file.pii_audit_forwarder_zip.output_base64sha256
  timeout          = 30
  tags             = local.common_tags
}

resource "aws_cloudwatch_event_rule" "regulated_events" {
  name        = "${local.name_prefix}-regulated-events"
  description = "Routes regulated data governance and anomaly events."
  event_pattern = jsonencode({
    source = ["custom.gov.data"]
    detail-type = [
      "PIIAccessViolation",
      "SensitiveDatasetAnomaly",
      "DataQualityBreach"
    ]
  })
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "compliance_alert_target" {
  rule      = aws_cloudwatch_event_rule.regulated_events.name
  target_id = "compliance-alert"
  arn       = aws_lambda_function.compliance_alert.arn
}

resource "aws_cloudwatch_event_target" "pii_audit_forwarder_target" {
  rule      = aws_cloudwatch_event_rule.regulated_events.name
  target_id = "pii-audit-forwarder"
  arn       = aws_lambda_function.pii_audit_forwarder.arn
}

resource "aws_lambda_permission" "allow_eventbridge_compliance_alert" {
  statement_id  = "AllowExecutionFromEventBridgeComplianceAlert"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.compliance_alert.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.regulated_events.arn
}

resource "aws_lambda_permission" "allow_eventbridge_pii_audit_forwarder" {
  statement_id  = "AllowExecutionFromEventBridgePiiAuditForwarder"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pii_audit_forwarder.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.regulated_events.arn
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
      aws_s3_bucket.raw.arn,
      "${aws_s3_bucket.raw.arn}/*",
      aws_s3_bucket.cleaned.arn,
      "${aws_s3_bucket.cleaned.arn}/*",
      aws_s3_bucket.curated.arn,
      "${aws_s3_bucket.curated.arn}/*"
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

resource "aws_glue_catalog_database" "regulated_db" {
  name = replace("${local.name_prefix}_regulated_db", "-", "_")
}

resource "aws_glue_crawler" "raw_crawler" {
  name          = "${local.name_prefix}-raw-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.regulated_db.name
  table_prefix  = "raw_"
  schedule      = "cron(0 * * * ? *)"

  s3_target {
    path = "s3://${aws_s3_bucket.raw.bucket}/landing/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  tags = local.common_tags
}

resource "aws_glue_crawler" "curated_crawler" {
  name          = "${local.name_prefix}-curated-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.regulated_db.name
  table_prefix  = "curated_"
  schedule      = "cron(15 * * * ? *)"

  s3_target {
    path = "s3://${aws_s3_bucket.curated.bucket}/analytics/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  tags = local.common_tags
}

resource "aws_athena_workgroup" "regulated_analytics" {
  name = "${local.name_prefix}-athena-wg"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    result_configuration {
      encryption_configuration {
        encryption_option = "SSE_KMS"
        kms_key_arn       = aws_kms_key.data_lake.arn
      }
      output_location = "s3://${aws_s3_bucket.curated.bucket}/athena-results/"
    }
  }

  tags = local.common_tags
}

data "aws_iam_policy_document" "cloudtrail_bucket_policy" {
  count = var.enable_cloudtrail_data_events ? 1 : 0

  statement {
    sid    = "AWSCloudTrailAclCheck"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.cloudtrail_logs[0].arn]
  }

  statement {
    sid    = "AWSCloudTrailWrite"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.cloudtrail_logs[0].arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}

resource "aws_s3_bucket_policy" "cloudtrail_logs" {
  count  = var.enable_cloudtrail_data_events ? 1 : 0
  bucket = aws_s3_bucket.cloudtrail_logs[0].id
  policy = data.aws_iam_policy_document.cloudtrail_bucket_policy[0].json
}

resource "aws_cloudtrail" "regulated" {
  count                          = var.enable_cloudtrail_data_events ? 1 : 0
  name                           = "${local.name_prefix}-trail"
  s3_bucket_name                 = aws_s3_bucket.cloudtrail_logs[0].id
  include_global_service_events  = true
  is_multi_region_trail          = true
  enable_log_file_validation     = true
  kms_key_id                     = aws_kms_key.data_lake.arn
  depends_on                     = [aws_s3_bucket_policy.cloudtrail_logs]

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["${aws_s3_bucket.raw.arn}/"]
    }

    data_resource {
      type   = "AWS::S3::Object"
      values = ["${aws_s3_bucket.cleaned.arn}/"]
    }

    data_resource {
      type   = "AWS::S3::Object"
      values = ["${aws_s3_bucket.curated.arn}/"]
    }
  }

  tags = local.common_tags
}

resource "aws_quicksight_namespace" "analytics" {
  count          = var.enable_quicksight_namespace ? 1 : 0
  namespace      = "${replace(local.name_prefix, "-", "_")}_analytics"
  identity_store = "QUICKSIGHT"
}
