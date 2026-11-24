from app.auth.db import get_last_active_session
import hmac


def authorize_session(drone_id: str, session: bytes):

    resp = get_last_active_session(drone_id)
    if resp is None:
        raise ValueError(f"No active flight session found for drone '{drone_id}'")
    print(session)
    if not hmac.compare_digest(
        session,
        resp["session_key"],
    ):
        raise ValueError("Invalid session token")
    return {
        "drone_id": resp["drone_id"],
        "session": session,
        "status": resp["status"],
        "created_at": resp["created_at"],
    }
