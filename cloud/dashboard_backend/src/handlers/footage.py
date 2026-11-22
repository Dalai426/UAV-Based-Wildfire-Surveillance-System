import os
import boto3
from botocore.config import Config
from configs.logger_config import logger

# How long the signed link works, in seconds
URL_LIFETIME = 900

_client = None


def _s3():
    global _client
    if _client is None:
        # Short timeouts: if S3 cannot be reached, the request must not hang
        _client = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_REGION", "eu-north-1"),
            config=Config(
                signature_version="s3v4",
                connect_timeout=2,
                read_timeout=3,
                retries={"max_attempts": 1},
            ),
        )
    return _client


def get_footage_url(event_id):
    """Signed link to the footage of one incident, or None.

    The ground station uploads to <event_id>/<evidence_id>.mp4,
    so the folder name is the incident id.
    """
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        logger.warning("S3_BUCKET is not set")
        return None
    try:
        s3 = _s3()
        found = s3.list_objects_v2(Bucket=bucket, Prefix=f"{event_id}/")
        videos = [o for o in found.get("Contents", []) if o["Key"].endswith(".mp4")]
        if not videos:
            return None
        newest = max(videos, key=lambda o: o["LastModified"])
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": newest["Key"]},
            ExpiresIn=URL_LIFETIME,
        )
    except Exception as exc:
        # The incident details must still load when the footage link fails
        logger.error("Could not get footage link for %s: %s", event_id, exc)
        return None
