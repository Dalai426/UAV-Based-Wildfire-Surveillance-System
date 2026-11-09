# main.py
import os
import logging
import time
from datetime import datetime, timedelta, timezone

import ssl
import httpx
import sqlite3
import threading


from app.db import (
    get_pending_events,
    record_event_attempt,
    mark_event_sent,
    record_event_failure
)

from app.api import send_event
from app.auth import CredentialsManager


from app.retry import (
    parse_retry_after,
    retry_delay,
)


CLOUD_API_BASE_URL = os.environ["CLOUD_API_BASE_URL"]
ALERT_URL = f"{CLOUD_API_BASE_URL}/ground-station/alert"
AWS_REGION = os.environ["AWS_REGION"]

EVENT_CHECK_INTERVAL_SECONDS = 1
DATABASE_RETRY_SECONDS = 1

# Maximum delivery cycles, including the initial attempt.
# TODO: Review this limit once cloud duplicate handling is fixed.
MAX_EVENT_ATTEMPTS = 10


def handle_pending_events(
    api_client: httpx.Client,
    credentials_manager: CredentialsManager,
) -> None:
    
    events = get_pending_events(max_attempts=MAX_EVENT_ATTEMPTS)

    if not events:
        logging.info("No pending events to send")
        return

    logging.info("Sending %s pending events", len(events))
    for event in events:
        event_id = event["event_id"]
        payload_json = event["cloud_payload_json"]
        attempt = event["cloud_attempts"] + 1

        credentials = credentials_manager.get_credentials()

        # Persist a fallback retry time before sending.
        fallback_delay = retry_delay(attempt)

        next_attempt_at = (
            datetime.now(timezone.utc) + fallback_delay
        ).isoformat()

        # Save the attempt and a fallback retry time before sending.
        # If we crash before recording the outcome, the event remains retryable.
        record_event_attempt(
            event_id=event_id,
            next_attempt_at=next_attempt_at,
        )

        try:
            # Allow one immediate retry if AWS rejects expired credentials.
            # Both sends count as the single delivery cycle already saved in SQLite.
            for send_attempt in range(2):
                try:
                    send_event(
                        client=api_client,
                        api_url=ALERT_URL,
                        region=AWS_REGION,
                        credentials=credentials,
                        payload_json=payload_json,
                    )
                    break  # Successfully sent.

                except httpx.HTTPStatusError as error:

                    expired = (
                        error.response.status_code == 403
                        and error.response.headers.get("x-amzn-errortype")
                        == "ExpiredTokenException"
                    )

                    # Only the first send can trigger immediate recovery.
                    if not expired or send_attempt == 1:
                        raise

                    credentials_manager.invalidate_credentials(credentials)
                    credentials = credentials_manager.get_credentials()
            
        except httpx.HTTPStatusError as error:
            # TODO: Cloud currently returns 500 for existing event IDs.
            # We cannot distinguish duplicates from temporary server failures,
            # so both are retried until the attempt limit is reached.

            response = error.response
            delay = retry_delay(
                attempt,
                status_code=response.status_code,
                retry_after=parse_retry_after(
                    response.headers.get("Retry-After")
                ),
            )
            last_error = str(error)    

        except httpx.RequestError as error:
            delay = retry_delay(attempt)
            last_error = str(error)

        else:
            logging.info("Event %s sent successfully", event_id)
            mark_event_sent(event_id)
            continue

        # Both failure handlers reach this shared scheduling block.
        next_attempt_at = (
            datetime.now(timezone.utc) + delay
        ).isoformat()

        if attempt >= MAX_EVENT_ATTEMPTS:
            logging.error(
                "Event %s exhausted %s delivery attempts; "
                "automatic retries stopped; last error: %s",
                event_id,
                attempt,
                last_error,
            )
        else:
            logging.warning(
                "Event %s failed: %s; retry scheduled for %s",
                event_id,
                last_error,
                next_attempt_at,
            )

        # Schedule this event for a later retry, then continue with the next event.
        # A network or API failure should not prevent other events from being sent.
        record_event_failure(
            event_id=event_id,
            next_attempt_at=next_attempt_at,
            last_error=last_error,
        )


def run_event_worker(api_client, credentials_manager):
    while True:
        try:
            handle_pending_events(
                api_client,
                credentials_manager,
            )
        # A database error stops the current batch because delivery state
        # could not be read or saved reliably. Pause before querying again
        except sqlite3.Error:
            logging.exception(
                "Event database operation failed; retrying in %s seconds", 
                DATABASE_RETRY_SECONDS
            )
            time.sleep(DATABASE_RETRY_SECONDS)
        else:
            # Wait before checking for more events.
            time.sleep(EVENT_CHECK_INTERVAL_SECONDS)

