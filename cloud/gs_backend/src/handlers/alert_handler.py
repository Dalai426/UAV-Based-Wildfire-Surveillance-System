from configs.logger_config import logger
from models.detectionEvent import DetectionEvent
import json

def handle_alert(data):
    logger.info("Request Body: %s", data.get("body"))
    body = data.get("body") or "{}"
    event = json.loads(body)
    detection = DetectionEvent.model_validate(event)
    return {
        "ok": "3"
    }
