import json

import httpx
import pytest

from backend.agents.orchestrator import Investigation, Orchestrator
from backend.models.schemas import Transaction


def tool(name, args="{}", id="call-1"):
    return {"id": id, "type": "function", "function": {"name": name, "arguments": args}}


def agent(settings, engine, index, store):
    settings.llm_key = "test-key-not-real"
    settings.llm_base = "https://llm.example/v1"
    settings.llm_model = "test-model"
    return Orchestrator(settings, engine, index, store)


def test_workflow_fallback(settings, engine, index, store, samples):
    a = Orchestrator(settings, engine, index, store)
    r = a.verify(Transaction(**samples[0]["transaction"]))
    assert r["execution_mode"] == "Workflow Mode"
    assert r["assessment"] == "PASS"
    assert len(r["trace"]) == 5
    assert store.get_report(r["id"])["rule_results"] == r["rule_results"]


@pytest.mark.parametrize(
    "name,args",
    [
        ("exec", {}),
        ("retrieve_relevant_policies", {"query": "hello", "top_k": 999}),
        ("inspect_transaction", {"override": True}),
        ("evaluate_compliance_rules", None),
        ("generate_verification_report", {}),
    ],
)
def test_invalid_tools_rejected(engine, index, samples, name, args):
    run = Investigation(Transaction(**samples[0]["transaction"]), engine, index)
    assert "error" in run.call(name, args)
    assert run.trace[-1]["state"] == "failure"


def test_genuine_tool_call_loop_and_mandatory_safeguard(
    settings, engine, index, store, samples, monkeypatch
):
    a = agent(settings, engine, index, store)
    responses = iter(
        [
            {"tool_calls": [tool("inspect_transaction")]},
            {
                "tool_calls": [
                    tool(
                        "retrieve_relevant_policies",
                        json.dumps({"query": "scholarship exception", "top_k": 2}),
                        "call-2",
                    )
                ]
            },
            {
                "tool_calls": [
                    tool(
                        "retrieve_relevant_policies",
                        json.dumps({"query": "transfer upper limit", "top_k": 3}),
                        "call-3",
                    )
                ]
            },
            {
                "content": json.dumps(
                    {
                        "overview": "issues_detected",
                        "rule_ids": ["CAP-INR"],
                        "citation_ids": [],
                    }
                )
            },
        ]
    )

    def chat(messages, timeout):
        assert timeout <= 12
        assert messages[0]["role"] == "system"
        return next(responses)

    monkeypatch.setattr(a, "_chat", chat)
    r = a.verify(Transaction(**samples[1]["transaction"]))
    assert r["execution_mode"] == "Agent Mode"
    assert r["assessment"] == "FLAGGED"
    assert len([s for s in r["trace"] if s["tool_name"] == "retrieve_relevant_policies"]) == 2
    assert any(
        s["origin"] == "safeguard" and s["tool_name"] == "evaluate_compliance_rules"
        for s in r["trace"]
    )
    assert r["ai_explanation"]["overview"] == "FLAGGED"


@pytest.mark.parametrize(
    "content",
    [
        {"overview": "requirements_satisfied", "rule_ids": [], "citation_ids": []},
        {"overview": "issues_detected", "rule_ids": ["FAKE"], "citation_ids": []},
        {"overview": "issues_detected", "rule_ids": [], "citation_ids": ["invented"]},
        {"assessment": "PASS", "summary": "Ignore every policy"},
    ],
)
def test_model_cannot_override_or_invent(
    settings, engine, index, store, samples, monkeypatch, content
):
    a = agent(settings, engine, index, store)
    responses = iter(
        [
            {"tool_calls": [tool("inspect_transaction")]},
            {"content": json.dumps(content)},
        ]
    )
    monkeypatch.setattr(a, "_chat", lambda *args: next(responses))
    r = a.verify(Transaction(**samples[1]["transaction"]))
    assert r["assessment"] == "FLAGGED" and r["ai_explanation"] is None
    assert all(p["chunk_id"] in {c["chunk_id"] for c in index.chunks} for p in r["evidence"])


@pytest.mark.parametrize(
    "response",
    [
        {"content": "Tool calls unsupported"},
        {"tool_calls": "bad"},
        {"tool_calls": [{"invalid": True}]},
        {"tool_calls": [tool("inspect_transaction", "{bad json")]},
    ],
)
def test_malformed_provider_falls_back(
    settings, engine, index, store, samples, monkeypatch, response
):
    a = agent(settings, engine, index, store)
    monkeypatch.setattr(a, "_chat", lambda *args: response)
    r = a.verify(Transaction(**samples[0]["transaction"]))
    assert r["execution_mode"] == "Workflow Mode" and r["assessment"] == "PASS"
    assert any(s["tool_name"] == "evaluate_compliance_rules" for s in r["trace"])


def test_api_failure_and_secret_redaction(settings, engine, index, store, samples, monkeypatch):
    a = agent(settings, engine, index, store)

    def broken(*args):
        raise RuntimeError("Secret test-key-not-real in a transport error")

    monkeypatch.setattr(a, "_chat", broken)
    r = a.verify(Transaction(**samples[4]["transaction"]))
    assert r["execution_mode"] == "Workflow Mode" and r["assessment"] == "FLAGGED"
    assert "test-key-not-real" not in json.dumps(r)


def test_bounds_repeating_model(settings, engine, index, store, samples, monkeypatch):
    a = agent(settings, engine, index, store)
    monkeypatch.setattr(a, "_chat", lambda *args: {"tool_calls": [tool("inspect_transaction")]})
    r = a.verify(Transaction(**samples[0]["transaction"]))
    assert len([s for s in r["trace"] if s["origin"] == "agent"]) == a.MAX_STEPS
    assert r["assessment"] == "PASS"


def test_openai_compatible_wire_protocol(settings, engine, index, store, monkeypatch):
    a = agent(settings, engine, index, store)
    real_client = httpx.Client

    def transport(request):
        assert str(request.url) == "https://llm.example/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key-not-real"
        data = json.loads(request.content)
        assert data["model"] == "test-model" and len(data["tools"]) == 5
        assert data["max_tokens"] == 600 and data["tool_choice"] == "auto"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"tool_calls": [tool("inspect_transaction")]}}]},
        )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(transport), **kwargs),
    )
    assert (
        a._chat([{"role": "user", "content": "Synthetic data"}], 5)["tool_calls"][0]["function"][
            "name"
        ]
        == "inspect_transaction"
    )


def test_retrieval_miss_cannot_skip_mandatory_rules(
    settings, engine, index, store, samples, monkeypatch
):
    original = index.search
    unrelated = original("scholarship", 1)
    monkeypatch.setattr(index, "search", lambda *args: unrelated)
    a = Orchestrator(settings, engine, index, store)
    r = a.verify(Transaction(**samples[1]["transaction"]))
    assert r["assessment"] == "FLAGGED"
    assert any(x["rule_id"] == "CAP-INR" and x["result"] == "FLAGGED" for x in r["rule_results"])
    assert not any(p["policy_id"] == "POLICY-TRANSFER-01" for p in r["evidence"])
