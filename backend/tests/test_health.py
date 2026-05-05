"""Basic health and smoke tests for the ZECT API."""


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_routes_exist(client):
    """Verify key route prefixes return something other than 404."""
    for path in [
        "/api/projects",
        "/api/analytics/overview",
        "/api/skills",
        "/api/token-controls/usage",
    ]:
        resp = client.get(path)
        assert resp.status_code != 404, f"{path} returned 404"
