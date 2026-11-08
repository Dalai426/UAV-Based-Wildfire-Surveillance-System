variable "project_name" {
  description = "Project Name"
  type        = string
}

variable "network_cidr_block" {
  description = "the CIDR block of the VPC"
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