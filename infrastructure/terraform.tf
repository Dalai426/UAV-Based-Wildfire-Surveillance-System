terraform {
  // it is like npm packages
  required_providers {
    aws = {
      // it refers provider name in terraform registry
      source  = "hashicorp/aws"
      version = ">= 5.79.0"
    }
  }
  # backend "s3" {
  #   bucket       = "stateterraform526"
  #   key          = "group-01/terraform.tfstate"
  #   region       = "us-east-2"
  #   use_lockfile = true
  # }
  required_version = ">= 1.0.0"
}