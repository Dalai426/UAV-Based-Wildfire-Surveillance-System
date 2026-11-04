from shared_configs.logger_config import logger
import boto3
import os

cognito_client = boto3.client('cognito-idp')
sns = boto3.client("sns", region_name="eu-north-1")
SNS_TOPIC_ARN=os.environ["SNS_TOPIC_ARN"]
logger.info("The ARN of SNS service for sending emails : %s", SNS_TOPIC_ARN)

def subscribe_email(email):
    logger.info(email)
    response = sns.subscribe(
        TopicArn=SNS_TOPIC_ARN,
        Protocol="email",
        Endpoint=email
    )
    logger.info(response)
    return response["SubscriptionArn"]

def handler(event, context):
    logger.info(event)
    user_pool_id = event.get('userPoolId') 
    username = event.get('userName')
    userInfo=event.get("request",{}).get("userAttributes",{})
    # subscribed
    email_subscribed = userInfo.get("custom:event_subscribed")
    logger.info("Email subscribed: %s", email_subscribed)
    if email_subscribed != "subscribed":
        try:
            sub_res=subscribe_email(userInfo.get("email"))
            if sub_res == "pending confirmation":
                event_subscribed = "pending"
            else:
                event_subscribed = "subscribed"
            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=username,
                UserAttributes=[
                {
                    "Name": "custom:event_subscribed",
                    "Value": event_subscribed
                }
            ])
            event["request"]["userAttributes"]["custom:event_subscribed"] = event_subscribed
        except Exception as exc:
            logger.exception(
                "Failed to subscribe user email or update Cognito attribute: %s",
                exc
            )
    return event
    
    
    


