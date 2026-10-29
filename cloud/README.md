### Commands for Testing Lambda Functions Locally
```bash
sam build
sam local invoke [function_name] --event [event_json]
```
**Example for the ground-station backend**
```bash
sam build
sam local invoke gsBackendFunction --event src/events/alert/wildfire_alert_body.json
```
### Commands for Testing API gateway
```bash
cd gs_backend
sam build
sam local start-api --port 3000
```
### Commands for Deploying Resources
```bash
sam build
sam deploy --parameter-overrides ParameterKey=LambdaExecutionRoleArn,ParameterValue=$ARN
```
