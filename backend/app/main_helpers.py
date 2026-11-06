from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Mission, Role, User


def owned_mission(mid: str, db: Session, user: User, write: bool = False) -> Mission:
    if user.role != Role.REQUESTER:
        raise HTTPException(403, "Operazione riservata al richiedente")
    mission = db.scalar(select(Mission).where(Mission.id == mid, Mission.requester_id == user.id))
    if not mission:
        raise HTTPException(404, "Missione non trovata")
    return mission
