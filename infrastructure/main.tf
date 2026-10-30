data "aws_caller_identity" "current" {}

locals {
  s3_bucket_name = lower(
    "${var.project_name}-${var.region}-s3"
  )
  vpc_name = lower(
    "${var.project_name}-${var.region}-vpc"
  )
  db_name = lower(
    "${var.project_name}-${var.region}-db"
  )
}

module "network" {
  source = "./network"
  // variables
  vpc_name = local.vpc_name
}

module "bastion_ec2" {
  source = "./bastion_ec2"
  // variables
  vpc_id         = module.network.vpc_id
  public_subnets = module.network.public_subnet_ids

}

module "database" {
  source = "./database"
  // variables
  db_name                   = local.db_name
  vpc_id                    = module.network.vpc_id
  db_instance_class         = "db.t3.micro"
  private_subnets           = module.network.private_subnet_ids
  network_cidr_block        = module.network.cidr_block
  bastion_security_group_id = module.bastion_ec2.bastion_security_group_id
}


module "monitoring" {
  source = "./monitoring"
  // variables
  project_name               = var.project_name
  budget_notification_emails = ["Gadalai426@gmail.com"]
}

module "storage" {
  source = "./s3"
  // variables
  s3_bucket_name = local.s3_bucket_name
}

module "permissions" {
  source = "./permissions"
  // variables
  project_name  = var.project_name
  s3_bucket_arn = module.storage.bucket_arn

  permissions_for_lambda = {
    "gsBackend" = {
      log_group_arn = module.monitoring.log_group_gs_arn
    }
    "dashboardBackend" = {
      log_group_arn = module.monitoring.log_group_dashboard_arn
    }
  }
}