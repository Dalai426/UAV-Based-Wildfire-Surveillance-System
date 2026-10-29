resource "aws_key_pair" "bastion" {
  key_name   = "drone-bastion-key"
  public_key = file(pathexpand("~/.ssh/aws-bastion.pub"))
}

resource "aws_security_group" "bastion" {
  name        = "drone-bastion-sg"
  description = "SSH access to bastion host"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH from my computer only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Retrieve the latest Amazon Linux 2023 AMI
data "aws_ssm_parameter" "amazon_linux" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "bastion" {
  ami           = data.aws_ssm_parameter.amazon_linux.value
  instance_type = "t3.micro"

  subnet_id = var.public_subnets[0]

  vpc_security_group_ids = [
    aws_security_group.bastion.id
  ]
  key_name                    = aws_key_pair.bastion.key_name
  associate_public_ip_address = true
}