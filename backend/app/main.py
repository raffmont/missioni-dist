import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from .auth import current_user, new_session, ph, verify_password
from .config import settings
from .db import get_db
from .documents import docx, pdf
from .models import AuditEvent, Authorization, LoginThrottle, Mission, Role, Status, User
from .models import Session as AuthSession
from .schemas import (
    CredentialResetIn,
    DeleteAccountIn,
    LoginIn,
    MissionIn,
    MissionOut,
    MissionPatch,
    ProtocolIn,
    UserOut,
)

app = FastAPI(
    title="Missioni DIST", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[host.strip() for host in settings().allowed_hosts.split(",") if host.strip()],
)

# Imported after app construction to avoid coupling the Sprint C router to legacy routes.
from .sprint_c import router as sprint_c_router  # noqa: E402

app.include_router(sprint_c_router)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.update(
        {
            "Content-Security-Policy": (
                "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
            ),
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
        }
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.exception_handler(HTTPException)
async def problem(_, exc):
    return JSONResponse(
        {"type": "about:blank", "title": str(exc.detail), "status": exc.status_code},
        status_code=exc.status_code,
        media_type="application/problem+json",
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness verifies dependencies without returning their details."""
    try:
        db.execute(text("SELECT 1"))
        object_store = __import__("app.object_store", fromlist=["store"]).store()
        if not object_store.local:
            object_store.client.head_bucket(Bucket=object_store.bucket)
    except Exception as exc:
        raise HTTPException(503, "Dipendenze non disponibili") from exc
    return {"status": "ready"}


@app.post("/api/v1/auth/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, request: Request, db: Session = Depends(get_db)):
    remote = request.client.host if request.client else "unknown"
    key = hashlib.sha256(f"{payload.email.lower()}|{remote}".encode()).hexdigest()
    throttle = db.get(LoginThrottle, key)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if throttle and throttle.blocked_until and throttle.blocked_until.replace(tzinfo=None) > now:
        raise HTTPException(429, "Troppi tentativi. Riprovare più tardi")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        if not throttle or now - throttle.window_started.replace(tzinfo=None) > timedelta(
            minutes=15
        ):
            throttle = LoginThrottle(key_hash=key, failures=0, window_started=now)
        throttle.failures += 1
        if throttle.failures >= 5:
            throttle.blocked_until = now + timedelta(minutes=15)
        db.add(throttle)
        db.commit()
        raise HTTPException(401, "Credenziali non valide")
    if throttle:
        db.delete(throttle)
        db.commit()
    sid, csrf = new_session(db, user)
    response.set_cookie(
        "missioni_session",
        sid,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="strict",
        max_age=settings().session_hours * 3600,
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf
    response.set_cookie(
        "missioni_csrf",
        csrf,
        httponly=False,
        secure=settings().cookie_secure,
        samesite="strict",
        max_age=settings().session_hours * 3600,
        path="/",
    )
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role.value)


@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role.value)


@app.get("/api/v1/users/me/export")
def export_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    missions = list(db.scalars(select(Mission).where(Mission.requester_id == user.id)))
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role.value},
        "missions": [
            {
                "id": m.id,
                "destination": m.destination,
                "country": m.country,
                "purpose": m.purpose,
                "transport_modes": m.transport_modes,
                "transport_mode": m.transport_mode,
                "fund_code": m.fund_code,
                "cup": m.cup,
                "fund_manager": m.fund_manager,
                "planned_start": m.planned_start.isoformat(),
                "planned_end": m.planned_end.isoformat(),
                "status": m.status.value,
                "protocol_number": m.authorization.protocol_number if m.authorization else None,
                "protocol_date": (
                    m.authorization.protocol_date.isoformat()
                    if m.authorization and m.authorization.protocol_date
                    else None
                ),
            }
            for m in missions
        ],
    }


@app.delete("/api/v1/users/me", status_code=204)
def delete_me(
    data: DeleteAccountIn,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if data.confirmation != "ELIMINA IL MIO ACCOUNT":
        raise HTTPException(422, "Conferma non valida")
    mission_ids = list(db.scalars(select(Mission.id).where(Mission.requester_id == user.id)))
    if mission_ids:
        db.execute(delete(AuditEvent).where(AuditEvent.mission_id.in_(mission_ids)))
        db.execute(delete(Mission).where(Mission.id.in_(mission_ids)))
    db.execute(delete(AuditEvent).where(AuditEvent.actor_id == user.id))
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.delete(user)
    db.commit()
    response.delete_cookie("missioni_session", path="/")
    response.delete_cookie("missioni_csrf", path="/")


@app.post("/api/v1/admin/users/{uid}/credentials/reset", status_code=204)
def reset_credentials(
    uid: str,
    data: CredentialResetIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role != Role.ADMIN:
        raise HTTPException(403, "Operazione riservata all'amministratore")
    target = db.get(User, uid)
    if not target:
        raise HTTPException(404, "Utente non trovato")
    target.password_hash = ph.hash(data.temporary_password)
    for session in db.scalars(
        select(AuthSession).where(AuthSession.user_id == uid, AuthSession.revoked_at.is_(None))
    ):
        session.revoked_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="credentials.admin_reset",
            metadata_redacted='{"target":"redacted"}',
        )
    )
    db.commit()


@app.post("/api/v1/auth/logout", status_code=204)
def logout(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for s in db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    ):
        s.revoked_at = datetime.now(timezone.utc)
    db.commit()
    response.delete_cookie("missioni_session", path="/")


def scoped(db: Session, user: User):
    q = select(Mission)
    if user.role == Role.REQUESTER:
        q = q.where(Mission.requester_id == user.id)
    elif user.role == Role.PROTOCOL_OFFICER:
        q = q.where(Mission.status.in_([Status.AUTHORIZATION_READY, Status.AUTHORIZED]))
    else:
        q = q.where(False)
    return q


def get_mission(mid: str, db: Session, user: User) -> Mission:
    m = db.scalar(scoped(db, user).where(Mission.id == mid))
    if not m:
        raise HTTPException(404, "Missione non trovata")
    return m


@app.get("/api/v1/missions", response_model=list[MissionOut])
def list_missions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return list(db.scalars(scoped(db, user).order_by(Mission.created_at.desc())))


@app.post("/api/v1/missions", response_model=MissionOut, status_code=201)
def create_mission(
    data: MissionIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    if user.role != Role.REQUESTER:
        raise HTTPException(403, "Operazione riservata al richiedente")
    m = Mission(**data.model_dump(), requester_id=user.id)
    db.add(m)
    db.flush()
    db.add(AuditEvent(actor_id=user.id, mission_id=m.id, action="mission.created"))
    db.commit()
    return m


@app.get("/api/v1/missions/{mid}", response_model=MissionOut)
def read_mission(mid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return get_mission(mid, db, user)


@app.patch("/api/v1/missions/{mid}", response_model=MissionOut)
def update_mission(
    mid: str, data: MissionPatch, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    m = get_mission(mid, db, user)
    if m.requester_id != user.id:
        raise HTTPException(403, "Sola lettura")
    for k, v in data.model_dump().items():
        setattr(m, k, v)
    m.version += 1
    m.status = Status.DRAFT
    db.add(AuditEvent(actor_id=user.id, mission_id=m.id, action="mission.updated"))
    db.commit()
    return m


@app.post("/api/v1/missions/{mid}/authorization/render")
def render(
    mid: str, format: str = "pdf", db: Session = Depends(get_db), user: User = Depends(current_user)
):
    m = get_mission(mid, db, user)
    if m.requester_id != user.id and user.role != Role.PROTOCOL_OFFICER:
        raise HTTPException(403, "Accesso negato")
    owner = db.get(User, m.requester_id)
    auth = m.authorization or Authorization(mission_id=m.id, document_version=0)
    auth.rendered_at = datetime.now(timezone.utc)
    auth.document_version += 1
    m.status = Status.AUTHORIZATION_READY
    db.add_all(
        [auth, AuditEvent(actor_id=user.id, mission_id=m.id, action="authorization.rendered")]
    )
    db.commit()
    body = docx(m, owner) if format == "docx" else pdf(m, owner)
    media = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "docx"
        else "application/pdf"
    )
    return Response(
        body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="autorizzazione-{m.id}.{format}"'},
    )


@app.put("/api/v1/missions/{mid}/protocol", response_model=MissionOut)
def protocol(
    mid: str, data: ProtocolIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    m = get_mission(mid, db, user)
    if m.requester_id != user.id:
        raise HTTPException(403, "Solo il richiedente registra il protocollo ricevuto")
    if not m.authorization or not m.authorization.rendered_at:
        raise HTTPException(409, "Generare prima l'autorizzazione")
    m.authorization.protocol_number = data.protocol_number
    m.authorization.protocol_date = data.protocol_date
    m.status = Status.AUTHORIZED
    db.add(AuditEvent(actor_id=user.id, mission_id=m.id, action="protocol.recorded"))
    db.commit()
    return m


# The production image contains the built SPA. Mounting it here keeps one application
# ingress and avoids introducing another reverse proxy in Docker Compose.
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
