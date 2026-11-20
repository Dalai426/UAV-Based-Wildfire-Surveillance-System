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
- AI fire detection on the live video stream (inference service)
- events filled from the drone's telemetry at the detection time
- fire episodes: one event per connected fire

Drone authentication is planned but not implemented yet.

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

### Inference Service

The inference service watches the live video for fire.

It:

- reads the live stream from MediaMTX over RTSP (TCP)
- analyses every 5th frame (`TARGET_FPS`), about 6 per second: enough to notice a fire within a second, while the model still keeps up with the stream on the CPU
- gives each analysed frame a fire probability with a MobileNetV2 model (`models/mobilenet_v2_flame3.pth`); a frame counts as fire above 0.5 (`FIRE_THRESHOLD`)
- reports fire to the Core (`POST /events`) only when at least 3 of the last 5 analysed frames are fire (`CONFIRM_MIN`, `CONFIRM_WINDOW`): a single misclassified frame (glare, a sunset, snow) does not raise an alert, while a real fire, visible in most frames, is confirmed within about half a second
- uses the oldest fire frame among those 5 as the detection time X: when the fire was first seen, not when it was confirmed
- takes X when the frame is read from the stream (`cap.grab()`), before decoding and prediction add their delay
- forgets its last predictions after a reconnect, so X never comes from footage before an outage

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

`POST /events` receives detections from the inference service (detection time X and confidence) and turns them into events:

- **Fire episodes and clips:** one fire = one event with one clip
  - **Episode:** a detection (3/5 frames) at most 5 s after the previous one (`EPISODE_GAP_S`) joins the current event (`"new_event": false`) instead of creating a new one. Inference reports about 6 times per second, so otherwise one fire would create hundreds of events. The 5 s count from the *last* detection: the episode lasts as long as fire keeps being seen, and ends after 5 s without it. This bridges short interruptions (smoke, trees, the drone turning, a few misclassified frames). Kept in memory only (see Roadmap)
  - **Clip:** only the first detection gets a clip, from 5 s before to 5 s after X (`CLIP_PADDING_S`), showing how the fire came into view. The rest of the episode has no footage and its duration is not recorded (see Roadmap). The Core fetches the clip in the background 7 s after the detection arrives: 5 s until the footage after X exists, plus 2 s because MediaMTX writes in 1-second parts (`MEDIAMTX_WRITE_DELAY_S`). It is 10 s long, unless the recording starts or stops within 5 s of X (e.g. fire at the very start or end of the video)
- **Drone position at X:** the Core keeps the last 10 minutes of telemetry (`HISTORY_S`, the same as MediaMTX's recording retention), one entry per position update, about 10 per second. The event gets the entry closest to X: at 10 per second it is at most 0.05 s away (measured: 0.05–0.11 s), about 1 m at survey speed.
- **Stale telemetry:** if the closest telemetry entry is more than 2 s from X (time when frame hits the inference service), or the position is still 0,0 because the GPS is not ready, the Core answers `409` and creates no event: an event with a wrong location would send firefighters to the wrong place.
The same for the drone (in telemetry.py): `STALE_AFTER_S` also has 2 s limit after which `link_status` becomes `STALE`.

### Timestamps

Video and telemetry are both timestamped on arrival at the ground station, with the ground station's clock (UTC):

- telemetry: when the Core receives a position
- video: when inference reads the frame (X), shortly after MediaMTX receives it while inference keeps up with the stream; MediaMTX's recordings, from which the clip is cut, use the time MediaMTX received the video

One clock means the drone's and the ground station's clocks never have to be compared. It is also the only option today: MAVSDK does not pass on the drone's own time with each position, and OpenCV does not expose the video's RTP timestamps.

The remaining error is the difference between the two delays from the drone to the ground station: the video is encoded and buffered, the telemetry is sent directly. It has not been measured yet (see Roadmap).

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

- `events`: event ID, initial detecting drone ID, local creation time (`created_at`, when the event is saved), the complete event sent to the cloud (`cloud_payload_json`: detection time, confidence, position, altitude, speed, battery), and its cloud delivery state.
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

Handled HTTP, filesystem, and metadata-validation failures mark evidence `failed` and appear in the Core's log; a retry (test 8) that fails returns both IDs. The event remains saved. Database failures and process interruptions may prevent status updates.

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
│       ├── telemetry.py
│       └── models/
│           ├── __init__.py
│           ├── events.py
│           └── evidence.py
├── inference-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── inference.py
├── models/
│   └── mobilenet_v2_flame3.pth
├── cloud-sync/
├── data/
│   ├── recordings/
│   ├── evidence/
│   └── database/
└── videos/
    └── wildfire.mp4    (not in git, only needed for test 1)
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

Cloud Sync needs the AWS settings and certificates in `.env`. To run only the local pipeline, without the cloud:

```bash
docker compose up -d --build media-server ground-station-core inference-service
```

Check that they are running:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Application code is copied into the image. After source changes, rebuild the changed service, e.g. `docker compose up -d --build ground-station-core` or `docker compose up -d --build inference-service`.

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

Sending the request again with a detection time at most 5 s later returns the same `event_id` with `"new_event": false`, and creates no new event or clip.

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

Use the `evidence_id` from the `POST /events` reply (test 5) or from the event (test 7). Retrying preserves both IDs and does not insert another evidence record. A failed retry returns `502` (MediaMTX unavailable) or `500` (storage or validation failed) with `event_id` and `evidence_id` inside `detail`. Unknown evidence IDs return `404`.

### 9. Verify failure handling

Stop the Media Server, then create an event as in test 5:

```bash
docker compose stop media-server
```

The event is still created (`200`, evidence `pending`), because the clip is fetched in the background. About 7 seconds later, read the event (test 7): it remains saved and its evidence is `failed`.

Restart MediaMTX and retry the failed evidence:

```bash
docker compose start media-server
curl -X POST http://localhost:8080/evidence/<evidence_id>/retry
```

The requested footage must still exist within recording retention. Restart the FFmpeg publisher if it exited when MediaMTX stopped; new recording resumes once publishing resumes.

Also check invalid requests: a detection time without timezone should return `400`; missing fields, unparseable timestamps, or a confidence outside 0–100 should return `422`.

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

## Known Issues

- **PyTorch is limited to 2 threads** (`TORCH_THREADS` in `inference-service/inference.py`). By default PyTorch uses every CPU core; for this small model that made predictions slower and took CPU time from video decoding, so inference fell behind the stream (MediaMTX "reader is too slow" warnings, decode errors, about 840 % CPU). With 2 threads it keeps up at about 90 % CPU. The Raspberry Pi 5 has only 4 cores, shared with MediaMTX, the Core and video decoding, so the value has to be measured again there; if the Pi still cannot keep up, lower `TARGET_FPS`.

## Roadmap

Planned additions include:

- timestamp correlation between video frames and telemetry
  - linear interpolation between the two nearest telemetry entries, instead of using the nearest entry
  - monotonic time for the telemetry lookup: might be important for Raspberry Pi later
  - measure the real offset between video and telemetry (their delays from the drone to the ground station differ)
- wait until MediaMTX's `/list` shows the footage instead of a fixed 2 s (`MEDIAMTX_WRITE_DELAY_S`): a fixed wait is a guess, too short under heavy load (the clip misses its end) and longer than needed otherwise
- keep the inference service running when the Core is unreachable: `requests.post` currently raises an error, so the service crashes and restarts
- shorter recording retention (data minimisation under GDPR): MediaMTX keeps 10 minutes of footage, including people and property unrelated to any event; a shorter window stores less personal data (team decision)
- if event exceeds length limit (20s): entire fire duration will still be stored locally and sent to the cloud or add more clips to the same event
- store the current fire episode in SQLite: it is kept in memory, so a Core restart during a fire creates a second event for it
- save the telemetry of the clip window (`telemetry.json`) next to each clip: the event only has the position at the detection time, while the drone moves about 100 m during a 10 s clip; inside the hashed evidence folder, footage and location data are also tamper-evident together
- drone/session authentication
- production transport and storage security

These will be added incrementally as the local ground-station pipeline is completed and tested.
