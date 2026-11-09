import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

from app.auth import TemporaryCredentials


def send_event(
    client: httpx.Client,
    api_url: str,
    region: str,
    credentials: TemporaryCredentials,
    payload_json: str,
) -> httpx.Response:
    """Sign and send an event using the supplied temporary credentials."""
    # Convert our credential model into the format Botocore uses for signing.
    aws_credentials = Credentials(
        access_key=credentials.access_key_id,
        secret_key=credentials.secret_access_key.get_secret_value(),
        token=credentials.session_token.get_secret_value(),
    )

    # Sign and send the same bytes. Changing the body after signing
    # would make the signature invalid.
    body = payload_json.encode("utf-8")

    request = AWSRequest(
        method="POST",
        url=api_url,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    # API Gateway uses the AWS service name "execute-api".
    # The signing region must match the region hosting the API.
    SigV4Auth(
        aws_credentials,
        "execute-api",
        region,
    ).add_auth(request)

    response = client.post(
        api_url,
        content=body,
        headers=dict(request.headers.items()),
        # A redirected request would need a signature for its new URL.
        follow_redirects=False,
    )

    # Let the event worker handle rejected requests and schedule retries.
    response.raise_for_status()

    return response

