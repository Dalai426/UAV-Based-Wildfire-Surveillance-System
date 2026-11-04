output "sns_role_policy_arn" {
  value = aws_iam_policy.lambda_sns_publish.arn
}

output "sns_topic_arn" {
  description = "SNS topic ARN for user notifications"
  value       = aws_sns_topic.user_notifications.arn
}

output "sns_topic_name" {
  description = "SNS topic name"
  value       = aws_sns_topic.user_notifications.name
}
