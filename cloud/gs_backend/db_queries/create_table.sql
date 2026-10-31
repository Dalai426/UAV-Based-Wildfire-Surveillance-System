CREATE EXTENSION IF NOT EXISTS postgis;
SELECT PostGIS_Version();

GRANT ALL PRIVILEGES
ON ALL TABLES IN SCHEMA public
TO lambda_functions;

CREATE TYPE detection_status AS ENUM (
    'active',
    'verified'
    'closed'
);

CREATE TABLE wildfire_detections (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gs_event_id VARCHAR(100) NOT NULL UNIQUE
    detection_timestamp TIMESTAMPTZ NOT NULL
    footage_duration DOUBLE PRECISION NOT NULL
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    status detection_status NOT NULL DEFAULT 'active',
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    confidence_percent DOUBLE PRECISION NOT NULL,
    ground_station_id VARCHAR(50) NOT NULL,
    ground_station JSONB DEFAULT '{}'::jsonb,
    drone_id VARCHAR(50) NOT NULL,
    drone JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

select * from wildfire_detections;