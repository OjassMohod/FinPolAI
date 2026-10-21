import json

import pytest
from fastapi.testclient import TestClient

from backend.config import ROOT, Settings
from backend.database.store import Store
from backend.main import create_app
from backend.rag.index import PolicyIndex
from backend.rules.engine import RuleEngine


@pytest.fixture
def samples():
    return json.loads((ROOT / "data/sample_transactions/samples.json").read_text())


@pytest.fixture
def engine():
    return RuleEngine(ROOT / "data/rules/rules.json")


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path, rag_mode="tfidf", llm_key="", llm_base="", llm_model="")


@pytest.fixture
def store(settings):
    return Store(settings.data_dir)


@pytest.fixture
def index(settings, store):
    return PolicyIndex(settings, store, ROOT / "data/policies")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c
