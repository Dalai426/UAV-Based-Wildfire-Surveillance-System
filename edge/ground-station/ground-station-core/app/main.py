import os
import uuid
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.db import (
    create_event as insert_event,
    get_event,
    init_db,
    mark_evidence_failed,
    mark_evidence_ready,
)

from app.evidence import create_evidence


# Main Ground Station Core HTTP API.
app = FastAPI(
    title="Ground Station Core",
)


# Temporary MVP configuration.
#
# Later these will be determined dynamically from authenticated
# drone sessions instead of environment variables.
DRONE_ID = os.environ["DRONE_ID"]
STREAM_KEY = os.environ["STREAM_KEY"]


class CreateEventRequest(BaseModel):
    """
    Manual event request used during development.

    Later the detection logic will create these automatically
    after the AI prediction has been confirmed.
    """

    start: datetime
    end: datetime


@app.on_event("startup")
def startup():
    """
    Initialize local persistent storage when Core starts.
    """

    init_db()


async def build_evidence(event: dict):
    """
    Create evidence for an event that already exists in SQLite.

    This function is shared by:
    - initial event creation
    - evidence retries
    """

    start = datetime.fromisoformat(
        event["start_time"]
    )

    end = datetime.fromisoformat(
        event["end_time"]
    )

    try:
        evidence = await create_evidence(
            event_id=event["event_id"],
            drone_id=event["drone_id"],
            stream_key=event["stream_key"],
            start=start,
            end=end,
        )

        # Evidence has been successfully created.
        # Persist its location and integrity information.
        mark_evidence_ready(
            event_id=event["event_id"],
            relative_path=evidence["relative_path"],
            sha256=evidence["sha256"],
            size_bytes=evidence["size_bytes"],
        )

        return evidence

    except httpx.HTTPError as exc:

        # Keep the event but remember that evidence generation failed.
        mark_evidence_failed(
            event["event_id"]
        )

        raise HTTPException(
            status_code=502,
            detail=f"Evidence creation failed: {exc}",
        )


@app.post("/events")
async def create_event(
    request: CreateEventRequest,
):
    """
    Create a new wildfire event and its evidence.

    Currently called manually for testing.

    Later this endpoint's logic will instead be triggered by
    the detection/event-confirmation logic inside the Core.
    """

    # Require timezone-aware timestamps.
    #
    # Example:
    # 2026-10-30T10:00:00+00:00
    if (
        request.start.tzinfo is None
        or request.end.tzinfo is None
    ):
        raise HTTPException(
            status_code=400,
            detail="timestamps must include timezone",
        )

    if request.end <= request.start:
        raise HTTPException(
            status_code=400,
            detail="end must be after start",
        )

    duration = (
        request.end - request.start
    ).total_seconds()

    # Current system requirement:
    # final evidence clips are at most 20 seconds.
    if duration > 20:
        raise HTTPException(
            status_code=400,
            detail="evidence cannot exceed 20 seconds",
        )

    # Generate the permanent event identity once.
    event_id = str(uuid.uuid4())

    # IMPORTANT:
    #
    # Persist the event before attempting evidence creation.
    #
    # If MediaMTX or evidence creation fails, the event is
    # still known and can be retried with the same event_id.
    insert_event(
        event_id=event_id,
        drone_id=DRONE_ID,
        stream_key=STREAM_KEY,
        start_time=request.start.isoformat(),
        end_time=request.end.isoformat(),
    )

    event = get_event(event_id)

    # Retrieve and persist the corresponding video evidence.
    evidence = await build_evidence(event)

    return {
        "event_id": event_id,
        "status": "READY",
        "evidence": evidence,
    }


@app.post("/events/{event_id}/evidence")
async def retry_evidence(
    event_id: str,
):
    """
    Retry evidence creation for an existing event.

    This deliberately does NOT generate a new event_id.
    """

    event = get_event(event_id)

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="event not found",
        )

    evidence = await build_evidence(event)

    return {
        "event_id": event_id,
        "status": "READY",
        "evidence": evidence,
    }


@app.get("/events/{event_id}")
def read_event(
    event_id: str,
):
    """
    Inspect the local state of an event.
    """

    event = get_event(event_id)

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="event not found",
        )

    return event
