import json
from pathlib import Path

body = json.loads(
    Path("events/alert/wildfire_alert_body.json").read_text()
)

event = {
    "httpMethod": "POST",
    "path": "/ground-station/alert",
    "headers": {
        "Content-Type": "application/json"
    },
    "body": json.dumps(body),
    "isBase64Encoded": False
}

print(event)