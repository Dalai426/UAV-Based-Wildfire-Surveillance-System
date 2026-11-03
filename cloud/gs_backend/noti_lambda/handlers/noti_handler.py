import os
import json
import uuid
import boto3
from shared_configs.logger_config import logger
from handlers.email_broadcaster import broadcast_emails


lambda_client = boto3.client("lambda")
is_local = os.environ.get("AWS_SAM_LOCAL") == "true"

def divide_into_batches(data, batch_size):
    if batch_size <= 0:
        raise ValueError("Batch size must be greater than zero")
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

def invoke_notification_batch(data, batch, index, message_id):
    payload = {
        **data,
        "users_emails": batch
    }
    lambda_event = {
        "Records": [
            {
                "messageId": str(uuid.uuid4()),
                "body": json.dumps({
                    "data": payload,
                    "action": "broadCastEmail"
                })
            }
        ]
    }
    response = lambda_client.invoke(
        FunctionName=os.environ.get("AWS_LAMBDA_FUNCTION_NAME"),
        InvocationType="Event",
        Payload=json.dumps(lambda_event).encode("utf-8")
    )
    if response["StatusCode"] != 202:
        raise RuntimeError(
            f"Failed to invoke Lambda for batch {index}. "
            f"Status: {response['StatusCode']}"
        )
    logger.info(
        "Successfully submitted batch %s for asynchronous processing. "
        "Parent message ID: %s",
        index,
        message_id
    )


def noti_events_handler(data, event):
    message_id=event.get("message_id")
    emails = ["gadalai426@gmail.com", "dgantu26@student.aau.dk"]
    batch_size = 1
    if not emails:
        logger.warning("No users available for notification")
        return {"success": True, "message": "No users to notify"}
    
    if len(emails) <= batch_size or is_local is True:
        logger.info("Sending emails directly to %s users", len(emails))
        broadcast_emails(emails)
    else:
        batches = list(divide_into_batches(emails, batch_size))
        logger.info("Created %s user batches", len(batches))
        for index, batch in enumerate(batches, start=1):
            logger.info(
                "Submitting batch %s containing %s users",
                index,
                len(batch)
            )
            invoke_notification_batch(
                data=data,
                batch=batch,
                index=index,
                message_id=message_id
            )
    return {"success": True}