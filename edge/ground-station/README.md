# Wildfire Detection Ground Station

Offline-first ground station for drone-based wildfire detection.

The ground station receives and records a live drone video stream, stores events locally, creates evidence clips from recorded footage, and keeps operating without an Internet connection.

## Current Status

Currently implemented:

- Media Server using MediaMTX
- rolling local video recording
- Ground Station Core API
- local SQLite event storage
- evidence extraction from recorded video
- evidence metadata and SHA-256 hashing
- retry-safe evidence creation

AI inference, drone telemetry/authentication, and cloud synchronization are planned but not implemented yet.

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
- generates and persists an `event_id`
- stores event state in SQLite
- requests recorded video intervals from the Media Server
- creates permanent evidence files
- creates evidence metadata
- calculates a SHA-256 integrity hash
- supports evidence retries using the same event ID

The current `/events` endpoint is used manually for testing. Later, events will be triggered by the detection pipeline.

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
    └── <event_id>/
        ├── <stream_key>.mp4
        └── metadata.json
```

Evidence is stored separately from the rolling recordings and is not affected by MediaMTX's rolling-recording cleanup.

`metadata.json` contains information such as:

```json
{
  "event_id": "...",
  "drone_id": "...",
  "stream_key": "...",
  "start": "...",
  "end": "...",
  "video_file": "...",
  "relative_path": "...",
  "size_bytes": 123456,
  "sha256": "...",
  "status": "ready"
}
```

### Database

The local SQLite database is stored under:

```text
data/database/
```

An event is saved before evidence creation starts.

This means that if evidence creation fails, the event still exists and evidence can be retried using the same `event_id`.

## How Evidence Creation Works

When an event is created:

```text
Create event
    ↓
Generate event_id
    ↓
Save event to SQLite
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
Mark event READY
```

If evidence creation fails, the event remains in the database and can be retried.

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
│       └── evidence.py
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

Use a valid interval from the Media Server recording range:

```bash
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{
    "start": "<start-time>",
    "end": "<end-time>"
  }'
```

A successful request returns an `event_id` and evidence metadata.

### 6. Check the generated evidence

```bash
find data/evidence -type f
```

You should see:

```text
data/evidence/<date>/<event_id>/
├── <stream_key>.mp4
└── metadata.json
```

### 7. Check an event

```bash
curl http://localhost:8080/events/<event_id>
```

### 8. Retry evidence creation

```bash
curl -X POST \
  http://localhost:8080/events/<event_id>/evidence
```

The existing `event_id` is reused rather than creating a new event.

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
- drone telemetry and timestamp correlation
- drone/session authentication
- cloud synchronization
- production transport and storage security

These will be added incrementally as the local ground-station pipeline is completed and tested.
