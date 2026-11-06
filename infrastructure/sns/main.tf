
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
