import bcrypt


def hash_password(password: str) -> str:
    """Return bcrypt hash of the given password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
