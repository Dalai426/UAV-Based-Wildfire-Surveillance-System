output "credential_provider_url" {
  value       = module.permissions.credential_provider_url
  description = "IoT credentials provider endpoint"
}

output "ground_station_role_alias" {
  value       = module.permissions.ground_station_role_alias
  description = "The Roles Alias for Ground Station"
}

output "lambda_role_arn" {
  value       = module.permissions.lambda_role_arn
  description = "The Role ARNs For Lambda Functions"
}

output "db_endpoint" {
  value       = module.database.db_endpoint
  description = "The Database Endpoint"
}

output "sns_topic_arn" {
  value       = module.sns.sns_topic_arn
  description = "The SNS Topic ARN"
}
