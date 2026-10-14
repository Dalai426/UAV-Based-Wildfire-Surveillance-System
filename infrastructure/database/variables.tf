variable "db_name" {
  description = "DB name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "db_instance_class" {
  description = "RDS Instance Class for Database"
  type        = string
  default     = "db.t3.micro"
}

variable "lambda_security_group_id" {
  description = "Lambda Security Group ID"
  type        = string
}

variable "private_subnets" {
  description = "Private Subnet IDs"
  type        = list(string)
}