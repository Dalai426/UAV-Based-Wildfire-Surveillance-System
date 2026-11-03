output "email_broadcast_queue_url" {
  value = aws_sqs_queue.broadcast_queue.url
}

output "email_broadcast_queue_arn" {
  value = aws_sqs_queue.broadcast_queue.arn
}

output "consume_sqs_role_policy_arn" {
  value = aws_iam_policy.sqs_consume_policy.arn
}