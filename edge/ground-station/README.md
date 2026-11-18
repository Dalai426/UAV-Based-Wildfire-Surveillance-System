# Wildfire Detection Ground Station

Offline-first ground station for drone-based wildfire detection.

The ground station receives and records a live drone video stream, stores events locally, creates evidence clips from recorded footage, and keeps operating without an Internet connection.

## Current Status

Currently implemented:

- Media Server using MediaMTX
- rolling local video recording
- Ground Station Core API
- separate SQLite event and evidence storage
- typed request and evidence models using Pydantic
- evidence extraction from recorded video
- evidence metadata and SHA-256 hashing
- reuse of completed evidence on retries
- live drone telemetry over MAVLink (UDP 14551)
- cloud event delivery with persisted retries
- S3 evidence uploads with checksum verification
- shared temporary AWS credentials through AWS IoT

AI inference and drone authentication are planned but not implemented yet.

## Services

### Media Server

The Media Server is responsible for video transport and recording.

It:

- receives the live video stream
- makes the live stream available to other services
- records incoming video locally
- maintains a configurable rolling recording history
- exposes recorded intervals through the playback API

Rolling recording behavior and retention are configured through MediaMTX.

### Ground Station Core

The Ground Station Core contains the main application logic.

It currently:

- creates wildfire events
- generates and persists an `event_id` and a separate `evidence_id`
- stores event state in SQLite
- requests recorded video intervals from the Media Server
- creates permanent evidence files
- creates evidence metadata
- calculates a SHA-256 integrity hash
- supports evidence retries using the same evidence ID
- receives the drone's telemetry (position, altitude, speed, attitude, battery, flight mode) on UDP 14551 and serves the latest values at `GET /telemetry/latest`

`POST /events` receives detections from the inference service (detection time and confidence) and fills the event from the telemetry history at that time.

The inference service only reports fire once 3 of its last 5 predictions are above the threshold, and uses the oldest of those fire frames as the detection time.

Detections at most 4.5 s apart (`EPISODE_GAP_S`) belong to the same fire episode: the first creates one event and one evidence record, the following ones join that event. The database relationship supports multiple evidence records per event, but additional-clip creation is not implemented.

### Cloud Sync

Cloud Sync delivers stored events to the cloud API and uploads completed
evidence videos to S3.

Separate workers process events and evidence independently. Both use SQLite
to track delivery attempts and retries, and share temporary AWS credentials
obtained through AWS IoT.

See [Cloud Sync](cloud-sync/README.md) for implementation details.

## Local Storage

Runtime data is stored under:

```text
data/
├── recordings/
├── evidence/
└── database/
```

### Recordings

```text
data/recordings/
└── <stream_key>/
    └── ...
```

These files are managed by MediaMTX and form the rolling recording buffer.

Rolling recordings are temporary and are automatically removed according to the configured retention policy.

### Evidence

```text
data/evidence/
└── YYYY-MM-DD/
    └── <evidence_id>/
        ├── video.mp4
        └── metadata.json
```

Evidence is stored separately from the rolling recordings and is not affected by MediaMTX's rolling-recording cleanup.

The date is the requested interval's start date in UTC. The evidence ID identifies the clip; its event and source stream are recorded in SQLite and metadata.

`metadata.json` contains information such as:

```json
{
  "evidence_id": "...",
  "event_id": "...",
  "drone_id": "...",
  "stream_key": "...",
  "requested_start": "2026-11-01T10:00:00Z",
  "requested_end": "2026-11-01T10:00:10Z",
  "relative_path": "2026-11-01/<evidence_id>/video.mp4",
  "size_bytes": 123456,
  "sha256": "<64-character lowercase hexadecimal hash>"
}
```

### Database

The local SQLite database is stored under:

```text
data/database/ground-station.db
```

The database has two tables:

- `events`: event ID, initial detecting drone ID, and local creation time (`created_at`). This timestamp is when the event is saved, not a separate detection timestamp.
- `evidence`: evidence ID, parent event ID, source drone and stream, requested interval, creation status (`pending`, `ready`, or `failed`), file path, hash, size, and creation time.

The event is committed independently before the pending evidence record is inserted. An evidence failure does not roll back the event. Retries load the original evidence inputs and reuse its `evidence_id`.

`init_db()` creates missing tables at startup; it does not migrate existing tables. Databases from the previous combined event/evidence schema need migration. For disposable development data, stop the Core, remove the test database, and restart it to create the current schema. Existing video files remain on disk but are not automatically imported into a new database.

## How Evidence Creation Works

When an event is created:

```text
Create event
    ↓
Same episode as the previous detection? → reply with its event_id, stop
    ↓
Look up telemetry at the detection time
    ↓
Generate event_id and evidence_id
    ↓
Save event to SQLite
    ↓
Save separate pending evidence record
    ↓
Reply; wait 7 s in the background
    ↓
Request recorded interval from Media Server
    ↓
Download to temporary file
    ↓
Calculate SHA-256
    ↓
Move to final evidence directory
    ↓
Write metadata.json
    ↓
Mark evidence ready
```

Handled HTTP, filesystem, and metadata-validation failures mark evidence `failed` and return both IDs. The event remains saved. Database failures and process interruptions may prevent status updates.

Completed evidence is reused when both the video and valid metadata exist. Retries do not recalculate the stored hash. Simultaneous creation/retry requests for the same evidence are not yet protected against conflicts.

## Project Structure

```text
ground-station/
├── .env
├── compose.yml
├── mediamtx/
│   └── mediamtx.yml
├── ground-station-core/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── db.py
│       ├── evidence.py
│       ├── schemas.py
│       └── telemetry.py
├── data/
│   ├── recordings/
│   ├── evidence/
│   └── database/
└── videos/
    └── wildfire.mp4
```

## Running

Create the local data directories:

```bash
mkdir -p data/recordings data/evidence data/database
```

Build and start the services:

```bash
docker compose up -d --build
```

Check that they are running:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Application code is copied into the image. After source changes, rebuild the Core with `docker compose up -d --build ground-station-core`.

## Testing

### 1. Publish a test video

A prerecorded video can be used to simulate the drone:

```bash
ffmpeg \
  -re \
  -stream_loop -1 \
  -i videos/wildfire.mp4 \
  -map 0:v:0 \
  -an \
  -c:v copy \
  -rtsp_transport tcp \
  -f rtsp \
  rtsp://localhost:8554/d7f3a91c
```

The stream key must match the configured `STREAM_KEY`.

The virtual drone's camera (`edge/drone`) publishes to the same path. Use either this test video or the drone camera, not both.

### 2. Check that recordings are being created

```bash
find data/recordings -type f
```

### 3. Find available recording times

```bash
curl "http://localhost:9996/list?path=d7f3a91c"
```

Use a start time contained in the returned recording range.

### 4. Test recorded video playback

```bash
curl --get http://localhost:9996/get \
  --data-urlencode "path=d7f3a91c" \
  --data-urlencode "start=<recorded-start-time>" \
  --data-urlencode "duration=<seconds>" \
  --data-urlencode "format=mp4" \
  -o test-evidence.mp4
```

The resulting file can be checked with:

```bash
ffplay test-evidence.mp4
```

### 5. Create a test event

Simulates a detection from the inference service. The drone must be flying (see `edge/drone/README.md`), because the event takes the drone's position at the detection time.

Use a detection time from the last few seconds, with a timezone:

```bash
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{
    "detection_time": "<detection-time>",
    "confidence_percent": 87
  }'
```

A successful request returns right away:

```json
{
  "event_id": "...",
  "new_event": true,
  "evidence_id": "...",
  "evidence_status": "pending",
  "telemetry_distance_s": 0.081
}
```

Sending the request again with a detection time at most 4.5 s later returns the same `event_id` with `"new_event": false`, and creates no new event or clip.

`telemetry_distance_s` is how far the nearest telemetry entry is from the detection time. The event gets that entry's position, altitude, speed and battery.

The Core fetches the clip [detection time − 5 s, detection time + 5 s] in the background, about 7 seconds later, once the footage after the detection has been recorded (`CLIP_PADDING_S` and `MEDIAMTX_WRITE_DELAY_S` in `app/main.py`). Check it with test 7.

If no telemetry entry is within 2 seconds of the detection time (drone not flying, telemetry gap, or GPS not ready yet), the Core returns `409` and creates no event.

### 6. Check the generated evidence

```bash
find data/evidence -type f
```

You should see:

```text
data/evidence/<date>/<evidence_id>/
├── video.mp4
└── metadata.json
```

### 7. Check an event

```bash
curl http://localhost:8080/events/<event_id>
```

The response includes event fields and an `evidence` list containing database records and their creation states. Unknown event IDs return `404`.

To list all records locally (requires the SQLite CLI):

```bash
sqlite3 -header -column data/database/ground-station.db "SELECT * FROM events;"
sqlite3 -header -column data/database/ground-station.db "SELECT * FROM evidence;"
```

### 8. Retry evidence creation

```bash
curl -X POST \
  http://localhost:8080/evidence/<evidence_id>/retry
```

Use `evidence.evidence_id` from a successful creation response or `detail.evidence_id` from a handled failure response. Retrying preserves both IDs and does not insert another evidence record. Unknown evidence IDs return `404`.

### 9. Verify failure handling

Stop the Media Server, then submit an event request using a known recorded interval:

```bash
docker compose stop media-server
```

Expect `502` with `event_id` and `evidence_id` inside `detail`. Read the event to confirm it remains saved and the evidence is `failed`.

Restart MediaMTX and retry the failed evidence:

```bash
docker compose start media-server
curl -X POST http://localhost:8080/evidence/<evidence_id>/retry
```

The requested footage must still exist within recording retention. Restart the FFmpeg publisher if it exited when MediaMTX stopped; new recording resumes once publishing resumes.

Also check invalid requests: missing timezone, reversed/equal timestamps, and intervals above the limit should return `400`; missing fields or unparseable timestamps should return `422`.

### 10. Check the drone telemetry

Start the virtual drone (please see `edge/drone/README.md` before this step), then:

```bash
curl http://localhost:8080/telemetry/latest
```

Everything you need to know is explained in `edge/drone/README.md`.

## Development Configuration

The current development setup uses fixed values from `.env`:

```env
DRONE_ID=550e8400-e29b-41d4-a716-446655440000
STREAM_KEY=d7f3a91c
```

These are temporary development values.

The stream key identifies the Media Server stream. It is not intended to be an authentication secret.

Media recording behavior, retention, and related media settings are configured separately in the MediaMTX configuration.

## Roadmap

Planned additions include:

- AI inference from the live video stream
- timestamp correlation between video frames and telemetry
  - linear interpolation between the two nearest telemetry entries, instead of using the nearest entry
  - monotonic time for the telemetry lookup: might be important for Raspberry Pi later
- if event exceeds length limit (20s): fire duration per event (first to last detection), stored locally and sent to the cloud
- drone/session authentication
- production transport and storage security

These will be added incrementally as the local ground-station pipeline is completed and tested.
