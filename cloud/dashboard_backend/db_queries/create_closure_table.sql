-- One row per closed incident: who closed it and when.
-- Incidents are identified by gs_event_id (the id the ground station sends).
CREATE TABLE incident_closures (
    closure_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gs_event_id VARCHAR(100) NOT NULL UNIQUE REFERENCES wildfire_detections (gs_event_id),
    closed_by VARCHAR(100) NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- The GRANT in create_table.sql only covers tables that existed when it ran
GRANT ALL PRIVILEGES
ON incident_closures
TO lambda_functions;

select * from incident_closures;
