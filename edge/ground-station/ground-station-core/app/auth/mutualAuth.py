from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import (
    ec,
    rsa,
    padding,
)
from datetime import datetime, timezone


def load_certificate(pem_data: bytes):
    return x509.load_pem_x509_certificate(pem_data)


def verify_certificate_signature(cert, ca_cert):
    if cert.issuer != ca_cert.subject:
        raise ValueError("Certificate was not issued by trusted CA")
    ca_public_key = ca_cert.public_key()

    if isinstance(ca_public_key, ec.EllipticCurvePublicKey):
        ca_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            ec.ECDSA(cert.signature_hash_algorithm),
        )
    elif isinstance(ca_public_key, rsa.RSAPublicKey):
        ca_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
    else:
        raise ValueError("Unsupported CA public key type")

    now = datetime.now(timezone.utc)
    if now < cert.not_valid_before_utc:
        raise ValueError("Certificate is not yet valid")
    if now > cert.not_valid_after_utc:
        raise ValueError("Certificate has expired")


def verify_certificate(cert_pem: bytes, ca_cert):
    cert = load_certificate(cert_pem)
    verify_certificate_signature(cert, ca_cert)
    public_key = cert.public_key()
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("The certificate must contain an RSA public key")

    return cert, public_key
