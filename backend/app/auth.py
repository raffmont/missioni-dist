import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DB

from .config import settings
from .db import get_db
from .models import Session, User

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_session(db: DB, user: User):
    sid = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    db.add(
        Session(
            id=digest(sid),
            user_id=user.id,
            csrf_hash=digest(csrf),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings().session_hours),
            revoked_at=None,
        )
    )
    db.commit()
    return sid, csrf


def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False


def current_user(request: Request, db: DB = Depends(get_db)) -> User:
    raw = request.cookies.get("missioni_session")
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessione richiesta")
    session = db.get(Session, digest(raw))
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessione scaduta")
    expires = session.expires_at.replace(tzinfo=None)
    if session.revoked_at or expires < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessione scaduta")
    if (
        request.method not in {"GET", "HEAD", "OPTIONS"}
        and digest(request.headers.get("X-CSRF-Token", "")) != session.csrf_hash
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token CSRF non valido")
    return session.user
