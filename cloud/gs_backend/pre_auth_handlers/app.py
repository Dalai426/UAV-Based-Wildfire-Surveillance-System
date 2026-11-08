from shared_configs.logger_config import logger
import boto3
import os
import json

cognito_client = boto3.client("cognito-idp")
sns = boto3.client("sns", region_name="eu-north-1")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
logger.info("The ARN of SNS service for sending emails : %s", SNS_TOPIC_ARN)


def subscribe_email(email):
    response = sns.subscribe(
        TopicArn=SNS_TOPIC_ARN,
        Protocol="email",
        Endpoint=email,
        ReturnSubscriptionArn=True,
    )
    logger.info(response)

    logger.info("Subscription requested: %s", response)
    return response["SubscriptionArn"]


def is_email_subscribed(subscription_arn):
    try:
        subscription = sns.get_subscription_attributes(SubscriptionArn=subscription_arn)
        logger.info("------")
        logger.info(subscription)
        logger.info("------")
        if subscription is None:
            return False
        else:
            attributes = subscription.get("Attributes", {})
            pending = attributes.get("PendingConfirmation", "true")
            return pending.lower() == "false"
    except Exception as exc:
        logger.error(exc)
        # if not found, it is not subscribed
        return False


def handler(event, context):
    logger.info(event)
    user_pool_id = event.get("userPoolId")
    username = event.get("userName")
    userInfo = event.get("request", {}).get("userAttributes", {})

    email_sub_arn = userInfo.get("custom:email_sub_arn")
    logger.info("Email subscribed: %s", email_sub_arn)
    logger.info(email_sub_arn)
    try:
        event["request"]["userAttributes"]["custom:event_subscribed"] = "subscribed"
        if email_sub_arn and str(email_sub_arn).startswith("arn:") == True:
            if not is_email_subscribed(email_sub_arn):
                resp = subscribe_email(userInfo.get("email"))
                cognito_client.admin_update_user_attributes(
                    UserPoolId=user_pool_id,
                    Username=username,
                    UserAttributes=[
                        {"Name": "custom:email_sub_arn", "Value": f"{resp}"}
                    ],
                )
                event["request"]["userAttributes"][
                    "custom:event_subscribed"
                ] = "pending"
        else:
            resp = subscribe_email(userInfo.get("email"))
            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=username,
                UserAttributes=[{"Name": "custom:email_sub_arn", "Value": f"{resp}"}],
            )
            event["request"]["userAttributes"]["custom:event_subscribed"] = "pending"
    except Exception as exc:
        logger.exception(
            "Failed to subscribe user email or update Cognito attribute: %s", exc
        )
    return event
