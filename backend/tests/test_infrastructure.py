from fastapi.testclient import TestClient

from app.main import app


def test_health_has_security_headers_and_no_sensitive_details():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_api_is_never_publicly_cacheable(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "private, no-store"


def test_untrusted_host_is_rejected():
    client = TestClient(app, base_url="http://attacker.invalid")
    assert client.get("/health").status_code == 400
