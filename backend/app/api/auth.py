from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, PRIVATE, client_ip, current_user, get_session
from app.api.schemas import LoginIn, SessionOut, UserOut
from app.core.config import get_settings
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import (
    dummy_hash, hash_password, hash_token, needs_rehash, new_csrf_token, new_session_token, verify_password,
)
from app.db import get_db
from app.models import User, UserSession
from app.services.audit import record_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Every attempt counts toward the IP limit; only failures count toward the per-account limit.
ip_limiter = SlidingWindowLimiter(max_events=20, window_seconds=300)
email_limiter = SlidingWindowLimiter(max_events=5, window_seconds=900)


def reset_limiters() -> None:
    ip_limiter.clear()
    email_limiter.clear()


@router.post("/login", response_model=SessionOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    ip = client_ip(request)
    email = body.email.strip().lower()

    for limiter, key in ((ip_limiter, ip), (email_limiter, email)):
        if limiter.is_blocked(key):
            raise HTTPException(
                429, "Too many sign-in attempts. Wait a few minutes and try again.",
                headers={"Retry-After": str(limiter.retry_after(key))},
            )
    ip_limiter.record(ip)

    user = db.scalar(select(User).where(User.email == email))
    password_ok = verify_password(user.password_hash if user else dummy_hash(), body.password)
    if user is None or not user.is_active or not password_ok:
        email_limiter.record(email)
        record_audit(db, "login_failed", user_id=user.id if user else None, ip=ip, details={"email": email[:100]})
        db.commit()
        raise HTTPException(401, "Invalid email or password.")

    email_limiter.reset(email)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    now = datetime.now(timezone.utc)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now))
    token, csrf = new_session_token(), new_csrf_token()
    db.add(UserSession(
        id=hash_token(token), user_id=user.id, csrf_token=csrf,
        expires_at=now + timedelta(minutes=settings.session_ttl_minutes),
        ip=ip, user_agent=(request.headers.get("user-agent") or "")[:255] or None,
    ))
    user.last_login_at = now
    record_audit(db, "login", user_id=user.id, ip=ip)
    db.commit()

    response.set_cookie(
        COOKIE_NAME, token, max_age=settings.session_ttl_minutes * 60,
        httponly=True, secure=settings.is_production, samesite="lax", path="/",
    )
    return SessionOut(user=UserOut.model_validate(user), csrf_token=csrf)


@router.get("/me", response_model=SessionOut)
def me(user: User = Depends(current_user), session: UserSession = Depends(get_session)):
    return SessionOut(user=UserOut.model_validate(user), csrf_token=session.csrf_token)


@router.post("/logout", status_code=204, dependencies=PRIVATE)
def logout(
    request: Request, response: Response,
    session: UserSession = Depends(get_session), db: Session = Depends(get_db),
):
    record_audit(db, "logout", user_id=session.user_id, ip=client_ip(request))
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
