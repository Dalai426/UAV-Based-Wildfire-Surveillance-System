import json
import asyncpg
from configs.logger_config import logger
from configs.db_config import get_db_pool
from models.closeIncident import IncidentPath, CloseIncident
from models.errors import NotFoundError, ConflictError


async def list_incidents(data):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT d.gs_event_id, d.detection_timestamp,
                       d.footage_duration, d.latitude, d.longitude,
                       d.status::text AS status, d.confidence_percent,
                       d.ground_station_id, d.ground_station::text AS ground_station,
                       d.drone_id, d.drone::text AS drone, d.created_at,
                       c.closed_by, c.closed_at
                FROM wildfire_detections d
                LEFT JOIN incident_closures c ON c.gs_event_id = d.gs_event_id
                ORDER BY d.detection_timestamp DESC
                """
            )
    except asyncpg.PostgresError as exc:
        logger.error("PostgreSQL error while reading detections %s", exc)
        raise
    except Exception as exc:
        logger.exception("Error while reading detections %s", exc)
        raise
    return {
        "success": True,
        "data": [
            {
                "gs_event_id": r["gs_event_id"],
                "detection_time": r["detection_timestamp"].isoformat(),
                "footage_duration": r["footage_duration"],
                "status": r["status"],
                "confidence_percent": r["confidence_percent"],
                "coordinates": {
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                },
                "ground_station_id": r["ground_station_id"],
                "ground_station": json.loads(r["ground_station"] or "{}"),
                "drone_id": r["drone_id"],
                "drone": json.loads(r["drone"] or "{}"),
                "created_at": r["created_at"].isoformat(),
                "closed_by": r["closed_by"],
                "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None,
            }
            for r in rows
        ],
    }


async def close_incident(data):
    logger.info("Request Body: %s", data.get("body"))
    path = IncidentPath.model_validate(data.get("pathParameters") or {})
    body = json.loads(data.get("body") or "{}")
    request = CloseIncident.model_validate(body)
    row = await closeIncident(path.gs_event_id, request)
    return {
        "success": True,
        "data": {
            "gs_event_id": path.gs_event_id,
            "status": "closed",
            "closed_by": row["closed_by"],
            "closed_at": row["closed_at"].isoformat()
        }
    }


async def closeIncident(gs_event_id, request: CloseIncident):
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            # One transaction: the status change and the closing record succeed or fail together
            async with conn.transaction():
                status = await conn.fetchval(
                    "SELECT status::text FROM wildfire_detections WHERE gs_event_id = $1 FOR UPDATE",
                    gs_event_id
                )
                if status is None:
                    raise NotFoundError("Incident not found")
                if status == "closed":
                    raise ConflictError("Incident is already closed")
                await conn.execute(
                    "UPDATE wildfire_detections SET status = 'closed' WHERE gs_event_id = $1",
                    gs_event_id
                )
                row = await conn.fetchrow(
                    """
                    INSERT INTO incident_closures (gs_event_id, closed_by)
                    VALUES ($1, $2)
                    RETURNING closed_by, closed_at
                    """,
                    gs_event_id,
                    request.closed_by
                )
                return dict(row)
    except asyncpg.UniqueViolationError as exc:
        logger.error("Constraint violation err: %s", exc)
        raise ConflictError("Incident is already closed")
    except asyncpg.PostgresError as exc:
        logger.error("PostgreSQL error while closing incident %s", exc)
        raise
    except (NotFoundError, ConflictError):
        raise
    except Exception as exc:
        logger.exception("Error while closing incident %s", exc)
        raise
