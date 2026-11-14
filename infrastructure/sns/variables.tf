variable "project_name" {
  description = "Project Name"
  type        = string
}

variable "lambda_security_group_id" {
  description = "The Security Group ID of Lambda functions"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnets" {
  description = "Private Subnet IDs"
  type        = list(string)
}