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

output "credential_provider_url" {
  value       = data.aws_iot_endpoint.credential_provider.endpoint_address
  description = "The HTTPS mTLS endpoint your devices will query for AWS tokens"
}

# A role alias is an alternate data model that points to the IAM role. 
# An AWS IoT credentials provider request must include a role alias to 
# indicate which IAM role to assume in order to obtain temporary credentials from the AWS Security Token Service (AWS STS)
output "ground_station_role_alias" {
  value       = aws_iot_role_alias.iot_core_role_alias.alias
  description = "The Roles Alias for Ground Stations"
}
