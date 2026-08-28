import hashlib
import secrets

from app.core.config import settings

# Excludes 0/O and 1/I/L — read aloud or copied off a printed card at the
# start line, so visually ambiguous characters cause real support tickets.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_passkey(length: int = 10) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def hash_passkey(passkey: str) -> str:
    """Deterministic hash (sha256 + pepper), not bcrypt — login needs an indexed
    lookup by hash, and the passkey is high-entropy random rather than a
    user-chosen password, so bcrypt's brute-force resistance buys nothing here.
    """
    normalized = passkey.strip().upper()
    return hashlib.sha256((settings.passkey_pepper + normalized).encode()).hexdigest()


def verify_passkey(passkey: str, passkey_hash: str) -> bool:
    return secrets.compare_digest(hash_passkey(passkey), passkey_hash)
