from models.detectionEvent import DetectionEvent
from datetime import datetime, timezone

def get_email_body(event:DetectionEvent):
    detected_at = event.detection_time.strftime("%d %B %Y, %H:%M:%S UTC")
    message = f"""
🔥 WILDFIRE DETECTION ALERT
━━━━━━━━━━━━━━━━━━━━━━━━━━

A new potential wildfire has been detected by the Drone Surveillance System.

DETECTION DETAILS

• Detection ID: {event.event_id}
• Confidence: {event.confidence_percent}%
• Detected At: {detected_at}

⚠️ ACTION REQUIRED

Please review the detection and assess the situation as soon as possible.

Access to the surveillance dashboard through this link: 

━━━━━━━━━━━━━━━━━━━━━━━━━━
Drone Surveillance System

This is an automated notification. Please do not reply to this email.
"""
    return message