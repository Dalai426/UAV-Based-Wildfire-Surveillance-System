import os
import sqlite3
from pathlib import Path
from contextlib import closing
from datetime import datetime, timezone

DATABASE_PATH = os.environ["DATABASE_PATH"]


def connect() -> sqlite3.Connection:
    """Open the existing database created by Core.

    Use a separate connection for each operation.
    Wait up to one second if the database is locked.
    """
    database_uri = Path(DATABASE_PATH).resolve().as_uri()

    connection = sqlite3.connect(
        f"{database_uri}?mode=rw",
        uri=True,
        timeout=1,
    )
    connection.row_factory = sqlite3.Row

    return connection


def get_pending_events(
    limit: int = 20,
    *,
    max_attempts: int,
) -> list[sqlite3.Row]:
    """Return pending events whose retry time is due or has not been set."""
    now = datetime.now(timezone.utc).isoformat()

    with closing(connect()) as db:
        rows = db.execute(
            """
            SELECT event_id, cloud_payload_json, cloud_attempts
            FROM events
            WHERE cloud_status = 'pending'
              AND cloud_attempts < ?
              AND (
                  cloud_next_attempt_at IS NULL
                  OR cloud_next_attempt_at <= ?
              )
            ORDER BY created_at, event_id
            LIMIT ?
            """,
            (max_attempts, now, limit),
        ).fetchall()

    return rows


def record_event_attempt(
    event_id: str,
    next_attempt_at: str,
) -> None:
    """Count the attempt and set a fallback retry time before sending.

    If the process crashes during delivery, this retry time remains in SQLite.
    """
    with closing(connect()) as db:
        db.execute(
            """
            UPDATE events
            SET cloud_attempts = cloud_attempts + 1,
                cloud_next_attempt_at = ?
            WHERE event_id = ?
              AND cloud_status = 'pending'
            """,
            (next_attempt_at, event_id),
        )
        db.commit()


def record_event_failure(
    event_id: str,
    next_attempt_at: str,
    last_error: str,
) -> None:
    """Save the error and next retry time while leaving delivery pending."""
    with closing(connect()) as db:
        db.execute(
            """
            UPDATE events
            SET 
                cloud_next_attempt_at = ?,
                cloud_last_error = ?
            WHERE event_id = ?
              AND cloud_status = 'pending'
            """,
            (next_attempt_at, last_error, event_id),
        )
        db.commit()


def mark_event_sent(event_id: str) -> None:
    """Mark the event as sent and clear the retry time."""
    sent_at = datetime.now(timezone.utc).isoformat()

    with closing(connect()) as db:
        db.execute(
            """
            UPDATE events
            SET cloud_status = 'sent',
                cloud_next_attempt_at = NULL,
                cloud_sent_at = ?
            WHERE event_id = ?
            """,
            (sent_at, event_id),
        )
        db.commit()


def get_pending_evidence(limit: int = 20) -> list[sqlite3.Row]:
    """Return completed evidence that is pending upload and due for an attempt.

    Exclude evidence that is still being created or whose creation failed.
    """
    now = datetime.now(timezone.utc).isoformat()

    with closing(connect()) as db:
        rows = db.execute(
            """
            SELECT 
                event_id, 
                evidence_id,
                relative_path,
                sha256,
                size_bytes,
                cloud_attempts
            FROM evidence
            WHERE creation_status = 'ready'
              AND cloud_status = 'pending'
              AND (
                  cloud_next_attempt_at IS NULL
                  OR cloud_next_attempt_at <= ?
              )
            ORDER BY created_at, evidence_id
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()

    return rows


def record_evidence_attempt(
    evidence_id: str,
    next_attempt_at: str,
) -> None:
    """Count the attempt and set a fallback retry time before sending.

    If the process crashes during delivery, this retry time remains in SQLite.
    """
    with closing(connect()) as db:
        db.execute(
            """
            UPDATE evidence
            SET cloud_attempts = cloud_attempts + 1,
                cloud_next_attempt_at = ?
            WHERE evidence_id = ?
              AND cloud_status = 'pending'
            """,
            (next_attempt_at, evidence_id),
        )
        db.commit()


def mark_evidence_sent(evidence_id: str) -> None:
    """Mark the evidence as sent and clear the retry time."""
    sent_at = datetime.now(timezone.utc).isoformat()

    with closing(connect()) as db:
        db.execute(
            """
            UPDATE evidence
            SET cloud_status = 'sent',
                cloud_next_attempt_at = NULL,
                cloud_sent_at = ?
            WHERE evidence_id = ?
              AND cloud_status = 'pending'
            """,
            (sent_at, evidence_id),
        )
        db.commit()


def record_evidence_failure(
    evidence_id: str,
    next_attempt_at: str,
    last_error: str,
) -> None:
    """Save the error and next retry time while leaving delivery pending."""
    with closing(connect()) as db:
        db.execute(
            """
            UPDATE evidence
            SET cloud_next_attempt_at = ?,
                cloud_last_error = ?
            WHERE evidence_id = ?
              AND cloud_status = 'pending'
            """,
            (next_attempt_at, last_error, evidence_id),
        )
        db.commit()

    
