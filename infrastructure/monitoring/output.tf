output "log_group_gs_arn" {
  description = "Backend Log Group ARN"
  value       = aws_cloudwatch_log_group.gs_lambda_logs.arn
}

output "log_group_dashboard_arn" {
  description = "Dashboard Backend Log Group ARN"
  value       = aws_cloudwatch_log_group.dashboard_lambda_logs.arn
}