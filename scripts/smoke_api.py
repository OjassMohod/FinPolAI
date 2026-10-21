"""Make real local requests and verify all nine rule-derived demo outcomes."""

import os

import httpx

base = os.getenv("POLICYGUARD_URL", "http://127.0.0.1:8000")
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
with httpx.Client(base_url=base, timeout=90) as client:
    client.get("/api/health").raise_for_status()
    samples = client.get("/api/transactions/samples").json()
    assert len(samples) == len(expected)
    for sample, assessment in zip(samples, expected):
        response = client.post("/api/transactions/verify", json=sample["transaction"])
        response.raise_for_status()
        report = response.json()
        assert report["assessment"] == assessment, (sample["id"], report["assessment"])
        assert len(report["rule_results"]) == 37 and report["evidence"]
        saved = client.get("/api/verifications/" + report["id"])
        saved.raise_for_status()
        assert saved.json() == report
        print(
            sample["id"],
            report["assessment"],
            report["execution_mode"],
            report["retrieval_mode"],
        )
    print(
        "PASS: nine real requests, complete rule results, retrieved evidence and persisted reports."
    )
