import json
from configs.logger_config import logger
from handlers.alert_handler import handle_alert
from pydantic import ValidationError

routes = {
    ("POST", "/ground-station/alert"): handle_alert,
}

def response(status_code, data):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(data)
    }

def handler(event, context):
    logger.info("Cloud Backend Function Called")
    method = event.get("httpMethod", "")
    path = event.get("path", "").rstrip("/") or "/"
    route_handler = routes.get((method, path))
    if route_handler is None:
        return response(404, {"error": "Route not found"})
    try:
        resp = route_handler(event)
        return response(200, resp)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON request body")
        return response(400, {"error": "Invalid JSON body"})
    except ValidationError as exc:
        return response(400, {"error": "Invalid Input", "elaboration": exc.errors(include_url=False)})
    except Exception as exc:
        logger.exception("Failed to process request")
        return response(
            500,
            {"error": str(exc) or "Internal server error"}
        )

