import random
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


INITIAL_RETRY_SECONDS = 1
# Limit exponential backoff to 15 minutes.
# Server-provided Retry-After delays can exceed this.
MAX_RETRY_SECONDS = 15 * 60
FALLBACK_RETRY_SECONDS = 60 * 60

BACKOFF_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def parse_retry_after(value: str | None) -> timedelta | None:
    """Convert a Retry-After header into a duration."""
    if value is None:
        return None

    try:
        seconds = int(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)

            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)

            seconds = (
                retry_at - datetime.now(timezone.utc)
            ).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return None

    try:
        return timedelta(seconds=max(0, seconds))
    except OverflowError:
        return None


def retry_delay(
    attempt: int,
    *,
    status_code: int | None = None,
    retry_after: timedelta | None = None,
) -> timedelta:
    """Select a retry delay.

    attempt is the current delivery attempt, starting at 1.
    status_code=None represents a network failure.
    Credential-expiry recovery is handled separately by the worker.
    """
    if attempt < 1:
        raise ValueError("attempt must be at least 1")

    minimum_delay = timedelta(seconds=INITIAL_RETRY_SECONDS)

    # For throttling or temporary unavailability, respect the server's
    # requested wait instead of calculating our own delay.
    if status_code in {429, 503} and retry_after is not None:
        return max(minimum_delay, retry_after)

    use_backoff = (
        status_code is None
        or status_code in BACKOFF_STATUS_CODES
    )

    if use_backoff:
        delay_seconds = INITIAL_RETRY_SECONDS

        # Each failed attempt doubles the delay, up to the configured cap.
        for _ in range(attempt - 1):
            delay_seconds = min(delay_seconds * 2, MAX_RETRY_SECONDS)
            if delay_seconds >= MAX_RETRY_SECONDS:
                break
    else:
        # Other errors may require configuration or permission changes.
        # Use a one-hour base delay to avoid retrying them frequently.
        delay_seconds = FALLBACK_RETRY_SECONDS

    # Randomize the wait to reduce the chance of workers retrying together.
    # Use 80–100% of the selected delay, while keeping a one-second minimum.
    jittered_seconds = random.uniform(delay_seconds * 0.8, delay_seconds)

    return timedelta(
        seconds=max(INITIAL_RETRY_SECONDS, jittered_seconds)
    )
