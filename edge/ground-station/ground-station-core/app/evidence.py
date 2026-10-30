import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx


# Internal MediaMTX playback API URL.
MEDIAMTX_URL = os.environ["MEDIAMTX_PLAYBACK_URL"]

# Permanent evidence directory.
EVIDENCE_DIR = Path(os.environ["EVIDENCE_DIR"])

# Temporary files are kept separately so incomplete evidence
# never appears as a finished event.
TEMP_DIR = EVIDENCE_DIR / ".tmp"

EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


async def create_evidence(
    event_id: str,
    drone_id: str,
    stream_key: str,
    start: datetime,
    end: datetime,
):
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
        move to final event directory
              ↓
        create metadata.json
    """

    # Normalize all stored evidence times to UTC.
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)

    duration = (end_utc - start_utc).total_seconds()

    # Organize evidence by the date when the event started.
    event_date = start_utc.date().isoformat()

    # Example:
    #
    # 2026-10-30/
    # └── <event-id>/
    relative_directory = Path(event_date) / event_id
    event_directory = EVIDENCE_DIR / relative_directory

    # Use the stream key as the video filename.
    video_name = f"{stream_key}.mp4"

    video_path = event_directory / video_name
    metadata_path = event_directory / "metadata.json"

    # Make retries idempotent.
    #
    # If this event's evidence already exists, don't download
    # or create it again.
    if video_path.exists() and metadata_path.exists():
        return json.loads(metadata_path.read_text())

    # Download into .tmp first.
    #
    # This prevents partially downloaded videos from appearing
    # inside the final evidence directory.
    temp_path = TEMP_DIR / f"{event_id}-{stream_key}.mp4"

    # Parameters expected by MediaMTX's playback API.
    params = {
        "path": stream_key,
        "start": start_utc.isoformat(),
        "duration": duration,
        "format": "mp4",
    }

    # SHA-256 lets us later verify that the evidence file
    # has not changed or become corrupted.
    hasher = hashlib.sha256()

    try:
        async with httpx.AsyncClient(timeout=None) as client:

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
        event_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Atomic rename from temporary file to final evidence file.
        os.replace(
            temp_path,
            video_path,
        )

        # Metadata stored alongside the video.
        metadata = {
            "event_id": event_id,
            "drone_id": drone_id,
            "stream_key": stream_key,

            "start": start_utc.isoformat(),
            "end": end_utc.isoformat(),

            "video_file": video_name,

            # Store a relative path instead of a container-specific
            # absolute path such as /data/evidence/...
            "relative_path": str(
                relative_directory / video_name
            ),

            "size_bytes": video_path.stat().st_size,

            # Integrity fingerprint of the actual evidence bytes.
            "sha256": hasher.hexdigest(),

            "status": "ready",
        }

        # Write metadata through a temporary file as well.
        temp_metadata = event_directory / ".metadata.tmp"

        temp_metadata.write_text(
            json.dumps(
                metadata,
                indent=2,
            )
        )

        # Expose metadata.json only when completely written.
        os.replace(
            temp_metadata,
            metadata_path,
        )

        return metadata

    except Exception:

        # Remove a partial download if anything failed.
        if temp_path.exists():
            temp_path.unlink()

        # Let the Core decide how the event should be marked/retried.
        raise

