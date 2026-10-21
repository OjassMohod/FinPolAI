# Executed validation

Validated in this cloud onboarding session using Linux, Python 3.12.14, CPU-only PyTorch 2.8.0, and the pinned requirements.

## Automated tests

```bash
RUN_SEMANTIC_TESTS=1 .venv/bin/python -m pytest -q
```

**85 passed, 0 failed, 0 skipped** (3.42 seconds in the final run).

This includes actual cached MiniLM inference and cosine retrieval, a separate deterministic vector-cache unit test, TF-IDF fallback tests, rule operators and five currency boundaries, missing facts, exceptions, simultaneous violations, unsupported countries/currencies, Pydantic validation, text/PDF extraction, upload persistence, immutable historical reports after an in-memory policy change, mandatory rule evaluation despite a retrieval miss, mocked LLM tool loops, unsupported/malformed tool rejection, bounded execution, failure fallback, OpenAI-compatible HTTP request shape and rejection of invented outcomes/citations.

The default invocation without `RUN_SEMANTIC_TESTS=1` intentionally skips the real-model integration test. It does not automatically prove semantic readiness.

## Live backend and browser

- Started Uvicorn with the real `scripts/start.sh`, stopped only the process started for this task, and restarted using the same script with default automatic semantic retrieval.
- `/api/system/status`: database operational, **Semantic embeddings**, no retrieval warning, LLM not configured.
- `scripts/smoke_api.py`: nine real verification requests against the running server all matched expected outcomes; each returned all 37 rule considerations, actual retrieved passages, and a persisted report identical to its subsequent GET response.
- `scripts/browser_smoke.py`, using actual Chromium through Playwright: five scenarios (PASS, FLAGGED, NEEDS INFORMATION, REVIEW REQUIRED and scholarship exception), populated forms, real backend submission, report display, recorded trace, saved-history reopening, policy search, source/rule details and Markdown upload succeeded. The mobile viewport had no horizontal document overflow. No JavaScript execution errors were observed.
- PDF and text/Markdown uploads were exercised through FastAPI tests; a real text-based PDF preserved page 1 in its chunks. Browser upload exercised Markdown separately.
- `EMBEDDING_LOCAL_ONLY=1 .venv/bin/python scripts/prepare.py` successfully loaded the cached real model and retrieved passages without a download.
- `node --check frontend/js/app.js`, Ruff checks, `git diff --check` and `pip check` passed.

These checks created synthetic audit records and a few browser reference uploads under the ignored `.runtime/` directory. They do not seed any production data.

## Model and network

The real `sentence-transformers/all-MiniLM-L6-v2` safetensors model was downloaded from Hugging Face with TLS verification intact and remote Python code disabled. The observed snapshot is `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Local model files and vectors are cached under `.runtime/`.

The initial network denial was diagnosed and resolved for this running instance. The environment configuration draft includes the Hugging Face domains and its observed CDN destination `us.aws.cdn.hf.co` alongside the other file-host routes. A saved draft is not proof of publication or restoration in a new task.

## Not externally verified

- **Live external LLM:** no `LLM_API_KEY`, `LLM_BASE_URL` or `LLM_MODEL` was supplied. Actual provider authentication, model availability and live autonomous tool choice remain unverified. Agent implementation is covered by mocked tool-call integration tests and a mocked OpenAI-compatible HTTP transport; no paid API was used. Current live requests use explicitly labeled **Workflow Mode** with real semantic RAG and deterministic rule evaluation.
- Installation/startup were validated in this Linux machine; macOS/Windows and a completely new machine were not independently tested.
- No environment publication or fresh-task snapshot restoration was performed by the agent. Review/save the configuration and publish through environment settings.
- No production security, legal/regulatory correctness or real banking integration is claimed. Limits and restrictions are fictional.
