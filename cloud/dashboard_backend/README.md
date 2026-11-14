### Commands for Deploying Resources
```bash
aws login --profile ce1-group-ds
sam build
sam deploy \
  --profile ce1-group-ds \
  --region eu-north-1 \
  --stack-name drone-surveillance-dashboard-backend \
  --parameter-overrides \
    DashboardBackendLambdaFunctionsRoleArn="" \
    DBHost="" \
    DBUser="lambda_functions" \
    DBPassword="" \
    PrivateSubnetIds="subnet-0eae5d27f27218b41,subnet-02018e9f5cd08e591" \
    LambdaSecurityGroupId="sg-0e0531599a6615747" \
    UserPoolArn="arn:aws:cognito-idp:eu-north-1:876875539928:userpool/eu-north-1_yiBrC3S2O"
```