import httpx
from pydantic import AwareDatetime, BaseModel, Field, SecretStr
from datetime import datetime, timedelta, timezone
import logging
import time
import threading

from app.retry import (
    FALLBACK_RETRY_SECONDS,
    parse_retry_after,
    retry_delay,
)

logger = logging.getLogger(__name__)


class TemporaryCredentials(BaseModel):
    access_key_id: str = Field(alias="accessKeyId")
    secret_access_key: SecretStr = Field(alias="secretAccessKey")
    session_token: SecretStr = Field(alias="sessionToken")
    expiration: AwareDatetime


class CredentialsResponse(BaseModel):
    credentials: TemporaryCredentials


def fetch_iot_credentials(
    client: httpx.Client,
    endpoint: str,
    role_alias: str,
) -> TemporaryCredentials:
    response = client.get(
        f"https://{endpoint}/role-aliases/{role_alias}/credentials"
    )
    response.raise_for_status()

    result = CredentialsResponse.model_validate(response.json())
    return result.credentials


def credentials_expiring_soon(
    credentials: TemporaryCredentials,
) -> bool:
    # Refresh early so credentials are less likely to expire during a request.
    refresh_at = credentials.expiration - timedelta(minutes=5)
    return datetime.now(timezone.utc) >= refresh_at


class CredentialsManager:
    def __init__(
        self,
        client: httpx.Client,
        endpoint: str,
        role_alias: str,
    ):
        self.client = client
        self.endpoint = endpoint
        self.role_alias = role_alias
        self._credentials: TemporaryCredentials | None = None
        self._lock = threading.Lock()

    def get_credentials(self) -> TemporaryCredentials:
        attempt = 1

        while True:
            try:
                # Both workers share this cache. The lock ensures only one worker
                # fetches fresh credentials while the other waits for the result.
                with self._lock:
                    if (
                        self._credentials is None
                        or credentials_expiring_soon(self._credentials)
                    ):
                        self._credentials = fetch_iot_credentials(
                            self.client,
                            self.endpoint,
                            self.role_alias,
                        )

                    return self._credentials

            except httpx.HTTPStatusError as error:
                response = error.response
                delay = retry_delay(
                    attempt,
                    status_code=response.status_code,
                    retry_after=parse_retry_after(
                        response.headers.get("Retry-After")
                    ),
                )
                reason = str(error)

            except httpx.RequestError as error:
                delay = retry_delay(attempt)
                reason = str(error)

            except ValueError:
                delay = timedelta(seconds=FALLBACK_RETRY_SECONDS)
                reason = "Invalid credential response"

            logger.warning(
                "Credential fetch failed: %s; retrying in %.1f seconds",
                reason,
                delay.total_seconds(),
            )

            # Wait outside the lock so the other worker can still try fetching credentials.
            time.sleep(delay.total_seconds())
            attempt += 1

    def invalidate_credentials(
        self,
        used_credentials: TemporaryCredentials,
    ) -> None:
        with self._lock:
            # Only clear the credentials that failed. The other worker may
            # already have replaced them with fresh credentials.
            if self._credentials is used_credentials:
                self._credentials = None

    