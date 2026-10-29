resource "aws_budgets_budget" "account_monthly" {
  name         = "account-monthly-cost-budget"
  budget_type  = "COST"
  limit_amount = "30"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_notification_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_notification_emails
  }
}

resource "aws_cloudwatch_log_group" "gs_lambda_logs" {
  name              = "/${var.project_name}/gs/logs"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_group" "dashboard_lambda_logs" {
  name              = "/${var.project_name}/dashboard/logs"
  retention_in_days = 90
}