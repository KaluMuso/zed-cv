#!/usr/bin/env python3
"""Generate a VAPID key pair for Web Push. Run once; store keys in env."""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import base64


def b64url_public_key(public_key) -> str:
    numbers = public_key.public_numbers()
    raw = b"\x04" + numbers.x.to_bytes(32, "big") + numbers.y.to_bytes(32, "big")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def main() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_b64 = b64url_public_key(public_key)
    print("VAPID_PRIVATE_KEY (OCI backend .env):")
    print(priv_pem)
    print("VAPID_PUBLIC_KEY / NEXT_PUBLIC_VAPID_PUBLIC_KEY:")
    print(pub_b64)


if __name__ == "__main__":
    main()
