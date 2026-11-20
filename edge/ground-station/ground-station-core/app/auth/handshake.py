import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import (
    rsa,
    padding,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from app.auth.db import save_flight_session
from app.auth.mutualAuth import load_certificate, verify_certificate_signature
from typing import cast

CA_CERT_PATH = os.environ["CA_CERT_PATH"]
GS_CERT_PATH = os.environ["GS_CERT_PATH"]
GS_KEY_PATH = os.environ["GS_KEY_PATH"]


with open(CA_CERT_PATH, "rb") as f:
    CA_CERT = x509.load_pem_x509_certificate(f.read())

with open(GS_CERT_PATH, "rb") as f:
    GS_CERT_PEM = f.read()


with open(GS_KEY_PATH, "rb") as key_file:
    GS_PRIVATE_KEY = cast(
        RSAPrivateKey,
        serialization.load_pem_private_key(key_file.read(), password=None),
    )

# In-memory pending handshakes.
# Use cache mechanisms
pending_handshakes = {}

PBKDF2_ITERATIONS = 10_000
SESSION_KEY_LENGTH = 32


def b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def b64decode(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def canonical_json(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_drone_certificate(cert_pem: bytes, ca_cert):
    cert = load_certificate(cert_pem)

    verify_certificate_signature(cert, ca_cert)

    public_key = cert.public_key()

    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("Drone certificate must contain an RSA public key")

    return cert, public_key


def derive_session_key(
    pms: bytes,
    nonce_drone: bytes,
    nonce_gs: bytes,
) -> bytes:

    salt = nonce_drone + nonce_gs
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=SESSION_KEY_LENGTH,
        salt=salt,
        info=b"SENTINEL-UAV-FLIGHT-SESSION-v1",
    )
    return hkdf.derive(pms)


def create_handshake(drone_id: str, nonce_drone: bytes, drone_cert_pem: bytes):
    if len(nonce_drone) != 32:
        raise ValueError("Drone nonce must be 32 bytes")

    drone_cert, drone_public_key = verify_drone_certificate(
        drone_cert_pem,
        CA_CERT,
    )

    nonce_gs = secrets.token_bytes(32)
    pms = secrets.token_bytes(32)

    # Bind identity, both nonces and flight plan to the signature.
    transcript = {
        "protocol": "SENTINEL-UAV-v1",
        "drone_id": drone_id,
        "nonce_drone": base64.b64encode(nonce_drone).decode("ascii"),
        "nonce_gs": base64.b64encode(nonce_gs).decode("ascii"),
    }

    transcript_bytes = canonical_json(transcript)

    # encrypting pre-mmaster secret
    encrypted_pms = drone_public_key.encrypt(
        pms,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    signed_data = b"SENTINEL-KEY-AGREEMENT-v1" + transcript_bytes + encrypted_pms
    signature = GS_PRIVATE_KEY.sign(
        signed_data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

    session_key = derive_session_key(
        pms,
        nonce_drone,
        nonce_gs,
    )

    handshake_id = secrets.token_urlsafe(32)

    confirmation_data = (
        b"SENTINEL-KEY-CONFIRM-v1"
        + handshake_id.encode()
        + hashlib.sha256(signed_data).digest()
    )

    pending_handshakes[handshake_id] = {
        "drone_id": drone_id,
        "session_key": session_key,
        "confirmation_data": confirmation_data,
        "created_at": time.time(),
    }

    return {
        "handshake_id": handshake_id,
        "nonce_gs": b64encode(nonce_gs),
        "encrypted_pms": b64encode(encrypted_pms),
        "signature": b64encode(signature),
        "ground_station_certificate": b64encode(GS_CERT_PEM),
    }


def complete_handshake(
    handshake_id: str,
    drone_confirmation: str,
):
    # Retrieve the pending handshake from memory using its unique ID.
    # The pending handshake contains the drone identity,
    # derived session key, and expected confirmation data.
    pending = pending_handshakes.get(handshake_id)

    if pending is None:
        raise ValueError("Unknown or expired handshake")

    # Calculate the expected HMAC using the session key derived during the RSA key agreement.
    expected = hmac.new(
        pending["session_key"],
        pending["confirmation_data"],
        hashlib.sha256,
    ).digest()

    # Decode the Base64 confirmation received from the drone into its original binary HMAC representation.
    received = b64decode(drone_confirmation)

    # 5. Compare both HMAC values using a constant-time comparison.
    # This prevents timing-based attacks during verification.
    if not hmac.compare_digest(expected, received):
        # 6. Reject the handshake and remove its pending state
        # to prevent reuse of a failed handshake.
        pending_handshakes.pop(handshake_id, None)
        raise ValueError("Session key confirmation failed")

    save_flight_session(
        pending["drone_id"],
        pending["session_key"],
    )

    # 8. Remove the pending handshake because authentication has completed successfully. It must not be reused.
    pending_handshakes.pop(handshake_id, None)

    # 9. Return the authentication result to the drone.
    return {
        "status": "authenticated",
        "drone_id": pending["drone_id"],
    }
