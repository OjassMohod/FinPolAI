"""Safe, currency-scoped, three-valued declarative evaluation; no retrieval dependency."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from backend.models.schemas import Transaction

FIELDS = set(Transaction.model_fields)
OPS = {"known", "eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains_all"}


def validate_condition(node, depth=0):
    if depth > 8 or not isinstance(node, dict):
        raise ValueError("Invalid or overly nested condition")
    if set(node) in ({"all"}, {"any"}):
        children = next(iter(node.values()))
        if not isinstance(children, list) or not children or len(children) > 20:
            raise ValueError("Condition groups require 1–20 children")
        for child in children:
            validate_condition(child, depth + 1)
    elif set(node) == {"not"}:
        validate_condition(node["not"], depth + 1)
    elif set(node) == {"field", "operator", "value"}:
        f, op, v = node["field"], node["operator"], node["value"]
        if f not in FIELDS or op not in OPS:
            raise ValueError("Unknown field or operator")
        if op in {"in", "not_in", "contains_all"} and not isinstance(v, list):
            raise ValueError("Membership operators require a list")
        if op == "contains_all" and f != "documents":
            raise ValueError("contains_all requires documents")
        if op in {"gt", "gte", "lt", "lte"} and (
            f != "amount"
            or isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not Decimal(str(v)).is_finite()
        ):
            raise ValueError("Numeric comparison requires a finite amount")
        if op == "known" and v is not True:
            raise ValueError("known condition requires true")
    else:
        raise ValueError("Invalid condition shape")


def compare(node, tx):
    if "all" in node or "any" in node:
        key = "all" if "all" in node else "any"
        values = [compare(n, tx) for n in node[key]]
        if key == "all":
            return False if False in values else None if None in values else True
        return True if True in values else None if None in values else False
    if "not" in node:
        result = compare(node["not"], tx)
        return None if result is None else not result
    actual, expected, op = tx.get(node["field"]), node["value"], node["operator"]
    if actual is None:
        return None
    if op == "known":
        return True
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "in":
        return actual in expected
    if op == "not_in":
        return actual not in expected
    if op == "contains_all":
        return all(x in actual for x in expected)
    a, b = Decimal(str(actual)), Decimal(str(expected))
    if op == "gt":
        return a > b
    if op == "gte":
        return a >= b
    if op == "lt":
        return a < b
    if op == "lte":
        return a <= b
    raise ValueError("Unsupported operator")


def fields_in(node):
    if "field" in node:
        return {node["field"]}
    if "not" in node:
        return fields_in(node["not"])
    return set().union(*(fields_in(n) for n in next(iter(node.values()))))


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str
    policy_reference: str
    description: str
    assertion: dict
    when: dict | None = None
    action: Literal["flag", "manual_review"]
    exception: dict | None = None
    exception_reference: str | None = None

    @model_validator(mode="after")
    def validate_conditions(self):
        for cond in (self.assertion, self.when, self.exception):
            if cond:
                validate_condition(cond)

        # Amount rules must explicitly scope a currency in applicability.
        def compares_amount(n):
            if not n:
                return False
            if "field" in n:
                return n["field"] == "amount" and n["operator"] != "known"
            if "not" in n:
                return compares_amount(n["not"])
            return any(compares_amount(c) for c in next(iter(n.values())))

        if any(compares_amount(cond) for cond in (self.assertion, self.when, self.exception)):

            def scoped(n):
                if not n:
                    return False
                if n.get("field") == "currency" and n.get("operator") == "eq":
                    return True
                return "all" in n and any(scoped(x) for x in n["all"])

            if not scoped(self.when):
                raise ValueError("Amount rules require an explicit currency guard")
        if self.exception and not self.exception_reference:
            raise ValueError("Exceptions require a policy reference")
        return self


class RuleEngine:
    def __init__(self, rules_path: Path):
        self.rules = [Rule.model_validate(x) for x in json.loads(rules_path.read_text())]
        if len({r.rule_id for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate rule IDs")

    def evaluate(self, transaction: Transaction):
        tx = transaction.model_dump()
        results = []
        for r in self.rules:
            applies = compare(r.when, tx) if r.when else True
            actual_fields = fields_in(r.assertion) | (fields_in(r.when) if r.when else set())
            actual = {k: tx.get(k) for k in sorted(actual_fields)}
            checked = compare(r.assertion, tx)
            exception = compare(r.exception, tx) if r.exception else False
            if applies is False:
                status, explanation = (
                    "NOT APPLICABLE",
                    "Applicability condition does not match.",
                )
            elif applies is None:
                status, explanation = (
                    "NEEDS INFORMATION",
                    "Applicability cannot be determined from the available information.",
                )
            elif exception is True:
                status, explanation = (
                    "EXEMPT",
                    f"Documented exception applies: {r.exception_reference}.",
                )
            elif checked is None or (checked is False and exception is None):
                status, explanation = (
                    "NEEDS INFORMATION",
                    "Missing facts prevent this requirement or its exception from being resolved.",
                )
            elif checked:
                status, explanation = "PASS", "Configured requirement is satisfied."
            else:
                status = "FLAGGED" if r.action == "flag" else "REVIEW REQUIRED"
                explanation = (
                    "Configured requirement is not satisfied."
                    if status == "FLAGGED"
                    else "Configured condition requires manual compliance review."
                )
            results.append(
                {
                    "rule_id": r.rule_id,
                    "policy_reference": r.policy_reference,
                    "description": r.description,
                    "actual_value": actual,
                    "expected_condition": r.assertion,
                    "applicability": r.when,
                    "exception": r.exception,
                    "exception_reference": r.exception_reference,
                    "result": status,
                    "explanation": explanation,
                }
            )
        assessment = next(
            (
                s
                for s in ["FLAGGED", "NEEDS INFORMATION", "REVIEW REQUIRED"]
                if any(r["result"] == s for r in results)
            ),
            "PASS",
        )
        return {
            "assessment": assessment,
            "rule_results": results,
            "violations": [r["rule_id"] for r in results if r["result"] == "FLAGGED"],
            "unresolved": [r["rule_id"] for r in results if r["result"] == "NEEDS INFORMATION"],
        }
