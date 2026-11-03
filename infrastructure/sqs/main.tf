resource "aws_sqs_queue" "broadcast_queue" {
  name                       = "${var.project_name}-broadcast-email-queue"
  visibility_timeout_seconds = 60 * 3 # 3 minutes. It determines how long a message stays invisible after a consumer receives it.
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true
}

resource "aws_iam_policy" "sqs_consume_policy" {
  name = "sqs-consume-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:SendMessage"
      ]
      Resource = [
        aws_sqs_queue.broadcast_queue.arn
      ]
    }]
  })
}