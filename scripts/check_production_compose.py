"""Validate the rendered production Compose without retaining it as a CI artifact."""
import json
import sys

doc = json.load(sys.stdin)
services = doc["services"]
assert services["app"].get("ports"), "app must publish the single ingress"
for name in ("db", "minio"):
    assert not services[name].get("ports"), f"{name} must not publish ports"
assert services["app"].get("read_only") is True
assert services["minio"].get("read_only") is True
assert doc["networks"]["data"].get("internal") is True
rendered = str(doc).lower()
for forbidden in ("privileged", "/var/run/docker.sock", "network_mode"):
    assert forbidden not in rendered, f"forbidden production setting: {forbidden}"
print("Production Compose isolation checks passed.")
