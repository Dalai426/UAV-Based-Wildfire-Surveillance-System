import logging
import os
import ssl
import threading
import time

import httpx

from app.auth import CredentialsManager
from app.event_worker import run_event_worker
from app.evidence_worker import run_evidence_worker


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # The IoT credentials endpoint uses mutual TLS:
    # we verify the server and authenticate with our device certificate.
    tls = ssl.create_default_context(
        cafile=os.environ["IOT_CA_PATH"],
    )
    tls.load_cert_chain(
        certfile=os.environ["IOT_CERT_PATH"],
        keyfile=os.environ["IOT_KEY_PATH"],
    )

    # Use separate clients because only credential fetching needs mutual TLS.
    # Event requests authenticate through AWS signatures instead.
    with (
        httpx.Client(verify=tls, timeout=15) as credentials_client,
        httpx.Client(timeout=15) as api_client,
    ):
        # Both workers share cached credentials. The manager's lock prevents
        # them from refreshing credentials at the same time.
        credentials_manager = CredentialsManager(
            client=credentials_client,
            endpoint=os.environ["IOT_CREDENTIALS_ENDPOINT"],
            role_alias=os.environ["IOT_ROLE_ALIAS"],
        )

        # Separate threads let event delivery continue during video uploads.
        # Daemon threads allow the process to exit if either worker fails.
        workers = [
            threading.Thread(
                target=run_event_worker,
                args=(api_client, credentials_manager),
                name="event-worker",
                daemon=True,
            ),
            threading.Thread(
                target=run_evidence_worker,
                args=(credentials_manager,),
                name="evidence-worker",
                daemon=True,
            ),
        ]

        for worker in workers:
            worker.start()

        # Both workers should run indefinitely. If one stops, exit so
        # Compose can restart the service rather than leave it partly running.
        while all(worker.is_alive() for worker in workers):
            time.sleep(1)

        raise RuntimeError("A cloud-sync worker stopped")


if __name__ == "__main__":
    main()

    