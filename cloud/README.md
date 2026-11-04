### Commands for Deploying Resources
API Gateway URL : https://69tln0isqi.execute-api.eu-north-1.amazonaws.com/prod/
### Commands for Testing Lambda Functions Locally
```bash
sam build
sam local invoke [function_name] --event [event_json]
```
**Examples for Invoking Backend Functions**
```bash
sam build
sam local invoke gsBackendFunction --event ./events/alert/wildfire_alert_body.json --env-vars env.json 
AWS_PROFILE=ce1-group-ds sam local invoke emailSubscriptionListener --event ./events/email_subscription/event_pre_auth.json --env-vars env.json 
```
### Commands for Testing API gateway
```bash
cd gs_backend
sam build
sam local start-api --port 3000
```
### Commands for Hot Reload
```bash
sam build
pip install watchdog
watchmedo shell-command --patterns="*.py" --recursive --command='rsync -rv --include="*/" --include="*.py" --exclude="*" src/ .aws-sam/build/gsBackendFunction/' src
FLASK_SKIP_DOTENV=1 AWS_PROFILE=ce1-group-ds sam local start-api --port 3000 --env-vars env.json --warm-containers EAGER
```
### Commands for Deploying Resources
```bash
sam build
sam deploy \
  --profile ce1-group-ds \
  --region eu-north-1 \
  --stack-name drone-surveillance-backend \
  --parameter-overrides \
    CloudBackendLambdaFunctionsRoleArn="arn:aws:iam::876875539928:role/drone-surveillance-system-gsBackend-lambda-role" \
    DashboardBackendLambdaFunctionsRoleArn="arn:aws:iam::876875539928:role/drone-surveillance-system-dashboardBackend-lambda-role" \
    DBHost="drone-surveillance-system-eu-north-1-db.cfog8cc8ilss.eu-north-1.rds.amazonaws.com" \
    DBUser="lambda_functions" \
    DBPassword="@@@" \
    PrivateSubnetIds="subnet-0eae5d27f27218b41,subnet-02018e9f5cd08e591" \
    LambdaSecurityGroupId="sg-0e0531599a6615747" \
    SnsTopicArn="arn:aws:sns:eu-north-1:876875539928:drone-surveillance-system-user-notifications" \
    UserPoolArn="arn:aws:cognito-idp:eu-north-1:876875539928:userpool/eu-north-1_yiBrC3S2O"
```
### How to call the API
```bash
curl --location \
  'https://3bs1n2thya.execute-api.eu-north-1.amazonaws.com/prod/ground-station/alert' \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  --aws-sigv4 "aws:amz:eu-north-1:execute-api" \
  -H "x-amz-security-token: $AWS_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVT-001",
    "ground_station_id": "GS-001",
    "confidence_percent": 98.0,
    "status": "active",
    "drone_id": "DRONE-001"
  }'
```