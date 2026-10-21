"""Local semantic vectors with an explicit, observable TF-IDF fallback."""

import hashlib
import io
import json
import logging
import os
import re
import threading
from pathlib import Path
from uuid import uuid4

import httpx
import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)
MAX_TEXT = 300_000


def extract_pages(filename: str, content: bytes):
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise ValueError("Use a PDF, UTF-8 TXT, or Markdown document.")
    if not content:
        raise ValueError("The document is empty.")
    try:
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported.")
            if len(reader.pages) > 80:
                raise ValueError("PDFs may contain at most 80 pages.")
            pages = []
            total = 0
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                total += len(text)
                if total > MAX_TEXT:
                    raise ValueError("Extracted text is too large.")
                pages.append((i, text))
        else:
            pages = [(None, content.decode("utf-8"))]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "The document could not be read. Use a text-based PDF or UTF-8 text."
        ) from exc
    if sum(len(t) for _, t in pages) > MAX_TEXT:
        raise ValueError("Extracted text is too large.")
    if not any(t.strip() for _, t in pages):
        raise ValueError("No extractable text found. Scanned PDFs need OCR before upload.")
    return pages


def chunk_pages(pages, policy_id, source, size=180, overlap=35):
    result = []
    for page, text in pages:
        words = re.sub(r"\s+", " ", text).strip().split()
        for start in range(0, len(words), size - overlap):
            passage = " ".join(words[start : start + size])
            if not passage:
                continue
            result.append(
                {
                    "chunk_id": f"{policy_id}:{page or 0}:{start}",
                    "policy_id": policy_id,
                    "source_filename": source,
                    "page": page,
                    "text": passage,
                }
            )
            if start + size >= len(words):
                break
    return result


class PolicyIndex:
    def __init__(self, settings, store, policy_dir):
        self.settings, self.store = settings, store
        self.lock = threading.RLock()
        self.cache = settings.data_dir / "embeddings"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.vectorizer = None
        self.warning = None
        self.mode = "TF-IDF fallback"
        self.chunks = []
        self.policies = []
        for p in json.loads((policy_dir / "catalog.json").read_text()):
            text = (policy_dir / p["source_document"]).read_text()
            chunks = chunk_pages([(None, text)], p["policy_id"], p["source_document"])
            self.policies.append(
                p
                | {
                    "policy_text": text,
                    "chunks": len(chunks),
                    "processing_status": "processed",
                    "indexing_status": "indexed",
                    "enforceable": True,
                }
            )
            self.chunks.extend(chunks)
        for meta, chunks in store.documents():
            self.policies.append(meta)
            self.chunks.extend(chunks)
        if settings.rag_mode not in {"auto", "semantic", "tfidf"}:
            raise ValueError("RAG_MODE must be auto, semantic, or tfidf")
        if settings.rag_mode != "tfidf":
            try:
                # Repository-local cache; no remote Python code, pickle embeddings, or TLS bypass.
                os.environ.setdefault("HF_HOME", str(settings.data_dir / "huggingface"))
                os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
                import torch
                from sentence_transformers import SentenceTransformer

                torch.set_num_threads(min(4, os.cpu_count() or 1))
                model_options = dict(
                    device="cpu",
                    cache_folder=str(settings.data_dir / "models"),
                    trust_remote_code=False,
                    model_kwargs={"use_safetensors": True},
                )
                try:
                    self.model = SentenceTransformer(
                        settings.embedding_model, local_files_only=True, **model_options
                    )
                except Exception:
                    if settings.local_only:
                        raise
                    # Fail fast on a denied host rather than spending minutes on Hub retries.
                    with httpx.Client(timeout=5, follow_redirects=True) as client:
                        response = client.head(
                            "https://huggingface.co/"
                            + settings.embedding_model
                            + "/resolve/main/config.json"
                        )
                        response.raise_for_status()
                    self.model = SentenceTransformer(
                        settings.embedding_model,
                        local_files_only=False,
                        **model_options,
                    )
                self.mode = "Semantic embeddings"
            except Exception as exc:
                self.warning = f"Embedding model unavailable ({type(exc).__name__}); TF-IDF fallback is active."
                logger.warning(self.warning)
        else:
            self.warning = "TF-IDF fallback explicitly selected via RAG_MODE=tfidf."
        self._rebuild()

    def _encode(self, texts):
        result = []
        missing = []
        positions = []
        for i, t in enumerate(texts):
            key = hashlib.sha256((self.settings.embedding_model + "\0" + t).encode()).hexdigest()
            path = self.cache / (key + ".npy")
            if path.exists():
                result.append(np.load(path, allow_pickle=False))
            else:
                result.append(None)
                missing.append(t)
                positions.append((i, path))
        if missing:
            vectors = self.model.encode(
                missing,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=16,
            )
            for (i, path), v in zip(positions, vectors):
                # Atomic cache publication, safe for concurrent refreshes.
                tmp = path.with_suffix("." + uuid4().hex + ".tmp")
                with tmp.open("wb") as handle:
                    np.save(handle, v, allow_pickle=False)
                tmp.replace(path)
                result[i] = v
        return np.asarray(result, dtype=np.float32)

    def _rebuild(self):
        texts = [c["text"] for c in self.chunks]
        if self.model:
            try:
                self.vectors = self._encode(texts)
                return
            except Exception as exc:
                logger.warning("Embedding failed: %s", type(exc).__name__)
                self.model = None
                self.mode = "TF-IDF fallback"
                self.warning = "Embedding encoding failed; TF-IDF fallback is active."
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode"
        )
        self.vectors = self.vectorizer.fit_transform(texts)

    def search(self, query, top_k=5):
        with self.lock:
            if self.model:
                try:
                    q = self.model.encode(
                        [query], normalize_embeddings=True, show_progress_bar=False
                    )[0]
                    # Stored and query vectors are L2-normalized, so dot product is cosine similarity.
                    scores = self.vectors @ q
                except Exception:
                    self.model = None
                    self.mode = "TF-IDF fallback"
                    self.warning = "Query embedding failed; TF-IDF fallback is active."
                    self._rebuild()
            if self.model is None:
                q = self.vectorizer.transform([query])
                scores = (self.vectors @ q.T).toarray().ravel()
            indices = np.argsort(-scores, kind="stable")[:top_k]
            return {
                "mode": self.mode,
                "warning": self.warning,
                "documents_searched": [p["source_document"] for p in self.policies],
                "passages": [
                    self.chunks[int(i)] | {"score": round(float(scores[i]), 5)} for i in indices
                ],
            }

    def upload(self, filename, content):
        source = Path(filename.replace("\\", "/")).name[:120]
        pages = extract_pages(source, content)
        id = "UPLOAD-" + uuid4().hex[:12]
        chunks = chunk_pages(pages, id, source)
        meta = {
            "policy_id": id,
            "name": source,
            "source_document": source,
            "version": "reference upload",
            "description": "Untrusted reference material; no executable rules activated.",
            "effective_date": None,
            "associated_rule_ids": [],
            "policy_text": "\n\n".join(t for _, t in pages),
            "chunks": len(chunks),
            "processing_status": "processed",
            "indexing_status": "indexed",
            "enforceable": False,
        }
        with self.lock:
            # Compute the new index before committing durable metadata; roll back on any error.
            old_chunks = list(self.chunks)
            try:
                self.chunks.extend(chunks)
                self._rebuild()
                self.store.save_document(meta, chunks)
                self.policies.append(meta)
            except Exception:
                self.chunks = old_chunks
                self._rebuild()
                raise
        return meta
