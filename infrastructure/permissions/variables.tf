variable "project_name" {
  description = "Project Name"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 Bucket Arn"
  type        = string
}

variable "permissions_for_lambda" {
  description = "Permissions for Lambda functions"
  type = map(object({
    log_group_arn = string
  }))
}