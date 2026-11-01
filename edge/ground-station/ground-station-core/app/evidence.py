import hashlib
import os
from datetime import timezone
from pathlib import Path

import httpx

from app.schemas import CreateEvidence, Evidence


# Internal MediaMTX playback API URL.
MEDIAMTX_URL = os.environ["MEDIAMTX_PLAYBACK_URL"]

# Permanent evidence directory.
EVIDENCE_DIR = Path(os.environ["EVIDENCE_DIR"])

# Keep partial downloads separate from completed evidence files.
TEMP_DIR = EVIDENCE_DIR / ".tmp"

EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


async def create_evidence(request: CreateEvidence) -> Evidence:
    """
    Retrieve a recorded interval from MediaMTX and store it
    as permanent evidence.

    Workflow:

        MediaMTX recording
              ↓
        temporary MP4
              ↓
        calculate SHA-256
              ↓
        move to final evidence directory
              ↓
        create metadata.json
    """

    # Store the requested interval in UTC; these are not measured video times.
    start_utc = request.requested_start.astimezone(timezone.utc)
    end_utc = request.requested_end.astimezone(timezone.utc)

    duration = (end_utc - start_utc).total_seconds()

    # Group clips by the requested start date in UTC.
    event_date = start_utc.date().isoformat()

    # Example:
    #
    # 2026-10-30/
    # └── <evidence-id>/
    # Each evidence clip gets its own directory.
    relative_directory = Path(event_date) / request.evidence_id
    evidence_directory = EVIDENCE_DIR / relative_directory

    # The evidence directory supplies the unique identity.
    video_name = "video.mp4"

    video_path = evidence_directory / video_name
    metadata_path = evidence_directory / "metadata.json"

    # Reuse completed evidence on retries. This validates the metadata
    # structure but does not recheck the video's hash or prevent concurrent retries.
    if video_path.exists() and metadata_path.exists():
        return Evidence.model_validate_json(metadata_path.read_text())

    # Download into .tmp first.
    #
    # This prevents partially downloaded videos from appearing
    # inside the final evidence directory.
    temp_path = TEMP_DIR / f"{request.evidence_id}.mp4"

    # Parameters expected by MediaMTX's playback API.
    params = {
        "path": request.stream_key,
        "start": start_utc.isoformat(),
        "duration": duration,
        "format": "mp4",
    }

    # SHA-256 lets us later verify that the evidence file
    # has not changed or become corrupted.
    hasher = hashlib.sha256()

    try:
        async with httpx.AsyncClient(timeout=10) as client:

            # Stream the response rather than loading the entire
            # evidence file into RAM.
            async with client.stream(
                "GET",
                f"{MEDIAMTX_URL}/get",
                params=params,
            ) as response:

                # Raise an exception for HTTP errors.
                response.raise_for_status()

                with temp_path.open("wb") as file:

                    async for chunk in response.aiter_bytes():

                        # Write each network chunk directly to disk.
                        file.write(chunk)

                        # Calculate the integrity hash at the same time.
                        hasher.update(chunk)

                    # Push Python's buffered data to the OS.
                    file.flush()

                    # Ask the OS to flush the file to disk.
                    os.fsync(file.fileno())

        # Only create the final directory after MediaMTX
        # successfully returned the complete video.
        evidence_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Atomic rename from temporary file to final evidence file.
        os.replace(
            temp_path,
            video_path,
        )

        # Metadata stored alongside the video.
        evidence = Evidence(
            evidence_id=request.evidence_id,
            event_id=request.event_id,
            drone_id=request.drone_id,
            stream_key=request.stream_key,

            requested_start=start_utc,
            requested_end=end_utc,

            # Store a relative path instead of a container-specific
            # absolute path such as /data/evidence/...
            relative_path=str(relative_directory / video_name),

            size_bytes=video_path.stat().st_size,

            # Integrity fingerprint of the actual evidence bytes.
            sha256=hasher.hexdigest(),
        )

        # Write metadata through a temporary file as well.
        temp_metadata = evidence_directory / ".metadata.tmp"

        temp_metadata.write_text(
            evidence.model_dump_json(indent=2)
        )

        # Expose metadata.json only when completely written.
        os.replace(
            temp_metadata,
            metadata_path,
        )

        return evidence

    except Exception:

        # Remove a partial download if anything failed.
        if temp_path.exists():
            temp_path.unlink()

        # Let the API workflow update the evidence record and report the failure.
        raise

