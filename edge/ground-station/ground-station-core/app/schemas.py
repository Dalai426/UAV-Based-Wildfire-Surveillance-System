from datetime import datetime

from pydantic import BaseModel, Field


class CreateEventRequest(BaseModel):
    """Create a test event and request its first evidence interval."""

    start: datetime
    end: datetime


class CreateEvidence(BaseModel):
    """Source and interval needed before an evidence file exists."""

    evidence_id: str
    event_id: str
    drone_id: str
    stream_key: str
    requested_start: datetime
    requested_end: datetime


class Evidence(BaseModel):
    """Completed clip metadata, also saved beside the video as JSON."""

    evidence_id: str
    event_id: str
    drone_id: str
    stream_key: str
    requested_start: datetime
    requested_end: datetime
    relative_path: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

