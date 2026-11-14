
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class GroundStation(BaseModel):
    model_config = ConfigDict(extra="allow")

class Coordinates(BaseModel):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)

class Drone(BaseModel):
    model_config = ConfigDict(extra="allow")
    speed: float = Field(ge=0)
    battery_status: str = Field(min_length=0)

class DetectionEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=80)
    ground_station_id: str = Field(min_length=1, max_length=80)
    ground_station: GroundStation
    confidence_percent: float = Field(ge=0, le=100)
    detection_time: datetime
    footage_duration: float = Field(ge=0)
    status: str = Field(min_length=1, max_length=35)
    coordinates: Coordinates
    drone_id: str = Field(min_length=1, max_length=80)
    drone: Drone
