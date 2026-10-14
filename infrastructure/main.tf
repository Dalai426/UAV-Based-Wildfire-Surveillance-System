data "aws_caller_identity" "current" {}

locals {
  s3_bucket_name = lower(
    "${var.project_name}-${var.region}-s3"
  )
}

module "storage" {
  source = "./storage"
  // variables
  s3_bucket_name = local.s3_bucket_name
}

module "permissions" {
  source = "./permissions"
  // variables
  project_name = var.project_name
}


