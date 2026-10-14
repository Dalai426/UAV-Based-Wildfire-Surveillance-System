output "lambda_role_name" {
  description = "IAM role name for Lambda"
  value       = aws_iam_role.lambda_role.name
}

output "lambda_role_arn" {
  description = "IAM role ARN to use when creating Lambda functions"
  value       = aws_iam_role.lambda_role.arn
}