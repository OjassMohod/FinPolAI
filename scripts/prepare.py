"""Initialize the database and warm the local retrieval cache; prints no secrets."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.config import ROOT, Settings
from backend.database.store import Store
from backend.rag.index import PolicyIndex

settings = Settings()
index = PolicyIndex(settings, Store(settings.data_dir), ROOT / "data/policies")
print(f"Database initialized. {len(index.policies)} policies; {len(index.chunks)} chunks.")
print("Retrieval:", index.mode)
if index.warning:
    print(index.warning)
result = index.search("scholarship tuition documentation exception", 3)
assert result["passages"], "Retrieval returned no passages"
print("Retrieval smoke check passed. No transaction history was seeded.")
