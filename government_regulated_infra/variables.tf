variable "aws_region" {
  description = "AWS region for deployment."
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name used in resource naming."
  type        = string
  default     = "gov-regulated-iac"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "raw_bucket_name" {
  description = "Globally unique S3 bucket for raw landing data."
  type        = string
}

variable "cleaned_bucket_name" {
  description = "Globally unique S3 bucket for cleaned/validated data."
  type        = string
}

variable "curated_bucket_name" {
  description = "Globally unique S3 bucket for curated analytics data."
  type        = string
}

variable "alert_email" {
  description = "Optional email for SNS notifications. Set null to disable email subscription."
  type        = string
  default     = null
}

variable "enable_cloudtrail_data_events" {
  description = "Enable CloudTrail management and S3 data events for audit/compliance."
  type        = bool
  default     = true
}

variable "cloudtrail_logs_bucket_name" {
  description = "Globally unique S3 bucket for CloudTrail logs."
  type        = string
  default     = null

  validation {
    condition     = !var.enable_cloudtrail_data_events || (var.cloudtrail_logs_bucket_name != null && var.cloudtrail_logs_bucket_name != "")
    error_message = "cloudtrail_logs_bucket_name must be set when enable_cloudtrail_data_events is true."
  }
}

variable "kms_deletion_window_in_days" {
  description = "KMS key deletion window in days."
  type        = number
  default     = 30
}

variable "enable_quicksight_namespace" {
  description = "Enable QuickSight namespace creation for analytics teams."
  type        = bool
  default     = false
}
