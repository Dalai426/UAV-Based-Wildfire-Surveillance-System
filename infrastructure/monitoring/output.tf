output "cloudwatch_log_group_name" {
  description = "Log Group Name"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "log_group_arn" {
  description = "Backend Log Group ARN"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}