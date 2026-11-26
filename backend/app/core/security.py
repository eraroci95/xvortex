import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.concurrency import Slots
from app.core.config import get_settings

_hasher = PasswordHasher()  # Argon2id with the library's current recommended parameters
_dummy_hash: str | None = None
# Each hash or verify allocates ~64 MiB, so only a few may run at once (PASSWORD_HASH_CONCURRENCY).
_hash_slots = Slots(lambda: get_settings().password_hash_concurrency)


def hash_password(password: str) -> str:
    with _hash_slots:
        return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    with _hash_slots:
        try:
            return _hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def dummy_hash() -> str:
    """Verified against when the email is unknown, so response time doesn't reveal which emails exist."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(16))
    return _dummy_hash


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
