from sqlalchemy import select

from .auth import ph
from .db import SessionLocal
from .models import Role, User


def run():
    with SessionLocal() as db:
        if db.scalar(select(User).limit(1)):
            return
        rows = [
            (
                "amministratore@example.org",
                "Amministratore Demo",
                Role.ADMIN,
                "Demo-Amministratore-2026!",
            ),
            ("richiedente@example.org", "Ada Esempio", Role.REQUESTER, "Demo-Richiedente-2026!"),
            ("secondo@example.org", "Bruno Esempio", Role.REQUESTER, "Demo-Secondo-2026!"),
            (
                "protocollo@example.org",
                "Ufficio Protocollo",
                Role.PROTOCOL_OFFICER,
                "Demo-Protocollo-2026!",
            ),
            (
                "missioni@example.org",
                "Ufficio Missioni",
                Role.MISSIONS_OFFICER,
                "Demo-Missioni-2026!",
            ),
        ]
        for email, name, role, password in rows:
            db.add(User(email=email, name=name, role=role, password_hash=ph.hash(password)))
        db.commit()


if __name__ == "__main__":
    run()
