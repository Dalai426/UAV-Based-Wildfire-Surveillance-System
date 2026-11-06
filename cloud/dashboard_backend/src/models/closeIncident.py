from pydantic import BaseModel, Field, ConfigDict


class IncidentPath(BaseModel):
    gs_event_id: str = Field(min_length=1, max_length=80)


class CloseIncident(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    closed_by: str = Field(min_length=1, max_length=100)
