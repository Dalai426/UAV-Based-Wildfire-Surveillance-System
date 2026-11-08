
resource "aws_sns_topic" "user_notifications" {
  name = "${var.project_name}-user-notifications"

  # Encryption using AWS-managed SNS key
  kms_master_key_id = "alias/aws/sns"
}


resource "aws_iam_policy" "lambda_sns_publish" {
  name        = "${var.project_name}-lambda-sns-publish"
  description = "Allow Lambda to publish SNS notifications"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sns:Subscribe",
          "sns:GetSubscriptionAttributes"
        ]
        Resource = aws_sns_topic.user_notifications.arn
      }
    ]
  })
}

# SNS VPC Interface Endpoint
resource "aws_vpc_endpoint" "sns" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.eu-north-1.sns"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  subnet_ids = var.private_subnets
  security_group_ids = [aws_security_group.sns_endpoint.id]
}

# Security Group for the SNS endpoint
resource "aws_security_group" "sns_endpoint" {
  name        = "drone-surveillance-system-sns-endpoint-sg"
  description = "Allow resources to reach SNS endpoint"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTPS from entire vpc"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks  = [var.network_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
