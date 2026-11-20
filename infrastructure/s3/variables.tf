variable "s3_bucket_name" {
  description = "S3 Bucket Name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_route_table_ids" {
  description = "Private Route Table IDs"
  type        = list(string)
}