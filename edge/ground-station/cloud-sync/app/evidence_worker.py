import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError as BotoConnectionError,
    HTTPClientError,
)

from app.auth import CredentialsManager, TemporaryCredentials
from app.db import (
    get_pending_evidence,
    record_evidence_attempt,
    mark_evidence_sent,
    record_evidence_failure,
)

from app.retry import parse_retry_after, retry_delay
from app.s3 import upload_evidence, verify_evidence


EVIDENCE_CHECK_INTERVAL_SECONDS = 1
DATABASE_RETRY_SECONDS = 1
CONDITIONAL_STATUS_CODES = {409, 412}
BACKOFF_ERROR_CODES = {
    "InternalError",
    "RequestTimeout",
    "ServiceUnavailable",
    "SlowDown",
    "Throttling",
    "ThrottlingException",
}

logger = logging.getLogger(__name__)


class EvidenceVerificationError(Exception):
    """The remote object cannot be accepted as this evidence."""


class EvidenceWorker:
    """Use a class to keep the S3 session, client, and its credentials
    together across upload batches.

    Reusing the client allows uploads to reuse network connections.
    The client holds the credentials supplied when created, so we
    replace it when the credentials manager returns fresh credentials.
    """
    def __init__(self, credentials_manager: CredentialsManager):
        self.credentials_manager = credentials_manager
        self.bucket = os.environ["CLOUD_S3_BUCKET"]
        self.region = os.environ["AWS_REGION"]
        self.evidence_dir = Path(os.environ["EVIDENCE_DIR"]).resolve()
        self.session = boto3.Session(region_name=self.region)
        self._client = None
        self._client_credentials = None

    def _get_client(self, credentials: TemporaryCredentials):
        # The S3 client holds the credentials it was created with.
        # Replace it when the manager returns a different credential object.
        if self._client is None or self._client_credentials is not credentials:
            client = self.session.client(
                "s3",
                aws_access_key_id=credentials.access_key_id,
                aws_secret_access_key=credentials.secret_access_key.get_secret_value(),
                aws_session_token=credentials.session_token.get_secret_value(),
                config=Config(
                    connect_timeout=15,
                    read_timeout=60,
                    # Return control so retries can verify before resending.
                    retries={"mode": "standard", "total_max_attempts": 1},
                ),
            )
            self.close()
            self._client = client
            self._client_credentials = credentials

        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._client_credentials = None

    def _remote_matches(self, client, key: str, evidence: sqlite3.Row) -> bool:
        """Return True for matching, False for missing; raise if verification fails."""
        result = verify_evidence(
            client=client,
            bucket=self.bucket,
            key=key,
            size_bytes=evidence["size_bytes"],
            sha256=evidence["sha256"],
        )

        if result == "matching":
            return True
        if result == "missing":
            return False

        raise EvidenceVerificationError(f"Remote evidence {key} is {result}")

    def _deliver(self, client, evidence: sqlite3.Row, verify_first: bool) -> None:
        key = f"{evidence['event_id']}/{evidence['evidence_id']}.mp4"

        # Check S3 before retrying: an earlier upload may already have succeeded.
        if verify_first and self._remote_matches(client, key, evidence):
            return

        path = (self.evidence_dir / evidence["relative_path"]).resolve()
        if not path.is_relative_to(self.evidence_dir):
            raise ValueError("Evidence path is outside EVIDENCE_DIR")

        try:
            upload_evidence(
                client=client,
                bucket=self.bucket,
                key=key,
                path=path,
                size_bytes=evidence["size_bytes"],
                sha256=evidence["sha256"],
            )
        except ClientError as error:
            status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status not in CONDITIONAL_STATUS_CODES:
                raise

            # An earlier upload may have succeeded, but we failed to record it as sent.
            # If S3 already has the correct video, we can mark delivery successful.
            # If the video is missing, pass the upload error to retry handling.
            if not self._remote_matches(client, key, evidence):
                raise

    def handle_pending_evidence(self) -> None:
        for evidence in get_pending_evidence(limit=20):
            evidence_id = evidence["evidence_id"]
            attempt = evidence["cloud_attempts"] + 1
            credentials = self.credentials_manager.get_credentials()

            next_attempt_at = (
                datetime.now(timezone.utc) + retry_delay(attempt)
            ).isoformat()

            # Save the attempt and a fallback retry time before contacting S3.
            # This lets delivery recover if the process crashes during the upload.
            record_evidence_attempt(evidence_id, next_attempt_at)

            try:
                # A previous upload may have succeeded without SQLite recording success.
                # Verify retries before sending the video again; first attempts upload directly.
                verify_first = evidence["cloud_attempts"] > 0

                # Allow one immediate retry after refreshing expired credentials.
                # Both sends count as the single delivery cycle already recorded in SQLite.
                for send_attempt in range(2):
                    try:
                        client = self._get_client(credentials)
                        self._deliver(client, evidence, verify_first)
                        break
                    except ClientError as error:
                        code = error.response.get("Error", {}).get("Code")
                        if code != "ExpiredToken" or send_attempt == 1:
                            raise
                        
                        # Invalidate only the credentials used here: the other worker may
                        # already have refreshed the shared cache.
                        self.credentials_manager.invalidate_credentials(credentials)
                        credentials = self.credentials_manager.get_credentials()
                        verify_first = True

            except ClientError as error:
                response = error.response
                metadata = response.get("ResponseMetadata", {})
                status = metadata.get("HTTPStatusCode", 0)
                code = response.get("Error", {}).get("Code")

                # Use the shared retry helper's 503 policy to select exponential backoff.
                # This does not change the actual S3 response.
                if status in CONDITIONAL_STATUS_CODES or code in BACKOFF_ERROR_CODES:
                    status = 503
                delay = retry_delay(
                    attempt,
                    status_code=status,
                    retry_after=parse_retry_after(
                        metadata.get("HTTPHeaders", {}).get("retry-after")
                    ),
                )
                last_error = str(error)

            except (BotoConnectionError, HTTPClientError) as error:
                # Leave pending; the next delivery cycle verifies before PUT.
                delay = retry_delay(attempt)
                last_error = str(error)

            except (
                BotoCoreError,
                OSError,
                TypeError,
                ValueError,
                EvidenceVerificationError,
            ) as error:
                delay = retry_delay(attempt, status_code=400)
                last_error = str(error)

            else:
                logger.info("Evidence %s sent successfully", evidence_id)
                mark_evidence_sent(evidence_id)
                continue

            next_attempt_at = (datetime.now(timezone.utc) + delay).isoformat()

            logger.warning(
                "Evidence %s failed: %s; retry scheduled for %s",
                evidence_id,
                last_error,
                next_attempt_at,
            )
            
            record_evidence_failure(
                evidence_id=evidence_id,
                next_attempt_at=next_attempt_at,
                last_error=last_error,
            )

    def run(self) -> None:
        while True:
            try:
                self.handle_pending_evidence()
            except sqlite3.Error:
                logger.exception(
                    "Evidence database operation failed; retrying in %s seconds",
                    DATABASE_RETRY_SECONDS,
                )
                time.sleep(DATABASE_RETRY_SECONDS)
            else:
                time.sleep(EVIDENCE_CHECK_INTERVAL_SECONDS)


def run_evidence_worker(credentials_manager: CredentialsManager) -> None:
    worker = EvidenceWorker(credentials_manager)
    try:
        worker.run()
    finally:
        worker.close()


