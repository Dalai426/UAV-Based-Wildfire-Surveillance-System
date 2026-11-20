import os
import sqlite3
import time

# Database configuration
DATABASE_PATH = os.environ["DATABASE_PATH"]


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialise_sentinel_database():
    with get_connection() as conn:
        # We can add flight plan, and mission id
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sentinel_flights (
                drone_id TEXT PRIMARY KEY,
                session_key BLOB NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL
            )
        """)
        conn.commit()


def save_flight_session(drone_id: str, session_key: bytes):
    created_at = int(time.time())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sentinel_flights (
                drone_id,
                session_key,
                status,
                created_at
            )
            VALUES (?, ?, 'active', ?)
            ON CONFLICT(drone_id) DO UPDATE SET
                session_key = excluded.session_key,
                status = 'active',
                created_at = excluded.created_at
            """,
            (
                drone_id,
                session_key,
                created_at,
            ),
        )
        conn.commit()


def get_active_flight(drone_id: str):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM sentinel_flights
            WHERE drone_id = ?
              AND status = 'active'
            """,
            (drone_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "drone_id": row["drone_id"],
        "session_key": row["session_key"],
        "created_at": row["created_at"],
    }


def revoke_flight_session(drone_id: str, localStorage: bool = True):
    with get_connection() as conn:
        if localStorage:
            # Retain the record for audit purposes.
            conn.execute(
                """
                UPDATE sentinel_flights
                SET status = 'revoked'
                WHERE drone_id = ?
                """,
                (drone_id,),
            )
        else:
            # Permanently delete the session record.
            conn.execute(
                """
                DELETE FROM sentinel_flights
                WHERE drone_id = ?
                """,
                (drone_id,),
            )

        conn.commit()
