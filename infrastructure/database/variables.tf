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

variable "network_cidr_block" {
  description = "the CIDR block of the VPC"
  type        = string
}

variable "private_subnets" {
  description = "Private Subnet IDs"
  type        = list(string)
}