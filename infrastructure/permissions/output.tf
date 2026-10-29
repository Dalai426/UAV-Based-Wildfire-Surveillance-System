output "lambda_role_name" {
  description = "Names of the Lambda IAM roles"
  value = {
    for key, role in aws_iam_role.lambda_role :
    key => role.name
  }
}

output "lambda_role_arn" {
  description = "ARNs of the Lambda IAM roles"
  value = {
    for key, role in aws_iam_role.lambda_role :
    key => role.arn
  }
}
output "IoT_role_arn" {
  description = "IAM role ARN to use for Ground Station Auth"
  value       = aws_iam_role.iot_core_role.arn
}