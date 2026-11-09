import base64
from pathlib import Path
from typing import Literal

from botocore.client import BaseClient
from botocore.exceptions import ClientError


VerificationResult = Literal[
    "matching", "missing", "mismatched", "unverifiable"
]


def _checksum_base64(sha256: str) -> str:
    # SQLite stores the digest as hex. S3 expects the same digest as Base64.
    return base64.b64encode(bytes.fromhex(sha256)).decode("ascii")


def upload_evidence(
    client: BaseClient,
    bucket: str,
    key: str,
    path: str | Path,
    size_bytes: int,
    sha256: str,
) -> None:
    """Upload the video; let the worker handle any errors."""
    with Path(path).open("rb") as video:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=video,
            ContentType="video/mp4",
            ContentLength=size_bytes,

            # S3 checks that the uploaded bytes match the expected checksum.
            ChecksumSHA256=_checksum_base64(sha256),

            # Refuse to overwrite an existing object.
            # The worker must verify it before accepting it as delivered.
            IfNoneMatch="*",
        )


def verify_evidence(
    client: BaseClient,
    bucket: str,
    key: str,
    size_bytes: int,
    sha256: str,
) -> VerificationResult:
    """Check whether S3 contains the expected video."""
    try:
        # HEAD retrieves size and checksum without downloading the video.
        response = client.head_object(
            Bucket=bucket,
            Key=key,
            ChecksumMode="ENABLED",
        )
    except ClientError as error:
        status = error.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )

        # Only 404 means missing. Permission and other errors must propagate:
        # they do not tell us whether the video exists.
        if status == 404:
            return "missing"
        raise

    if response["ContentLength"] != size_bytes:
        return "mismatched"

    # Size alone cannot prove the contents match.
    # Use S3's stored SHA-256 checksum; ETag is not a SHA-256 checksum.
    remote_checksum = response.get("ChecksumSHA256")
    if remote_checksum is None:
        return "unverifiable"

    if remote_checksum != _checksum_base64(sha256):
        return "mismatched"

    return "matching"

