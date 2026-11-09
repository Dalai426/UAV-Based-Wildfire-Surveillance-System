import os
import sqlite3
from datetime import datetime, timezone

from app.models.evidence import CreateEvidence, Evidence


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


    # Reject evidence records referencing a nonexistent event.
    connection.execute("PRAGMA foreign_keys = ON")

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

                -- Drone that supplied the initial detection.
                drone_id TEXT NOT NULL,

                -- When the event was first created locally.
                created_at TEXT NOT NULL,

                -- Complete validated DetectionEvent JSON.
                cloud_payload_json TEXT NOT NULL,

                -- Cloud delivery state.
                cloud_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (cloud_status IN ('pending', 'sent')),
                cloud_attempts INTEGER NOT NULL DEFAULT 0,
                cloud_next_attempt_at TEXT,
                cloud_last_error TEXT,
                cloud_sent_at TEXT
            )
            """
        )

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL REFERENCES events(event_id),
                drone_id TEXT NOT NULL,
                stream_key TEXT NOT NULL,
                requested_start TEXT NOT NULL,
                requested_end TEXT NOT NULL,

                -- pending / ready / failed.
                creation_status TEXT NOT NULL DEFAULT 'pending',
                
                relative_path TEXT,

                -- Integrity hash of the final evidence video.
                sha256 TEXT,

                -- File size, useful later for uploads/storage.
                size_bytes INTEGER,

                created_at TEXT NOT NULL,

                cloud_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (cloud_status IN ('pending', 'sent')),
                cloud_attempts INTEGER NOT NULL DEFAULT 0,
                cloud_next_attempt_at TEXT,
                cloud_last_error TEXT,
                cloud_sent_at TEXT
            )
            """
        )


def insert_event(
    event_id: str,
    drone_id: str,
    cloud_payload_json: str,
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
                created_at,
                cloud_payload_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                event_id,
                drone_id,
                datetime.now(timezone.utc).isoformat(),
                cloud_payload_json,
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


def insert_evidence(request: CreateEvidence):
    with connect() as db:
        db.execute(
            """
            INSERT INTO evidence (
                evidence_id,
                event_id,
                drone_id,
                stream_key,
                requested_start,
                requested_end,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.evidence_id,
                request.event_id,
                request.drone_id,
                request.stream_key,
                request.requested_start.isoformat(),
                request.requested_end.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_evidence(evidence_id: str):
    """Load an evidence record for inspection or retry."""
    with connect() as db:
        row = db.execute(
            """
            SELECT *
            FROM evidence
            WHERE evidence_id = ?
            """,
            (evidence_id,),
        ).fetchone()

        return dict(row) if row else None


def mark_evidence_ready(evidence: Evidence):
    """
    Mark evidence as successfully created and store its metadata.
    """

    with connect() as db:
        db.execute(
            """
            UPDATE evidence
            SET creation_status = 'ready',
                relative_path = ?,
                sha256 = ?,
                size_bytes = ?
            WHERE evidence_id = ?
            """,
            (
                evidence.relative_path,
                evidence.sha256,
                evidence.size_bytes,
                evidence.evidence_id,
            ),
        )


def mark_evidence_failed(evidence_id: str):
    """
    Mark evidence generation as failed.
    """
    with connect() as db:
        db.execute(
            """
            UPDATE evidence
            SET creation_status = 'failed'
            WHERE evidence_id = ?
            """,
            (evidence_id,),
        )


def list_event_evidence(event_id: str):
    """Return all evidence records belonging to an event."""
    with connect() as db:
        rows = db.execute(
            """
            SELECT *
            FROM evidence
            WHERE event_id = ?
            ORDER BY created_at, evidence_id
            """,
            (event_id,),
        ).fetchall()

        return [dict(row) for row in rows]
    
