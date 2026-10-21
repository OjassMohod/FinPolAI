import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from tests.test_rag import text_pdf


def test_health_frontend_and_openapi(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert "PolicyGuard" in client.get("/").text
    assert client.get("/static/js/app.js").status_code == 200
    assert client.get("/static/css/app.css").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/transactions/verify" in schema["paths"]
    assert client.get("/docs").status_code == 200


def test_samples_end_to_end_persistence(client, settings):
    samples = client.get("/api/transactions/samples").json()
    expected = [
        "PASS",
        "FLAGGED",
        "FLAGGED",
        "FLAGGED",
        "FLAGGED",
        "REVIEW REQUIRED",
        "NEEDS INFORMATION",
        "PASS",
        "FLAGGED",
    ]
    ids = []
    for sample, outcome in zip(samples, expected):
        r = client.post("/api/transactions/verify", json=sample["transaction"])
        assert r.status_code == 200, r.text
        report = r.json()
        ids.append(report["id"])
        assert report["assessment"] == outcome
        assert report["policy_versions"] and report["evidence"]
        assert any(s["tool_name"] == "evaluate_compliance_rules" for s in report["trace"])
        assert client.get("/api/verifications/" + report["id"]).json() == report
    assert len(set(ids)) == 9
    assert len(client.get("/api/verifications").json()) == 9
    assert len(client.get("/api/verifications?assessment=FLAGGED").json()) == 5
    assert len(client.get("/api/verifications?limit=2&offset=2").json()) == 2
    with TestClient(create_app(settings)) as fresh:
        assert fresh.get("/api/verifications/" + ids[0]).json()["assessment"] == "PASS"
        assert sum(fresh.get("/api/system/status").json()["statistics"].values()) == 9


@pytest.mark.parametrize(
    "tx",
    [
        {"amount": -1},
        {"sender_country": "India"},
        {"currency": "usd"},
        {"documents": ["passport"]},
        {"untrusted_field": "bad"},
        {"sender_kyc": "false"},
    ],
)
def test_invalid_requests(client, tx):
    response = client.post("/api/transactions/verify", json=tx)
    assert response.status_code == 422 and response.json()["detail"]


def test_unknown_missing_is_not_pass(client):
    r = client.post("/api/transactions/verify", json={})
    assert r.status_code == 200 and r.json()["assessment"] == "NEEDS INFORMATION"


def test_policy_api_upload_and_search(client):
    p = client.get("/api/policies").json()[0]
    details = client.get("/api/policies/" + p["policy_id"]).json()
    assert details["rules"] and details["policy_text"]
    count = len(client.app.state.engine.rules)
    for filename, content in [
        ("demo.txt", b"Unique lunar settlement policy reference."),
        ("guide.md", b"# Planetary settlement references"),
        ("demo.pdf", text_pdf()),
    ]:
        r = client.post("/api/policies/upload", files={"file": (filename, content)})
        assert r.status_code == 201, r.text
        assert r.json()["indexing_status"] == "indexed" and r.json()["associated_rule_ids"] == []
    assert len(client.app.state.engine.rules) == count
    r = client.post("/api/policies/search", json={"query": "lunar settlement", "top_k": 2})
    assert r.json()["passages"][0]["source_filename"] == "demo.txt"
    assert client.post("/api/policies/search", json={"query": "x", "top_k": 999}).status_code == 422
    assert (
        client.post("/api/policies/upload", files={"file": ("bad.pdf", b"bad")}).status_code == 422
    )
    assert (
        client.post(
            "/api/policies/upload",
            files={"file": ("big.txt", b"a" * (5 * 1024 * 1024 + 1))},
        ).status_code
        == 413
    )


def test_unknown_ids_and_filter(client):
    assert client.get("/api/verifications/no-such-id").status_code == 404
    assert client.get("/api/policies/no-such-id").status_code == 404
    assert client.get("/api/verifications?assessment=FAKE").status_code == 422


def test_past_report_is_immutable_after_policy_changes(client, samples):
    before = client.post("/api/transactions/verify", json=samples[0]["transaction"]).json()
    rule = next(r for r in client.app.state.engine.rules if r.rule_id == "CAP-INR")
    rule.assertion["value"] = 1
    policy = next(
        p for p in client.app.state.index.policies if p["policy_id"] == "POLICY-TRANSFER-01"
    )
    policy["version"] = "2.0"
    after = client.post("/api/transactions/verify", json=samples[0]["transaction"]).json()
    assert after["assessment"] == "FLAGGED"
    saved = client.get("/api/verifications/" + before["id"]).json()
    assert saved == before
    assert saved["assessment"] == "PASS"
    assert (
        next(p for p in saved["policy_versions"] if p["policy_id"] == "POLICY-TRANSFER-01")[
            "version"
        ]
        == "1.0"
    )
    assert (
        next(r for r in saved["rule_results"] if r["rule_id"] == "CAP-INR")["expected_condition"][
            "value"
        ]
        == 1000000
    )
