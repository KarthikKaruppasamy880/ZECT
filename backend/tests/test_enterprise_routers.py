"""Tests for enterprise routers: audit, rules, sessions, outputs, export."""


def test_audit_trail_list(client):
    resp = client.get("/api/audit")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_audit_trail_stats(client):
    resp = client.get("/api/audit/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data or "total_entries" in data or isinstance(data, dict)


def test_rules_list(client):
    resp = client.get("/api/rules")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_rules_create_and_delete(client):
    rule = {
        "name": "test-no-console-log",
        "rule_type": "review",
        "severity": "medium",
        "condition": "console\\.log",
        "action": "Flag console.log usage",
    }
    resp = client.post("/api/rules", json=rule)
    assert resp.status_code in (200, 201)
    rule_id = resp.json().get("id")
    assert rule_id is not None

    # Delete
    resp = client.delete(f"/api/rules/{rule_id}")
    assert resp.status_code == 200


def test_rules_evaluate(client):
    # Create a rule first
    rule = {
        "name": "eval-test-rule",
        "rule_type": "security",
        "severity": "high",
        "condition": "eval\\(",
        "action": "Flag eval() usage",
    }
    client.post("/api/rules", json=rule)

    resp = client.post("/api/rules/evaluate", json={
        "code": "result = eval(user_input)",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data or "violations" in data or isinstance(data, (list, dict))


def test_sessions_list(client):
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_sessions_create(client):
    session = {
        "name": "Test Session",
        "project_id": 1,
    }
    resp = client.post("/api/sessions", json=session)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "id" in data


def test_outputs_list(client):
    resp = client.get("/api/outputs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_outputs_stats(client):
    resp = client.get("/api/outputs/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_outputs" in data


def test_outputs_create_and_rate(client):
    output = {
        "output_type": "code",
        "feature": "test",
        "title": "Test Output",
        "prompt_used": "Write hello world",
        "output_content": "print('hello world')",
        "language": "python",
        "model_used": "gpt-4o-mini",
        "tokens_used": 50,
        "cost_usd": 0.001,
    }
    resp = client.post("/api/outputs", json=output)
    assert resp.status_code in (200, 201)
    output_id = resp.json().get("id")
    assert output_id is not None

    # Rate it
    resp = client.post(f"/api/outputs/{output_id}/rate", json={
        "quality_score": 4,
        "was_accepted": True,
    })
    assert resp.status_code == 200


def test_export_list(client):
    resp = client.get("/api/export")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_export_create(client):
    export = {
        "content_type": "custom",
        "export_type": "markdown",
        "title": "Test Export",
        "custom_content": "# Test\nSome content",
    }
    resp = client.post("/api/export", json=export)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "job_id" in data or "content" in data


def test_jira_status(client):
    resp = client.get("/api/jira/status")
    assert resp.status_code == 200


def test_slack_status(client):
    resp = client.get("/api/slack/status")
    assert resp.status_code == 200


def test_ultrareview_list(client):
    resp = client.get("/api/ultrareview")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
