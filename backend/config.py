"""Runtime configuration. All persistent generated files live outside source data."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("POLICYGUARD_DATA_DIR", str(ROOT / ".runtime"))
        ).resolve()
    )
    rag_mode: str = field(default_factory=lambda: os.getenv("RAG_MODE", "auto"))
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )
    local_only: bool = field(default_factory=lambda: os.getenv("EMBEDDING_LOCAL_ONLY", "0") == "1")
    llm_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_base: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))

    @property
    def llm_configured(self):
        return bool(self.llm_key and self.llm_base and self.llm_model)
