-- gs_backend/db_queries/create_table.sql has no comma between 'verified' and 'closed',
-- so PostgreSQL joined them and the enum is ('active', 'verifiedclosed').
-- Without this fix an incident can never get the status 'closed'.
-- Run it once on a database that was created from the old script.
ALTER TYPE detection_status RENAME VALUE 'verifiedclosed' TO 'verified';
ALTER TYPE detection_status ADD VALUE IF NOT EXISTS 'closed';
