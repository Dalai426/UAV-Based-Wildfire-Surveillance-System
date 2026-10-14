output "db_endpoint" {
  description = "PostgreSQL connection endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "db_address" {
  description = "PostgreSQL hostname"
  value       = aws_db_instance.postgres.address
}

output "db_port" {
  description = "PostgreSQL port"
  value       = aws_db_instance.postgres.port
}

output "db_name" {
  description = "PostgreSQL database name"
  value       = aws_db_instance.postgres.db_name
}

output "db_username" {
  description = "PostgreSQL master username"
  value       = aws_db_instance.postgres.username
}

output "db_secret_arn" {
  description = "Secrets Manager ARN for the master credentials"
  value       = aws_db_instance.postgres.master_user_secret[0].secret_arn
}