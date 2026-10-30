import os
import sqlite3
from datetime import datetime, timezone


# Location of the SQLite database inside the container.
DATABASE_PATH = os.environ["DATABASE_PATH"]


def connect():
    """
    Open a connection to the local ground-station database.

    A new connection is created per operation for now.
    This keeps the MVP simple.
    """

    connection = sqlite3.connect(DATABASE_PATH)

    # Return rows that behave like dictionaries instead of tuples.
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    """
    Create database tables if they do not already exist.

    This runs whenever Ground Station Core starts.
    """

    with connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                -- Permanent identifier for this wildfire event.
                event_id TEXT PRIMARY KEY,

                -- Drone that generated the event.
                drone_id TEXT NOT NULL,

                -- MediaMTX stream used when the event occurred.
                stream_key TEXT NOT NULL,

                -- Evidence time interval.
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,

                -- PENDING / READY / FAILED.
                evidence_status TEXT NOT NULL,

                -- Relative path to the final evidence video.
                evidence_path TEXT,

                -- Integrity hash of the final evidence video.
                evidence_sha256 TEXT,

                -- File size, useful later for uploads/storage.
                evidence_size_bytes INTEGER,

                -- When the event was first created locally.
                created_at TEXT NOT NULL
            )
            """
        )


def create_event(
    event_id: str,
    drone_id: str,
    stream_key: str,
    start_time: str,
    end_time: str,
):
    """
    Persist an event before attempting evidence generation.

    This is important because evidence generation might fail.
    The same event_id can then be reused when retrying.
    """

    with connect() as db:
        db.execute(
            """
            INSERT INTO events (
                event_id,
                drone_id,
                stream_key,
                start_time,
                end_time,
                evidence_status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                drone_id,
                stream_key,
                start_time,
                end_time,
                "PENDING",
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_event(event_id: str):
    """
    Retrieve one event by its permanent event ID.
    """

    with connect() as db:
        row = db.execute(
            """
            SELECT *
            FROM events
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()

        return dict(row) if row else None


def mark_evidence_ready(
    event_id: str,
    relative_path: str,
    sha256: str,
    size_bytes: int,
):
    """
    Mark evidence as successfully created and store its metadata.
    """

    with connect() as db:
        db.execute(
            """
            UPDATE events
            SET
                evidence_status = 'READY',
                evidence_path = ?,
                evidence_sha256 = ?,
                evidence_size_bytes = ?
            WHERE event_id = ?
            """,
            (
                relative_path,
                sha256,
                size_bytes,
                event_id,
            ),
        )


def mark_evidence_failed(event_id: str):
    """
    Mark evidence generation as failed.

    The event itself remains in the database so evidence can
    later be retried using the same event_id.
    """

    with connect() as db:
        db.execute(
            """
            UPDATE events
            SET evidence_status = 'FAILED'
            WHERE event_id = ?
            """,
            (event_id,),
        )

