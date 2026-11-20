import os
import json
import base64
import secrets
import hashlib
import hmac

import requests

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import (
    padding,
    rsa,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import serialization

DRONE_ID = "550e8400-e29b-41d4-a716-446655440000"

GROUND_URL = f"http://{os.environ['GROUND_HOST'].rstrip('/')}:8080"

DRONE_CERT_PATH = os.environ["DRONE_CERT_PATH"]
DRONE_KEY_PATH = os.environ["DRONE_KEY_PATH"]
CA_CERT_PATH = os.environ["CA_CERT_PATH"]


SESSION_KEY_LENGTH = 32
PROTOCOL_ID = "SENTINEL-UAV-v1"


# --------------------------------------------------
# Load certificates and private key
# --------------------------------------------------
def load_certificate(path: str):
    with open(path, "rb") as file:
        return x509.load_pem_x509_certificate(file.read())


def load_private_key(path: str):
    with open(path, "rb") as file:
        return serialization.load_pem_private_key(
            file.read(),
            password=None,
        )


# --------------------------------------------------
# Base64 helpers
# --------------------------------------------------
def encode_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode_b64(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


# --------------------------------------------------
# Certificate validation
# --------------------------------------------------


def verify_certificate_signature(cert, ca_cert):

    if cert.issuer != ca_cert.subject:
        raise ValueError("Certificate was not issued by the trusted CA")

    ca_public_key = ca_cert.public_key()

    if not isinstance(ca_public_key, rsa.RSAPublicKey):
        raise ValueError("CA public key must be RSA")

    ca_public_key.verify(
        cert.signature,
        cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        cert.signature_hash_algorithm,
    )


def verify_certificate_validity(cert):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    if now < cert.not_valid_before_utc:
        raise ValueError("Certificate is not valid yet")

    if now > cert.not_valid_after_utc:
        raise ValueError("Certificate has expired")


def get_common_name(cert):
    attributes = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)

    if not attributes:
        raise ValueError("Certificate has no Common Name")

    return attributes[0].value


def verify_ground_station_certificate(gs_cert, ca_cert):

    verify_certificate_signature(gs_cert, ca_cert)
    verify_certificate_validity(gs_cert)

    gs_public_key = gs_cert.public_key()

    if not isinstance(gs_public_key, rsa.RSAPublicKey):
        raise ValueError("Ground Station certificate must contain an RSA public key")

    return gs_public_key


# --------------------------------------------------
# Verify Ground Station signature
# --------------------------------------------------


def verify_ground_station_signature(
    gs_public_key,
    transcript: bytes,
    encrypted_pms: bytes,
    signature: bytes,
):
    if not isinstance(gs_public_key, rsa.RSAPublicKey):
        raise ValueError("Ground Station public key must be RSA")
    signed_data = b"SENTINEL-KEY-AGREEMENT-v1" + transcript + encrypted_pms
    try:
        gs_public_key.verify(
            signature,
            signed_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        print("Ground Station RSA-PSS signature verified")
    except Exception as exc:
        raise ValueError(
            "Ground Station RSA-PSS signature verification failed"
        ) from exc


# --------------------------------------------------
# Decrypt pre-master secret
# --------------------------------------------------


def decrypt_pms(drone_private_key, encrypted_pms: bytes) -> bytes:

    if not isinstance(drone_private_key, rsa.RSAPrivateKey):
        raise ValueError("Drone private key must be RSA")

    return drone_private_key.decrypt(
        encrypted_pms,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


# --------------------------------------------------
# Derive session key using HKDF-SHA256
# --------------------------------------------------


def derive_session_key(
    pms: bytes,
    nonce_drone: bytes,
    nonce_gs: bytes,
) -> bytes:

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=SESSION_KEY_LENGTH,
        salt=nonce_drone + nonce_gs,
        info=b"SENTINEL-UAV-FLIGHT-SESSION-v1",
    )

    return hkdf.derive(pms)


# --------------------------------------------------
# Create key confirmation
# --------------------------------------------------


def create_key_confirmation(
    session_key: bytes,
    handshake_id: str,
    signed_data: bytes,
) -> str:

    confirmation_data = (
        b"SENTINEL-KEY-CONFIRM-v1"
        + handshake_id.encode()
        + hashlib.sha256(signed_data).digest()
    )

    confirmation = hmac.new(
        session_key,
        confirmation_data,
        hashlib.sha256,
    ).digest()
    return base64.b64encode(confirmation).decode("ascii")


def canonical_json(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# --------------------------------------------------
# Complete SENTINEL handshake
# --------------------------------------------------


def establish_session() -> bytes:

    # Load drone credentials.
    drone_cert = load_certificate(DRONE_CERT_PATH)
    drone_private_key = load_private_key(DRONE_KEY_PATH)
    ca_cert = load_certificate(CA_CERT_PATH)

    verify_certificate_signature(drone_cert, ca_cert)
    verify_certificate_validity(drone_cert)

    if not isinstance(drone_private_key, rsa.RSAPrivateKey):
        raise ValueError("Drone private key must be RSA")

    # 1. Generate a fresh 32-byte drone nonce.
    nonce_drone = secrets.token_bytes(32)

    # 2. Send initial handshake request.
    init_request = {
        "drone_id": DRONE_ID,
        "nonce_drone": encode_b64(nonce_drone),
        "drone_certificate": drone_cert.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode("ascii"),
    }

    response = requests.post(
        f"{GROUND_URL}/sentinel/handshake/init",
        json=init_request,
        verify=CA_CERT_PATH,
        timeout=15,
    )

    response.raise_for_status()
    handshake_response = response.json()

    # 3. Read Ground Station handshake response.
    handshake_id = handshake_response["handshake_id"]

    nonce_gs = decode_b64(handshake_response["nonce_gs"])
    encrypted_pms = decode_b64(handshake_response["encrypted_pms"])
    signature = decode_b64(handshake_response["signature"])

    if len(nonce_gs) != 32:
        raise ValueError("Ground Station nonce must be 32 bytes")

    gs_cert_pem = base64.b64decode(
        handshake_response["ground_station_certificate"],
        validate=True,
    )

    gs_cert = x509.load_pem_x509_certificate(gs_cert_pem)

    # 4. Verify Ground Station certificate.
    gs_public_key = verify_ground_station_certificate(
        gs_cert,
        ca_cert,
    )

    transcript = {
        "protocol": "SENTINEL-UAV-v1",
        "drone_id": DRONE_ID,
        "nonce_drone": base64.b64encode(nonce_drone).decode("ascii"),
        "nonce_gs": base64.b64encode(nonce_gs).decode("ascii"),
    }

    transcript_bytes = canonical_json(transcript)

    # 6. Reconstruct the exact data signed by the Ground Station.
    signed_data = b"SENTINEL-KEY-AGREEMENT-v1" + transcript_bytes + encrypted_pms
    # 7. Verify Ground Station signature.
    verify_ground_station_signature(
        gs_public_key,
        transcript_bytes,
        encrypted_pms,
        signature,
    )

    # 8. Decrypt PMS using drone private key.
    pms = decrypt_pms(
        drone_private_key,
        encrypted_pms,
    )

    # 9. Derive the shared session key.
    session_key = derive_session_key(
        pms,
        nonce_drone,
        nonce_gs,
    )

    # 10. Prove possession of the derived session key.
    confirmation = create_key_confirmation(
        session_key,
        handshake_id,
        signed_data,
    )

    complete_request = {
        "handshake_id": handshake_id,
        "confirmation": confirmation,
    }

    response = requests.post(
        f"{GROUND_URL}/sentinel/handshake/complete",
        json=complete_request,
        verify=CA_CERT_PATH,
        timeout=15,
    )

    response.raise_for_status()

    result = response.json()

    if result.get("status") != "authenticated":
        raise RuntimeError("Ground Station did not activate the session")

    print("SENTINEL handshake completed successfully")

    return session_key


# --------------------------------------------------
# When drone mission finish, drones should call it
# --------------------------------------------------


def revokeSession(session: bytes):
    init_request = {
        "drone_id": DRONE_ID,
        "session": base64.b64encode(session).decode("ascii"),
    }
    response = requests.post(f"{GROUND_URL}/revoke/session", json=init_request)
    response.raise_for_status()
    handshake_response = response.json()
    print(handshake_response)
    return True


def main():

    session_key = establish_session()

    print("SENTINEL authentication successful")

    # Do not print the actual session key in production.
    print("Session key fingerprint:", hashlib.sha256(session_key).hexdigest())
    revokeSession(session_key)


if __name__ == "__main__":
    main()
