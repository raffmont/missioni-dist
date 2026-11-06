"""Configurable, auditable deletion of expired draft missions."""

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from .config import settings
from .db import SessionLocal
from .models import AuditEvent, Mission, RetentionRun, Status


def execute(
    dry_run: bool = True, at: datetime | None = None, session_factory=SessionLocal
) -> dict[str, object]:
    current = at or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=settings().retention_days)
    with session_factory() as db:
        ids = sorted(
            db.scalars(
                select(Mission.id).where(
                    Mission.status == Status.DRAFT, Mission.updated_at < cutoff
                )
            ).all()
        )
        verification = hashlib.sha256("\n".join(ids).encode()).hexdigest()
        run = RetentionRun(
            cutoff_at=cutoff,
            dry_run=dry_run,
            candidates=len(ids),
            deleted=0,
            verification_hash=verification,
        )
        db.add(run)
        db.flush()
        if ids and not dry_run:
            db.execute(delete(AuditEvent).where(AuditEvent.mission_id.in_(ids)))
            result = db.execute(delete(Mission).where(Mission.id.in_(ids)))
            run.deleted = result.rowcount
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "run_id": run.id,
            "dry_run": dry_run,
            "cutoff_at": cutoff.isoformat(),
            "candidates": len(ids),
            "deleted": run.deleted,
            "verification_hash": verification,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute", action="store_true", help="Delete candidates; default is dry-run"
    )
    print(json.dumps(execute(dry_run=not parser.parse_args().execute), sort_keys=True))
