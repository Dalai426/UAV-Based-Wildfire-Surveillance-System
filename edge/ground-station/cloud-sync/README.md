# Cloud Sync

Delivers locally stored events and evidence to AWS. Core creates the records
and video files; Cloud Sync handles their cloud delivery.

## Workers

Separate workers run in their own threads:

- `event_worker.py` sends stored event JSON to the cloud API.
- `evidence_worker.py` uploads completed evidence videos to S3.

Each worker processes due records sequentially in batches, then pauses before
checking again. Evidence is selected only when creation is `ready`
and cloud delivery is `pending`.

## Delivery state

Events and evidence have separate cloud delivery states: `pending` and `sent`.

Before delivery, the worker records the attempt and a fallback retry time.
Failures save the error and schedule another attempt. Successful delivery
records the completion time and clears the retry time.

The last error is retained after success. There is no maximum attempt count.

## S3 uploads

Videos remain on disk. SQLite stores their relative paths, sizes, and SHA-256
checksums.

Objects use this key:

`{event_id}/{evidence_id}.mp4`

Uploads use a conditional PUT to prevent overwriting existing objects.
Retries first check whether S3 already contains the expected video.

Verification compares remote size and SHA-256 without downloading the video.
Matching objects count as delivered. Mismatched or unverifiable objects remain
pending and their errors are recorded.

## Credentials

Both workers share a credentials manager. It obtains temporary AWS
credentials through mutual TLS and refreshes them before expiry.

A lock prevents simultaneous refreshes. Retry waits happen outside the lock.

An expired-token response triggers a credential refresh and an immediate retry
within the same recorded delivery cycle.

The evidence worker reuses its S3 client and replaces it when credentials change.

## Retries

Temporary failures use capped exponential backoff with jitter.
Other errors use a longer fallback delay.

For supported responses, `Retry-After` overrides the calculated delay.
SQLite failures pause batch processing before another check.