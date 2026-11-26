import hmac
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.clientip import resolve_client_ip
from app.core.config import get_settings
from app.core.security import hash_token
from app.db import get_db
from app.models import User, UserSession

COOKIE_NAME = "xv_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def client_ip(request: Request) -> str:
    """Best-effort client address for audit logs and the per-IP limit. Render's proxy appends to
    X-Forwarded-For without clearing what the client sent, so only the entries a trusted proxy wrote
    (counted from the right, TRUSTED_PROXY_HOPS) are believed. See resolve_client_ip."""
    return resolve_client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
        get_settings().trusted_proxy_hops,
    )


def get_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Not signed in.")
    session = db.get(UserSession, hash_token(token))
    if session is None:
        raise HTTPException(401, "Not signed in.")
    if _aware(session.expires_at) <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(401, "Your session expired. Sign in again.")
    return session


def current_user(session: UserSession = Depends(get_session), db: Session = Depends(get_db)) -> User:
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Not signed in.")
    return user


def require_csrf(request: Request, session: UserSession = Depends(get_session)) -> None:
    if request.method in SAFE_METHODS:
        return
    sent = request.headers.get("x-csrf-token", "")
    # Compare bytes: compare_digest raises TypeError on non-ASCII str, which would be a 500.
    if not hmac.compare_digest(sent.encode(), session.csrf_token.encode()):
        raise HTTPException(403, "Missing or invalid CSRF token. Reload the page and try again.")


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Administrator access required.")
    return user


# Attach to every private router: authentication, then CSRF for state-changing methods.
PRIVATE = [Depends(current_user), Depends(require_csrf)]
