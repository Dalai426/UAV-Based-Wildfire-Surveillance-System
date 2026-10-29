
# Get available availability zones in the specified region
data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.19.0"

  name = var.vpc_name

  azs = slice(
    data.aws_availability_zones.available.names,
    0,
    2
  )
  // The range of IP address 
  cidr            = "10.0.0.0/16"
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]

  create_igw = false
  // door that allow services in the vpc to access public internet
  enable_nat_gateway   = false
  enable_dns_support   = true
  enable_dns_hostnames = true
}

// virtual firewall
resource "aws_security_group" "lambda" {
  name        = "lambda-security-group"
  description = "Security group for Lambda functions"
  vpc_id      = module.vpc.vpc_id

  # The egress manages outgoing traffic
  # It allows lambda functions to connect IP addresses in VPC
  egress {
    description = "Allow outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}