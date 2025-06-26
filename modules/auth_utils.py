import hashlib


def hash_password(password: str) -> str:
    """Return SHA-256 hash of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()
