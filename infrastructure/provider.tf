provider "aws" {
  region  = var.region
  profile = "ce1-group-ds"
  default_tags {
    tags = {
      Project   = "ce-semester-1"
      ManagedBy = "terraform"
    }
  }
}