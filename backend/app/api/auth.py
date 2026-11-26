from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, PRIVATE, client_ip, current_user, get_session
from app.api.schemas import LoginIn, PasswordChange, SessionOut, UserOut
from app.core.config import get_settings
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import (
    dummy_hash, hash_password, hash_token, needs_rehash, new_csrf_token, new_session_token, verify_password,
)
from app.db import get_db
from app.models import User, UserSession
from app.services.audit import record_audit
from app.services.passwords import set_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Each attempt is counted before the password is checked, so parallel requests cannot all slip
# past the limit. A successful sign-in clears the per-account count, so only failures stick.
ip_limiter = SlidingWindowLimiter(max_events=20, window_seconds=300)
email_limiter = SlidingWindowLimiter(max_events=5, window_seconds=900)
# Changing a password needs the current one, so a stolen session cannot be used to guess it freely.
password_limiter = SlidingWindowLimiter(max_events=5, window_seconds=900)


def reset_limiters() -> None:
    ip_limiter.clear()
    email_limiter.clear()
    password_limiter.clear()


def _open_session(db: Session, user: User, request: Request, response: Response, ip: str) -> str:
    """Add a new server-side session row, set its cookie on the response and return its CSRF token.
    The caller commits."""
    settings = get_settings()
    token, csrf = new_session_token(), new_csrf_token()
    db.add(UserSession(
        id=hash_token(token), user_id=user.id, csrf_token=csrf,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.session_ttl_minutes),
        ip=ip, user_agent=(request.headers.get("user-agent") or "")[:255] or None,
    ))
    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.session_ttl_minutes * 60,
        httponly=True, secure=settings.is_production, samesite="lax", path="/",
    )
    return csrf


@router.post("/login", response_model=SessionOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    email = body.email.strip().lower()

    for limiter, key in ((ip_limiter, ip), (email_limiter, email)):
        if not limiter.try_record(key):
            raise HTTPException(
                429, "Too many sign-in attempts. Wait a few minutes and try again.",
                headers={"Retry-After": str(limiter.retry_after(key))},
            )

    user = db.scalar(select(User).where(User.email == email))
    password_ok = verify_password(user.password_hash if user else dummy_hash(), body.password)
    if user is None or not user.is_active or not password_ok:
        record_audit(db, "login_failed", user_id=user.id if user else None, ip=ip, details={"email": email[:100]})
        db.commit()
        raise HTTPException(401, "Invalid email or password.")

    email_limiter.reset(email)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    now = datetime.now(timezone.utc)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now))
    csrf = _open_session(db, user, request, response, ip)
    user.last_login_at = now
    record_audit(db, "login", user_id=user.id, ip=ip)
    db.commit()
    return SessionOut(user=UserOut.model_validate(user), csrf_token=csrf)


@router.get("/me", response_model=SessionOut)
def me(user: User = Depends(current_user), session: UserSession = Depends(get_session)):
    return SessionOut(user=UserOut.model_validate(user), csrf_token=session.csrf_token)


@router.post("/password", response_model=SessionOut, dependencies=PRIVATE)
def change_password(
    body: PasswordChange, request: Request, response: Response,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    """Change your own password. Every session is replaced, including this one, so a copied cookie
    stops working; the response carries the new session's CSRF token."""
    ip = client_ip(request)
    key = str(user.id)
    if not password_limiter.try_record(key):
        raise HTTPException(
            429, "Too many attempts. Wait a few minutes and try again.",
            headers={"Retry-After": str(password_limiter.retry_after(key))},
        )
    # 400, not 401: the app treats a 401 as an expired session and signs the user out.
    if not verify_password(user.password_hash, body.current_password):
        record_audit(db, "password_change_failed", user_id=user.id, ip=ip)
        db.commit()
        raise HTTPException(400, "Your current password is not correct.")
    if body.new_password == body.current_password:
        raise HTTPException(400, "Choose a password that is different from the current one.")

    password_limiter.reset(key)
    revoked = set_password(db, user, body.new_password)
    csrf = _open_session(db, user, request, response, ip)
    record_audit(db, "password_changed", user_id=user.id, ip=ip, details={"sessions_revoked": revoked})
    db.commit()
    return SessionOut(user=UserOut.model_validate(user), csrf_token=csrf)


@router.post("/logout", status_code=204, dependencies=PRIVATE)
def logout(
    request: Request, response: Response,
    session: UserSession = Depends(get_session), db: Session = Depends(get_db),
):
    record_audit(db, "logout", user_id=session.user_id, ip=client_ip(request))
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
