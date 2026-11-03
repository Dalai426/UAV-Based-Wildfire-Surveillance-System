from shared_configs.logger_config import logger
import json
import boto3
import os
from shared_configs.logger_config import logger
import json
import urllib.request
import urllib.error

aws_region=os.environ["AWS_REGION"]

sts = boto3.client("sts", region_name=aws_region)
identity = sts.get_caller_identity()
logger.info("AWS Account: %s", identity["Account"])

# IF we use SES
logger.info("AWS_REGION: %s", aws_region)
ses = boto3.client(
    "sesv2",
    region_name=aws_region
)

def broadcast_emails_handler(data, event):
    emails=data.get("users_emails")
    broadcast_emails(emails)

def broadcast_emails(emails):
    for email in emails:
        print(email)
    return {
        "success":True
    }

def send_email(recipient, subject, message, html=False):
    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {
            "name": "Wildfire Surveillance System",
            "email": "wildfire.surveillance.alerts@gmail.com"
        },
        "to": [
            {"email": recipient}
        ],
        "subject": subject
    }

    if html:
        payload["htmlContent"] = message
    else:
        payload["textContent"] = message

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "accept": "application/json",
            "api-key": os.environ["BREVO_API_KEY"],
            "content-type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info("%s is informed about the wildfire", recipient)
            return {
                "success": True
            }

    except urllib.error.HTTPError as e:
        error_message = e.read().decode("utf-8")
        logger.error("Email sending failed: %s", error_message)
        return {
            "success": False,
            "error": e.read().decode("utf-8")
        }
