variable "project_name" {
  description = "Project Name"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 Bucket Arn"
  type        = string
}

variable "sqs_consume_policy_arn" {
  description = "The Arn of Sqs Consume Policy for Lambda functions"
  type        = string
}

variable "permissions_for_lambda" {
  description = "Permissions for Lambda functions"
  type = map(object({
    log_group_arn = string
  }))
}

variable "gs_backend_api_execution_arn" {
  description = "GS Backend API Gateway execution ARN"
  type        = string
}