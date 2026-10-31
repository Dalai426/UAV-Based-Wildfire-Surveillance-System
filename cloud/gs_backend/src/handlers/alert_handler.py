from configs.logger_config import logger
from models.detectionEvent import DetectionEvent
from configs.db_config import get_db_pool
import json
import asyncpg

async def handle_alert(data):
    logger.info("Request Body: %s", data.get("body"))
    body = data.get("body") or "{}"
    print(data)
    event_json = json.loads(body)
    event = DetectionEvent.model_validate(event_json)
    row = await insertEvent(event)
    return {
        "success":True,
        "data": {
            "event_id": str(row["event_id"]),
            "created_at": row["created_at"].isoformat()
        }
    }

async def insertEvent(event:DetectionEvent):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
                # It consider values as if WHERE username = "' OR '1'='1"
                row = await conn.fetchrow(
                    """
                    INSERT INTO wildfire_detections (
                        gs_event_id,
                        detection_timestamp,
                        footage_duration,
                        latitude,
                        longitude,
                        status,
                        location,
                        confidence_percent,
                        ground_station_id,
                        ground_station,
                        drone_id,
                        drone
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6,
                        ST_SetSRID(ST_MakePoint($5, $4), 4326)::geography,
                        $7, $8, $9::jsonb, $10, $11::jsonb
                    )
                    RETURNING event_id, created_at
                    """,
                    event.event_id,
                    event.detection_time,
                    event.footage_duration,
                    event.coordinates.latitude,
                    event.coordinates.longitude,
                    'active',
                    event.confidence_percent,
                    event.ground_station_id,
                    event.ground_station.model_dump_json(),
                    event.drone_id,
                    event.drone.model_dump_json()
                )
                return dict(row)
    except asyncpg.UniqueViolationError as exc:
        logger.error("Constraint violation err: %s", exc)
        raise 
    except asyncpg.PostgresError as exc:
        logger.error("PostgreSQL error while inserting detection %s", exc)
        raise
    except Exception as exc:
        logger.exception("Error while inserting detection %s", exc)
        raise
                
        