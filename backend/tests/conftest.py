import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["COOKIE_SECURE"] = "false"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import ph
from app.db import Base, get_db
from app.main import app
from app.models import Role, User

engine = create_engine(
    "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
Testing = sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Testing() as db:
        db.add_all(
            [
                User(
                    email="uno@example.org",
                    name="Utente Uno",
                    role=Role.REQUESTER,
                    password_hash=ph.hash("Password-uno!"),
                ),
                User(
                    email="due@example.org",
                    name="Utente Due",
                    role=Role.REQUESTER,
                    password_hash=ph.hash("Password-due!"),
                ),
                User(
                    email="protocollo@example.org",
                    name="Protocollo",
                    role=Role.PROTOCOL_OFFICER,
                    password_hash=ph.hash("Password-protocollo!"),
                ),
                User(
                    email="admin@example.org",
                    name="Amministratore",
                    role=Role.ADMIN,
                    password_hash=ph.hash("Password-amministratore!"),
                ),
                User(
                    email="missioni@example.org",
                    name="Ufficio Missioni",
                    role=Role.MISSIONS_OFFICER,
                    password_hash=ph.hash("Password-missioni!"),
                ),
            ]
        )
        db.commit()
    yield


def override_db():
    with Testing() as db:
        yield db


app.dependency_overrides[get_db] = override_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth():
    def login(client, email, password):
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200
        return r.headers["x-csrf-token"]

    return login
