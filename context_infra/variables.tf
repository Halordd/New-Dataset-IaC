variable "aws_region" {
  description = "AWS region for deployment."
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Project name used in resource naming."
  type        = string
  default     = "context-iac"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "data_lake_bucket_name" {
  description = "Globally unique S3 bucket name for the data lake."
  type        = string
}

variable "kinesis_shard_count" {
  description = "Number of shards for the Kinesis stream."
  type        = number
  default     = 1
}

variable "alert_email" {
  description = "Optional email for SNS notifications. Set null to disable email subscription."
  type        = string
  default     = null
}

variable "enable_managed_grafana" {
  description = "Enable Amazon Managed Grafana workspace creation."
  type        = bool
  default     = false
}
