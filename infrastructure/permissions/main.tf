# The Role for Lambda Functions.
resource "aws_iam_role" "lambda_role" {

  for_each = var.permissions_for_lambda

  name = "${var.project_name}-${each.key}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_vpc_access" {
  name        = "${var.project_name}-lambda-vpc-access"
  description = "Allow Lambda to manage network interfaces for VPC access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:AssignPrivateIpAddresses",
        "ec2:UnassignPrivateIpAddresses"
      ]
      Resource = "*" # Required by AWS — EC2 network interfaces have no ARN scope
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  for_each   = var.permissions_for_lambda
  role       = aws_iam_role.lambda_role[each.key].name
  policy_arn = aws_iam_policy.lambda_vpc_access.arn
}

resource "aws_iam_policy" "lambda_logging" {
  for_each    = var.permissions_for_lambda
  name        = "${var.project_name}-${each.key}-lambda-logging"
  description = "Allow Lambda functions to write to the shared log group"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "${each.value.log_group_arn}:*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logging" {
  for_each   = var.permissions_for_lambda
  role       = aws_iam_role.lambda_role[each.key].name
  policy_arn = aws_iam_policy.lambda_logging[each.key].arn
}

# The Role for IoT Core
resource "aws_iam_role" "iot_core_role" {
  #https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role
  name = "${var.project_name}-IoT-credentials-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "credentials.iot.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "iot_s3_access" {
  name = "${var.project_name}-iot-s3-access"
  role = aws_iam_role.iot_core_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:PutObject"
      ]
      Resource = "${var.s3_bucket_arn}"
    }]
  })
}

