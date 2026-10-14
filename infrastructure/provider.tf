provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "ce-semester-1"
      ManagedBy = "terraform"
    }
  }
}