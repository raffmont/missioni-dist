from io import BytesIO

from conftest import Testing
from docx import Document
from pypdf import PdfReader
from sqlalchemy import select

from app.models import Mission, RetentionRun, User
from app.retention import execute as retention_execute

MISSION = {
    "destination": "Città Esempio",
    "country": "Italia",
    "purpose": "Convegno scientifico sintetico",
    "transport_modes": ["Aereo", "Treno", "Auto personale"],
    "fund_code": "FONDO-DEMO",
    "cup": None,
    "fund_manager": "Responsabile Esempio",
    "planned_start": "2027-02-10",
    "planned_end": "2027-02-12",
}


def structure_roles(node):
    node = node.get_object() if hasattr(node, "get_object") else node
    if isinstance(node, list):
        return [role for child in node for role in structure_roles(child)]
    if not isinstance(node, dict):
        return []
    return ([str(node["/S"])] if "/S" in node else []) + structure_roles(node.get("/K", []))


def test_health(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_openapi_uses_date_and_transport_list_contract(client):
    schemas = client.get("/api/openapi.json").json()["components"]["schemas"]
    mission = schemas["MissionIn"]["properties"]
    assert mission["planned_start"]["format"] == "date"
    assert mission["planned_end"]["format"] == "date"
    array_variant = next(
        variant for variant in mission["transport_modes"]["anyOf"] if variant.get("type") == "array"
    )
    assert array_variant["minItems"] == 1 and array_variant["maxItems"] == 5
    assert schemas["TransportMode"]["enum"] == [
        "Aereo",
        "Treno",
        "Auto a noleggio",
        "Auto personale",
        "Auto dipartimentale",
    ]


def test_session_cookie_and_password_hash(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "uno@example.org", "password": "Password-uno!"},
    )
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(value for value in cookies if value.startswith("missioni_session="))
    csrf_cookie = next(value for value in cookies if value.startswith("missioni_csrf="))
    assert "HttpOnly" in session_cookie and "SameSite=strict" in session_cookie
    assert "HttpOnly" not in csrf_cookie and "SameSite=strict" in csrf_cookie
    with Testing() as db:
        assert db.scalar(
            select(User.password_hash).where(User.email == "uno@example.org")
        ).startswith("$argon2id$")


def test_cors_rejects_untrusted_origin(client):
    response = client.options(
        "/api/v1/missions",
        headers={"Origin": "https://malicious.example.org", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_invalid_dates_and_read_only_roles(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    invalid = dict(MISSION)
    invalid["planned_end"] = "2027-02-09"
    assert (
        client.post("/api/v1/missions", json=invalid, headers={"X-CSRF-Token": csrf}).status_code
        == 422
    )
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    officer_csrf = auth(client, "protocollo@example.org", "Password-protocollo!")
    assert (
        client.post(
            "/api/v1/missions", json=MISSION, headers={"X-CSRF-Token": officer_csrf}
        ).status_code
        == 403
    )
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": officer_csrf})
    missions_csrf = auth(client, "missioni@example.org", "Password-missioni!")
    assert client.get("/api/v1/missions").json() == []
    assert (
        client.post(
            "/api/v1/missions", json=MISSION, headers={"X-CSRF-Token": missions_csrf}
        ).status_code
        == 403
    )


def test_end_to_end_and_pdf_metadata(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    h = {"X-CSRF-Token": csrf}
    created = client.post("/api/v1/missions", json=MISSION, headers=h)
    assert created.status_code == 201
    assert created.json()["transport_modes"] == ["Aereo", "Treno", "Auto personale"]
    assert created.json()["transport_mode"] == "Aereo"
    assert created.json()["planned_start"] == "2027-02-10"
    mid = created.json()["id"]
    rendered = client.post(f"/api/v1/missions/{mid}/authorization/render?format=pdf", headers=h)
    assert rendered.status_code == 200
    reader = PdfReader(BytesIO(rendered.content))
    assert reader.metadata.title == "Richiesta di autorizzazione alla missione"
    pdf_text = reader.pages[0].extract_text()
    assert "non protocollato" in pdf_text
    assert "Aereo, Treno, Auto personale" in pdf_text
    assert "10/02/2027 – 12/02/2027" in pdf_text
    assert "08:00" not in pdf_text and "18:00" not in pdf_text
    assert bool(reader.trailer["/Root"]["/MarkInfo"]["/Marked"])
    assert reader.trailer["/Root"]["/Lang"] == "it"
    assert "/StructTreeRoot" in reader.trailer["/Root"]
    roles = structure_roles(reader.trailer["/Root"]["/StructTreeRoot"])
    assert roles.index("/H1") < roles.index("/L") < roles.index("/P")
    done = client.put(
        f"/api/v1/missions/{mid}/protocol",
        json={"protocol_number": "PROT-DEMO-001", "protocol_date": "2027-01-15"},
        headers=h,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "AUTHORIZED"


def test_docx_contains_all_transports_and_date_only(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    headers = {"X-CSRF-Token": csrf}
    mid = client.post("/api/v1/missions", json=MISSION, headers=headers).json()["id"]
    rendered = client.post(
        f"/api/v1/missions/{mid}/authorization/render?format=docx", headers=headers
    )
    document = Document(BytesIO(rendered.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Aereo, Treno, Auto personale" in text
    assert "10/02/2027 – 12/02/2027" in text
    assert "08:00" not in text and "18:00" not in text


def test_date_contract_and_legacy_transport_compatibility(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    headers = {"X-CSRF-Token": csrf}
    with_time = dict(MISSION, planned_start="2027-02-10T00:00:00Z")
    assert client.post("/api/v1/missions", json=with_time, headers=headers).status_code == 422
    no_transport = dict(MISSION)
    no_transport.pop("transport_modes")
    assert client.post("/api/v1/missions", json=no_transport, headers=headers).status_code == 422
    legacy = dict(no_transport, transport_mode="Treno")
    response = client.post("/api/v1/missions", json=legacy, headers=headers)
    assert response.status_code == 201
    assert response.json()["transport_modes"] == ["Treno"]
    assert response.json()["transport_mode"] == "Treno"
    invalid_transport = dict(MISSION, transport_modes=["Teletrasporto"])
    assert (
        client.post("/api/v1/missions", json=invalid_transport, headers=headers).status_code
        == 422
    )


def test_object_level_isolation_and_csrf(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    made = client.post("/api/v1/missions", json=MISSION, headers={"X-CSRF-Token": csrf})
    mid = made.json()["id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    csrf2 = auth(client, "due@example.org", "Password-due!")
    assert client.get(f"/api/v1/missions/{mid}").status_code == 404
    assert (
        client.patch(
            f"/api/v1/missions/{mid}", json=MISSION, headers={"X-CSRF-Token": csrf2}
        ).status_code
        == 404
    )
    assert client.post("/api/v1/missions", json=MISSION).status_code == 403


def test_csrf_cookie_survives_frontend_reload(client, auth):
    auth(client, "uno@example.org", "Password-uno!")
    token = client.cookies.get("missioni_csrf")
    assert token
    response = client.post("/api/v1/missions", json=MISSION, headers={"X-CSRF-Token": token})
    assert response.status_code == 201


def test_protocol_requires_render(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    h = {"X-CSRF-Token": csrf}
    mid = client.post("/api/v1/missions", json=MISSION, headers=h).json()["id"]
    assert (
        client.put(
            f"/api/v1/missions/{mid}/protocol",
            json={"protocol_number": "X", "protocol_date": "2027-01-01"},
            headers=h,
        ).status_code
        == 409
    )


def test_persistent_rate_limit(client):
    payload = {"email": "uno@example.org", "password": "errata"}
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    assert client.post("/api/v1/auth/login", json=payload).status_code == 429


def test_export_and_account_deletion(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    headers = {"X-CSRF-Token": csrf}
    client.post("/api/v1/missions", json=MISSION, headers=headers)
    exported = client.get("/api/v1/users/me/export")
    assert exported.status_code == 200
    assert exported.json()["missions"][0]["destination"] == "Città Esempio"
    assert exported.json()["missions"][0]["transport_modes"] == MISSION["transport_modes"]
    deleted = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"confirmation": "ELIMINA IL MIO ACCOUNT"},
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_admin_reset_changes_password(client, auth):
    requester_csrf = auth(client, "uno@example.org", "Password-uno!")
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": requester_csrf})
    admin_csrf = auth(client, "admin@example.org", "Password-amministratore!")
    with Testing() as db:
        target_id = db.scalar(select(User.id).where(User.email == "uno@example.org"))
    response = client.post(
        f"/api/v1/admin/users/{target_id}/credentials/reset",
        json={"temporary_password": "Nuova-Password-Demo-2026!"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert response.status_code == 204
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": admin_csrf})
    assert auth(client, "uno@example.org", "Nuova-Password-Demo-2026!")


def test_retention_dry_run_and_verified_delete(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    mid = client.post("/api/v1/missions", json=MISSION, headers={"X-CSRF-Token": csrf}).json()["id"]
    with Testing() as db:
        mission = db.get(Mission, mid)
        mission.updated_at = mission.updated_at.replace(year=2020)
        db.commit()
    dry = retention_execute(dry_run=True, session_factory=Testing)
    assert dry["candidates"] == 1 and dry["deleted"] == 0
    done = retention_execute(dry_run=False, session_factory=Testing)
    assert done["deleted"] == 1 and len(done["verification_hash"]) == 64
    with Testing() as db:
        assert db.get(RetentionRun, done["run_id"]) is not None
