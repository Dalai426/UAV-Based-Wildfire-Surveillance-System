import json
from configs.logger_config import logger
from configs.async_loop_config import loop
from handlers.incident_handler import list_incidents, close_incident
from models.errors import NotFoundError, ConflictError
from pydantic import ValidationError
from configs.db_config import get_db_pool

# The path is written the way template.yaml declares it
routes = {
    ("GET", "/incidents"): list_incidents,
    ("POST", "/incidents/{gs_event_id}/close"): close_incident,
}
pool=loop.run_until_complete(get_db_pool())

def response(status_code, data):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(data)
    }

def handler(event, context):
    logger.info("Dashboard Backend Function Called")
    method = event.get("httpMethod", "")
    # "resource" is the route from template.yaml, "path" has the real id in it
    path = (event.get("resource") or event.get("path", "")).rstrip("/") or "/"
    route_handler = routes.get((method, path))
    if route_handler is None:
        return response(404, {"error": "Route not found"})
    try:
        resp = loop.run_until_complete(
            route_handler(event)
        )
        return response(200, resp)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON request body")
        return response(400, {"error": "Invalid JSON body"})
    except ValidationError as exc:
        return response(400, {"error": "Invalid Input", "elaboration": json.loads(exc.json(include_url=False))})
    except NotFoundError as exc:
        return response(404, {"error": str(exc)})
    except ConflictError as exc:
        return response(409, {"error": str(exc)})
    except Exception as exc:
        logger.exception("Failed to process request")
        return response(
            500,
            {"error": str(exc) or "Internal server error"}
        )
