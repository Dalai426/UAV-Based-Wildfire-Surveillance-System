import asyncio
import os
import uuid
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
import base64
import binascii
from cryptography import x509

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

from app.models.evidence import CreateEvidence, Evidence
from app.models.events import CreateEventRequest, DetectionEvent
from app.models.auth import (
    HandshakeCompleteRequest,
    HandshakeInitResponse,
    HandshakeInitRequest,
)
from app.auth.handshake import (
    create_handshake,
    complete_handshake,
)
from app.auth.db import initialise_sentinel_database
from app.telemetry import TelemetryState, run_telemetry_forever

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

# Temporary detection values for manual testing.
TEST_EVENT_VALUES = {
    "ground_station_id": "test-ground-station",
    "ground_station": {},
    "confidence_percent": 95.0,
    "status": "detected",
    "coordinates": {
        "longitude": 9.92,
        "latitude": 57.05,
    },
    "drone": {
        "speed": 0.0,
        "altitude": 50.0,
        "battery_status": "100%",
    },
}


# Latest telemetry from the drone.
#
# Filled by the telemetry receiver (app/telemetry.py),
# read by GET /telemetry/latest.
telemetry_state = TelemetryState()

# The background task that runs the telemetry receiver.
#
# We keep a reference to it: asyncio only keeps weak references
# to tasks, so an unreferenced task could disappear mid-run.
telemetry_task = None


@app.on_event("startup")
def startup():
    """
    Initialize local persistent storage when Core starts.
    """

    init_db()
    initialise_sentinel_database()


@app.on_event("startup")
async def start_telemetry_receiver():
    """
    Start receiving the drone's telemetry in the background.

    It runs as an asyncio task next to the API, so the API stays
    responsive while telemetry keeps arriving.
    """

    global telemetry_task

    telemetry_task = asyncio.create_task(run_telemetry_forever(telemetry_state))


@app.on_event("shutdown")
async def stop_telemetry_receiver():
    """
    Stop the telemetry receiver when the Core shuts down.
    """

    if telemetry_task is not None:
        telemetry_task.cancel()


async def save_evidence(request: CreateEvidence) -> Evidence:
    """Create evidence and report failures with IDs for retry."""
    try:
        # Download the requested footage and save the video
        # and metadata. Returns a completed Evidence model.
        evidence = await create_evidence(request)

        # Store the file details and mark this evidence ready.
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
    if request.start.tzinfo is None or request.end.tzinfo is None:
        raise HTTPException(
            status_code=400,
            detail="timestamps must include timezone",
        )

    if request.end <= request.start:
        raise HTTPException(
            status_code=400,
            detail="end must be after start",
        )

    duration = (request.end - request.start).total_seconds()

    # Limit the requested interval; output duration is not measured here.
    if duration > MAX_EVENT_EVIDENCE_SECONDS:
        raise HTTPException(
            status_code=400,
            detail=f"evidence cannot exceed {MAX_EVENT_EVIDENCE_SECONDS} seconds",
        )

    # Generate the permanent event identity once.
    event_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())

    # Persist the event before attempting evidence creation.
    # If MediaMTX or evidence creation fails, the event is
    # still known and can be retried with the same event_id.
    cloud_event = DetectionEvent.model_validate(
        {
            **TEST_EVENT_VALUES,
            "event_id": event_id,
            "drone_id": DRONE_ID,
            "detection_time": datetime.now(timezone.utc),
            "footage_duration": duration,
        }
    )

    insert_event(
        event_id=event_id,
        drone_id=DRONE_ID,
        cloud_payload_json=cloud_event.model_dump_json(),
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
        "status": "ready",
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
        "status": "ready",
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


@app.get("/telemetry/latest")
def read_latest_telemetry():
    """
    The drone's latest telemetry: position, altitude, speed,
    attitude, battery, flight mode and the link status.
    """

    return {
        "drone_id": DRONE_ID,
        **telemetry_state.snapshot(),
    }


@app.post(
    "/sentinel/handshake/init",
    response_model=HandshakeInitResponse,
)
async def initialise_handshake(request: HandshakeInitRequest):

    nonce_drone = decode_base64(
        request.nonce_drone,
        "nonce_drone",
    )

    if len(nonce_drone) != 32:
        raise HTTPException(
            status_code=400,
            detail="Drone nonce must be 32 bytes",
        )

    try:
        drone_cert_pem = request.drone_certificate.encode("ascii")

        # Validate that the supplied data is a PEM certificate.
        x509.load_pem_x509_certificate(drone_cert_pem)

        response = create_handshake(
            drone_id=request.drone_id,
            nonce_drone=nonce_drone,
            drone_cert_pem=drone_cert_pem,
        )

        return response

    except ValueError as exc:
        print(exc)
        raise HTTPException(
            status_code=401,
            detail="Drone authentication failed",
        ) from exc


@app.post("/sentinel/handshake/complete")
async def finish_handshake(request: HandshakeCompleteRequest):
    try:
        complete_handshake(
            handshake_id=request.handshake_id,
            drone_confirmation=request.confirmation,
        )
        return {
            "status": "authenticated",
            "message": "SENTINEL session established",
        }

    except ValueError as exc:
        print(exc)
        raise HTTPException(
            status_code=401,
            detail="Session key confirmation failed",
        ) from exc


def decode_base64(value: str, field_name: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Base64 value: {field_name}",
        ) from exc
