from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.models.schemas import Transaction
from backend.rules.engine import Rule, compare, validate_condition

EXPECTED = [
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


def test_all_scenarios(engine, samples):
    for sample, expected in zip(samples, EXPECTED):
        result = engine.evaluate(Transaction(**sample["transaction"]))
        assert result["assessment"] == expected, sample["id"]
        assert len(result["rule_results"]) == len(engine.rules)


def result_for(engine, tx, id):
    return next(x for x in engine.evaluate(Transaction(**tx))["rule_results"] if x["rule_id"] == id)


@pytest.mark.parametrize(
    "currency,cap,review,docs",
    [
        ("INR", 1000000, 500000, 200000),
        ("USD", 15000, 8000, 3000),
        ("EUR", 12000, 6000, 2500),
        ("SGD", 20000, 10000, 4000),
        ("GBP", 10000, 5000, 2000),
    ],
)
def test_currency_boundaries(engine, samples, currency, cap, review, docs):
    tx = samples[0]["transaction"] | {
        "currency": currency,
        "documents": ["source_of_funds"],
    }
    for amount, status in [(cap, "PASS"), (Decimal(cap) + Decimal(".01"), "FLAGGED")]:
        assert result_for(engine, tx | {"amount": amount}, "CAP-" + currency)["result"] == status
    for amount, status in [
        (review, "PASS"),
        (Decimal(review) + Decimal(".01"), "REVIEW REQUIRED"),
    ]:
        assert result_for(engine, tx | {"amount": amount}, "REVIEW-" + currency)["result"] == status
    assert (
        result_for(engine, tx | {"amount": docs, "documents": []}, "DOCS-" + currency)["result"]
        == "NOT APPLICABLE"
    )
    assert (
        result_for(
            engine,
            tx | {"amount": Decimal(docs) + Decimal(".01"), "documents": []},
            "DOCS-" + currency,
        )["result"]
        == "FLAGGED"
    )
    # INR numerical cap must never be compared to USD, EUR, SGD or GBP values.
    other = "USD" if currency == "INR" else "INR"
    assert result_for(engine, tx, "CAP-" + other)["result"] == "NOT APPLICABLE"


@pytest.mark.parametrize(
    "field",
    [
        "sender_name",
        "recipient_name",
        "sender_country",
        "recipient_country",
        "amount",
        "currency",
        "purpose",
        "customer_type",
        "sender_kyc",
        "recipient_verified",
        "documents",
    ],
)
def test_each_unknown_blocks_pass(engine, samples, field):
    tx = Transaction(**(samples[0]["transaction"] | {field: None}))
    assert engine.evaluate(tx)["assessment"] == "NEEDS INFORMATION"


@pytest.mark.parametrize("amount", [0, -1, "NaN", "Infinity", "0.001", True])
def test_invalid_amounts(amount):
    with pytest.raises(ValidationError):
        Transaction(amount=amount)


def test_unsupported_currency(engine, samples):
    r = engine.evaluate(Transaction(**(samples[0]["transaction"] | {"currency": "JPY"})))
    assert r["assessment"] == "FLAGGED"
    assert all(
        x["result"] == "NOT APPLICABLE"
        for x in r["rule_results"]
        if x["rule_id"].startswith("CAP-")
    )


def test_document_exception_does_not_waive_limits(engine, samples):
    tx = samples[7]["transaction"]
    assert result_for(engine, tx, "DOCS-INR")["result"] == "EXEMPT"
    assert engine.evaluate(Transaction(**(tx | {"amount": 1100000})))["assessment"] == "FLAGGED"
    assert (
        result_for(engine, tx | {"documents": ["scholarship_letter"]}, "DOCS-INR")["result"]
        == "FLAGGED"
    )
    assert result_for(engine, tx | {"documents": None}, "DOCS-INR")["result"] == "NEEDS INFORMATION"


def test_multiple_violations_and_precedence(engine, samples):
    r = engine.evaluate(Transaction(**samples[8]["transaction"]))
    assert {
        "KYC",
        "CAP-INR",
        "BUSINESS-INVOICE",
        "CORRIDOR-RECIPIENT_COUNTRY",
    }.issubset(set(r["violations"]))
    tx = samples[8]["transaction"] | {"recipient_verified": None}
    assert engine.evaluate(Transaction(**tx))["assessment"] == "FLAGGED"
    tx = samples[5]["transaction"] | {"recipient_name": None}
    assert engine.evaluate(Transaction(**tx))["assessment"] == "NEEDS INFORMATION"


@pytest.mark.parametrize(
    "op,a,b,expected",
    [
        ("gt", 2, 1, True),
        ("lt", 1, 2, True),
        ("gte", 2, 2, True),
        ("lte", 2, 2, True),
        ("eq", 2, 2, True),
        ("ne", 2, 2, False),
        ("in", "IN", ["IN"], True),
        ("not_in", "SG", ["IN"], True),
        ("contains_all", ["invoice"], ["invoice"], True),
    ],
)
def test_operators(op, a, b, expected):
    assert compare({"field": "x", "operator": op, "value": b}, {"x": a}) is expected


def test_three_valued_groups():
    known = {"field": "amount", "operator": "gt", "value": 2}
    false = {"field": "currency", "operator": "eq", "value": "USD"}
    assert compare({"all": [known, false]}, {"amount": None, "currency": "INR"}) is False
    assert compare({"any": [known, false]}, {"amount": None, "currency": "INR"}) is None
    assert compare({"not": known}, {"amount": None}) is None


@pytest.mark.parametrize(
    "condition",
    [
        {"field": "amount", "operator": "eval", "value": '__import__("os")'},
        {"field": "unknown", "operator": "eq", "value": 1},
        {"any": []},
        {"all": []},
        {"field": "amount", "operator": "gt", "value": "bad"},
    ],
)
def test_unsafe_conditions_rejected(condition):
    with pytest.raises(ValueError):
        validate_condition(condition)


def test_amount_rule_requires_currency_guard():
    with pytest.raises(ValidationError):
        Rule(
            rule_id="bad",
            policy_reference="test",
            description="unscoped",
            action="flag",
            assertion={"field": "amount", "operator": "gt", "value": 12},
        )
