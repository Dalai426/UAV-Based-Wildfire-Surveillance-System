import os
import uuid

import httpx
from fastapi import FastAPI, HTTPException

from pydantic import ValidationError


from app.db import (
    insert_event,
    insert_evidence,
    get_event,
    get_evidence,
    list_event_evidence,
    init_db,
    mark_evidence_failed,
    mark_evidence_ready,
)

from app.evidence import create_evidence
from app.schemas import CreateEventRequest, CreateEvidence, Evidence


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

# Maximum requested interval for event evidence, in seconds.
MAX_EVENT_EVIDENCE_SECONDS = 20


@app.on_event("startup")
def startup():
    """
    Initialize local persistent storage when Core starts.
    """

    init_db()



async def save_evidence(request: CreateEvidence) -> Evidence:
    """Create evidence and report failures with IDs for retry."""
    try:
        # Download the requested footage and save the video
        # and metadata. Returns a completed Evidence model.
        evidence = await create_evidence(request)

        # Store the file details and mark this evidence READY.
        mark_evidence_ready(evidence)
        return evidence

    except httpx.HTTPError as exc:
        # MediaMTX was unavailable or rejected the request.
        mark_evidence_failed(request.evidence_id)

        raise HTTPException(
            status_code=502,
            detail={
                "message": "MediaMTX evidence retrieval failed",
                "event_id": request.event_id,
                "evidence_id": request.evidence_id,
            },
        ) from exc

    except (OSError, ValidationError) as exc:
        # Saving files or validating evidence metadata failed.
        mark_evidence_failed(request.evidence_id)

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Evidence storage or validation failed",
                "event_id": request.event_id,
                "evidence_id": request.evidence_id,
            },
        ) from exc


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

    # Limit the requested interval; output duration is not measured here.
    if duration > MAX_EVENT_EVIDENCE_SECONDS:
        raise HTTPException(
            status_code=400,
            detail=f"evidence cannot exceed {MAX_EVENT_EVIDENCE_SECONDS} seconds",
        )

    # Generate the permanent event identity once.
    event_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())

    # IMPORTANT:
    #
    # Persist the event before attempting evidence creation.
    #
    # If MediaMTX or evidence creation fails, the event is
    # still known and can be retried with the same event_id.
    insert_event(
        event_id=event_id,
        drone_id=DRONE_ID,
    )

    # Save the pending evidence record.
    evidence_request = CreateEvidence(
        evidence_id=evidence_id,
        event_id=event_id,
        drone_id=DRONE_ID,
        stream_key=STREAM_KEY,
        requested_start=request.start,
        requested_end=request.end,
    )

    # Create a separate pending record for the evidence attempt.
    insert_evidence(evidence_request)

    # Retrieve and persist the corresponding video evidence.
    evidence = await save_evidence(evidence_request)

    return {
        "event_id": event_id,
        "status": "READY",
        "evidence": evidence,
    }


@app.post("/evidence/{evidence_id}/retry")
async def retry_evidence(evidence_id: str):
    # Load the original inputs so retries reuse the same identity,
    # source stream, and requested interval.
    record = get_evidence(evidence_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="evidence not found",
        )

    # Convert stored inputs into the request model.
    # Pydantic parses the saved timestamp strings as datetimes.
    evidence_request = CreateEvidence(
        evidence_id=record["evidence_id"],
        event_id=record["event_id"],
        drone_id=record["drone_id"],
        stream_key=record["stream_key"],
        requested_start=record["requested_start"],
        requested_end=record["requested_end"],
    )

    # Reuse the creation workflow and update evidence state.
    evidence = await save_evidence(evidence_request)

    return {
        "event_id": evidence.event_id,
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

    # Include each clip's creation state and file details.
    return {
        **event,
        "evidence": list_event_evidence(event_id),
    }
