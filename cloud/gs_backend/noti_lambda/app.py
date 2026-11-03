import json
from shared_configs.logger_config import logger
from handlers.noti_handler  import noti_events_handler
from handlers.email_broadcaster  import broadcast_emails

event_dict = {
    "notifyUsers": noti_events_handler,
    "broadCastEmail": broadcast_emails,
}

def handler(event, context):
    record = event["Records"][0]
    body = json.loads(record.get("body") or "{}")
    action = body.get("action")
    logger.info("Sending Email Function Is Called To Process %s", action)
    message_handler = event_dict.get(action)
    if message_handler is None:
        logger.warning("No handler found for action: %s", action)
        raise ValueError(f"No handler found for action: {action}")
    message_handler(body.get('data', {}), event)
    return {}
    
    
    


