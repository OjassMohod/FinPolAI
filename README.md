# PolicyGuard AI

An advisory banking-policy investigation workspace built in the FinPolAI repository. It combines local document retrieval, an independent deterministic rule engine, and an optional tool-calling LLM agent. The responsive HTML/CSS/vanilla JavaScript frontend talks to real FastAPI endpoints; SQLite keeps the full audit record.

**All policies, limits, corridors, names and transactions are fictional. Use synthetic data only. No payments are approved, rejected or executed.**

## Quick start

Python **3.11–3.13**, preferably 3.12; roughly 2 GB free disk for the CPU dependencies and model. Linux and macOS installation paths are provided. On Windows, use WSL. The validated environment is Linux with Python 3.12.

```bash
cd /workspace/FinPolAI  # or the directory where you cloned this repository
bash scripts/install.sh
bash scripts/start.sh
```

The server uses port **8000** and serves both the frontend and API. Visit the root of your local server in a browser. There is no separate frontend build or server. API documentation is at `/docs`; the OpenAPI schema is at `/openapi.json`. Swagger's documentation assets use jsDelivr; the main application has no external frontend assets.

For a local machine, clone normally first:

```bash
git clone https://github.com/OjassMohod/FinPolAI.git
cd FinPolAI
bash scripts/install.sh
bash scripts/start.sh
```

The install script creates `.venv`, installs a CPU-only PyTorch wheel before the pinned Python dependencies, initializes SQLite and attempts to cache the MiniLM model. It can be rerun without clearing history or changing policy files. No key, billing account, external database, JavaScript build tool or GPU is required.

For an explicit offline/fallback startup:

```bash
RAG_MODE=tfidf bash scripts/start.sh
```

To bind a development server to a cloud/container interface:

```bash
POLICYGUARD_HOST=0.0.0.0 POLICYGUARD_PORT=8000 bash scripts/start.sh
```

The default bind address is loopback. This is a local, single-user demonstration with no authentication. Use one server worker: the retrieval index is held in memory, while documents, vectors and audit data persist on disk.

## Configuration

Copy the example only if you need local overrides; keep an existing `.env`:

```bash
cp -n .env.example .env
```

Edit it locally. **Never commit or paste API keys into chat.** Environment variables take priority over `.env`; the app reads `.env` from the project root at startup. Restart after changing configuration.

| Variable | Default / purpose |
| --- | --- |
| `LLM_API_KEY` | Optional backend-only provider credential |
| `LLM_BASE_URL` | Optional OpenAI-compatible API base, including its version path; the client appends `/chat/completions` |
| `LLM_MODEL` | Optional provider model identifier; must support function/tool calling |
| `RAG_MODE` | `auto`; `semantic` also attempts MiniLM with visible fallback; `tfidf` explicitly selects the fallback |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2`; a local cached model directory is also accepted |
| `EMBEDDING_LOCAL_ONLY` | `0`; set `1` to prohibit model downloading and use cached weights or visible fallback |
| `POLICYGUARD_DATA_DIR` | `.runtime` under the checkout; use an absolute path if launching elsewhere |
| `POLICYGUARD_HOST` / `POLICYGUARD_PORT` | Start-script options, `127.0.0.1` / `8000` |

### Optional free-tier LLM

Choose a provider that currently offers a free tier **and OpenAI-compatible chat completions with tools**. Free quotas, signup requirements and supported models change, so no particular free offer or model availability is assumed. For example, a compatible provider may give you a base such as `https://api.your-provider.example/v1` and a tool-capable model identifier.

1. Obtain your own free-tier key from the chosen provider; enable only the quota you intend to use.
2. Set `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL` in the ignored `.env` or secure environment settings. Use HTTPS for remote providers. No code changes are needed to switch models.
3. In a restricted cloud environment, allow the provider's API hostname in environment settings. Bind a cloud proxy secret named `LLM_API_KEY` to that hostname if using injected credentials.
4. Restart. `/api/system/status` distinguishes **configured, untested** from tool calling verified on the last request.
5. Submit a synthetic demo. **Agent Mode** appears only after the model actually selects and successfully invokes a backend tool. Expand the recorded execution to inspect the calls.

Absent credentials, API errors, incompatible responses or unsupported tool calling fall back to **Workflow Mode**. This is deterministic orchestration, not autonomous AI. A local compatible server can also be configured; all three settings must be nonempty, even if that server accepts a dummy local-only key.

Do not send real customer data. The submitted transaction and bounded tool outputs are sent to the configured provider when enabled. Keys remain on the backend and are never included in API status, reports or public traces.

## Using the demo

1. Open **Dashboard** and choose one of nine synthetic scenarios. You can edit the populated fields.
2. Select **Verify Transaction**. The loading state waits for the real backend request; completed reports show actual recorded operations.
3. Inspect **Verification details**: outcome, next steps, unknown fields, every rule result, actual retrieved passages, source references and expandable tool execution.
4. Use **Policy knowledge base** to inspect source text and structured rule JSON, search passages, or upload reference documents.
5. Use **Audit history** to filter by outcome and reopen immutable report snapshots. Export a report as JSON from its details page.

| Scenario | Expected rule-derived assessment |
| --- | --- |
| Everyday INR 50,000, India → Singapore, both identities verified | PASS |
| INR 1,100,000 with source of funds | FLAGGED: fictional INR cap exceeded |
| INR 250,000 with an explicitly empty document list | FLAGGED: source of funds absent |
| Recipient KP | FLAGGED: unsupported and fictional restricted corridor |
| Sender KYC explicitly false | FLAGGED: identity requirement fails |
| Business INR 750,000 with invoice and source of funds | REVIEW REQUIRED: higher-value threshold |
| Amount and recipient verification unknown | NEEDS INFORMATION |
| INR 300,000 tuition with scholarship and enrollment letters | PASS: documented source-of-funds exception |
| INR 1,200,000, unverified sender, IR recipient, business without documents | FLAGGED: multiple simultaneous violations |

Expected outcomes are asserted in tests; neither the frontend nor the sample endpoint supplies precomputed results.

Three useful walkthroughs:

- **Everyday transfer:** choose scenario 01. Identity and corridor checks pass, the INR cap is respected, and no extra documents or manual review apply. The real engine returns PASS.
- **Above the cap:** choose scenario 02. Source-of-funds documentation passes, but `CAP-INR` flags the INR 1,100,000 amount against its fictional INR 1,000,000 cap. Review is also triggered; FLAGGED takes precedence.
- **Scholarship exception:** choose scenario 08. The INR 300,000 transfer would normally require source of funds. Purpose tuition plus both letters triggers `POLICY-EXCEPTION-07`, so `DOCS-INR` is EXEMPT. Identity, corridor and amount checks still run, and the overall result is PASS. Remove one letter to see the document rule flag it.

## Architecture and source map

```text
Browser: HTML + CSS + JavaScript / Fetch
                |
FastAPI — Pydantic validation — bounded agent orchestrator
                |                      |
        Local RAG search        Independent JSON rule engine
                |                      |
       Source chunks + vectors + authoritative rule results
                            |
             Grounded report + observable execution trace
                            |
                      SQLite audit snapshots
```

| Location | Responsibility |
| --- | --- |
| `backend/main.py` | FastAPI routes, lifespan, static frontend, upload limits |
| `backend/models/schemas.py` | Transaction validation and report schemas |
| `backend/rules/engine.py` | Validated declarative, three-valued evaluation |
| `backend/rag/index.py` | PDF/TXT/MD extraction, chunking, local vectors, fallback |
| `backend/agents/orchestrator.py` | OpenAI-compatible client, safe tools, bounded investigation and reports |
| `backend/database/store.py` | Idempotent SQLite schema v1, metadata and complete audit snapshots |
| `frontend/` | Responsive four-view interface, live API integration, report export |
| `data/policies/` | Eight fictional readable policies and versioned catalog |
| `data/rules/rules.json` | 37 executable structured rules |
| `data/sample_transactions/` | Nine synthetic inputs |
| `tests/` | Rule, RAG, agent, wire protocol and API tests |
| `scripts/` | Repeatable install/start, preparation, API and optional browser checks |
| `prompt.md` | Original project requirements and implementation decisions |

### RAG

Text-based PDFs use pypdf and preserve page numbers. UTF-8 TXT/Markdown uses native Python decoding. Whitespace-normalized text is chunked into 180 words with 35-word overlap, retaining policy IDs, filenames, chunk IDs and pages. Uploads are limited to 5 MiB, 80 PDF pages and 300,000 extracted characters. Encrypted, unreadable, empty or scanned PDFs fail with useful errors; no OCR is provided.

MiniLM runs locally on CPU. Its L2-normalized sentence vectors are cached as `.npy` files with pickle loading disabled. Queries use the same model; NumPy dot product computes cosine similarity. Model ID plus source text forms each cache key. Top-k is configurable from 1 to 10. Retrieved passages and similarity scores are the actual index results; zero similarity is possible and is not proof that a passage applies.

The first uncached semantic run downloads model files (roughly 90 MB of weights plus tokenizer/configuration) from Hugging Face. Dependencies are larger. Required destinations include `huggingface.co` and its file host `cas-bridge.xethub.hf.co`; the observed download used `us.aws.cdn.hf.co`, and some routes use `cdn-lfs.huggingface.co` or `cdn-lfs-us-1.huggingface.co`. No TLS, checksum, or certificate checks are disabled. Only safetensors weights are loaded; remote Python model code is disabled. Once cached, `EMBEDDING_LOCAL_ONLY=1` runs offline.

If model loading or encoding fails, **TF-IDF fallback** is explicitly shown in system status, search results and reports. This is vector-based lexical retrieval and **does not demonstrate semantic embeddings**. Semantic acceptance must be validated separately after model access is available.

Uploads add untrusted searchable text and metadata to SQLite and the index. Raw binary uploads are processed in memory and discarded. Uploads never generate, change or activate executable rules. Their embedded instructions cannot register tools or override the agent's system instructions.

### Rule engine

Rules are validated structured JSON: assertions, optional applicability conditions, optional explicit exceptions, action and policy reference. Conditions support `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains_all`, `known`, `all`, `any` and `not`. No `eval`, code execution or dynamic expressions are used. Amount rules require an explicit currency guard; amounts use Decimal. Currency schedules are separate and there is no live or implicit FX conversion.

All 37 configured rules are considered on every request, independent of retrieval and the LLM. Individual results are PASS, FLAGGED, NEEDS INFORMATION, REVIEW REQUIRED, NOT APPLICABLE or EXEMPT. Overall precedence is:

**FLAGGED > NEEDS INFORMATION > REVIEW REQUIRED > PASS**

Unknown applicability is unresolved, never presumed false. `null` documents means unknown; `[]` means a known empty list and can establish a missing-document violation. A known violation outranks missing information; both remain visible. Exceptions must be established from known facts and only waive their specific rule.

To extend policies, explicitly review/edit `data/rules/rules.json`, update the readable policy and catalog together, bump the policy version, add meaningful tests, and restart the single server. Uploaded prose alone is never enforceable. Past reports retain their original text evidence, actual values, rule conditions, exceptions, versions and outcomes.

### Agent and reporting

Five real read-only tools are exposed: `inspect_transaction`, `retrieve_relevant_policies`, `evaluate_compliance_rules`, `identify_missing_information`, `generate_verification_report`. Every tool's arguments are validated with Pydantic; extra properties, invalid counts, unknown tools and invalid sequencing are rejected and traced.

The LLM chooses which tool to call and whether to retrieve again. Limits: six model turns, twelve selected tool calls, 600 output tokens per turn, twelve seconds per HTTP request, and a 45-second investigation deadline. HTTP requests do not follow redirects. Mandatory server safeguards complete inspection, retrieval, full rule evaluation, missing-information detection and report generation regardless of model choices or failures.

Reports are assembled from tool outputs. The model may select an overview and actual rule/citation IDs for explanation highlights. Unknown IDs, mismatched outcomes, arbitrary prose or malformed selections are discarded. The server renders wording from authoritative rule outputs. This deliberately constrains free-form explanation to prevent invented requirements, citations and outcome changes. No private reasoning is requested or displayed.

The trace records actual tools, inputs, output summaries, outputs, origin, status, order and duration. The frontend shows the completed trace after the synchronous request; live SSE/polling is not implemented. Mode and failures remain visible.

### Persistence

`.runtime/policyguard.sqlite3` contains append-only report records and uploaded source metadata/text/chunks. Idempotent initialization uses SQLite schema version 1 and WAL. `.runtime/embeddings` caches vectors, `.runtime/models` caches weights, and `.runtime/pip-cache` may retain dependency downloads. No process is assumed to survive a cloud snapshot; use the start script in a new task. Back up the SQLite database using SQLite's backup facilities while the server is running, or copy the database with its WAL files after stopping the server. No user data is required or generated outside the synthetic demo.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Process readiness |
| GET | `/api/system/status` | Database, retrieval mode, model configuration, statistics |
| GET | `/api/transactions/samples` | Nine synthetic input scenarios |
| POST | `/api/transactions/verify` | Validate, investigate, evaluate, persist, return report |
| GET | `/api/verifications` | Assessment filter, `limit` (1–100), `offset` |
| GET | `/api/verifications/{id}` | Complete original report |
| GET | `/api/policies` | Source text and metadata |
| GET | `/api/policies/{id}` | Source text plus associated structured rules |
| POST | `/api/policies/search` | JSON `query`, `top_k` |
| POST | `/api/policies/upload` | Multipart `file` |

## Validation

```bash
.venv/bin/python -m pytest -q
node --check frontend/js/app.js  # optional syntax check; Node is not needed to run the app
```

The default tests use temporary SQLite databases, explicit TF-IDF and mocked LLM responses. They do not require a key or download model weights. Coverage includes currency boundaries, missing values, exceptions, precedence, safe operators, PDF extraction, upload persistence, source preservation, real API requests, all nine scenarios, restart persistence, malformed tools, bounded loops, failure fallback, provider wire format and rejection of invented LLM outcomes/citations.

After successfully caching MiniLM, explicitly verify real semantic retrieval:

```bash
.venv/bin/python scripts/prepare.py
RUN_SEMANTIC_TESTS=1 .venv/bin/python -m pytest tests/test_rag.py::test_real_semantic_retrieval_opt_in -q
```

That test **fails** if real semantic embeddings are unavailable; it never counts TF-IDF as semantic success. The default suite skips it explicitly. The vector-cache unit test uses a small test encoder and does not validate MiniLM quality.

Against a running server, make representative real requests (adds nine synthetic audit records):

```bash
.venv/bin/python scripts/smoke_api.py
```

Optional browser smoke testing needs Playwright and an installed Chromium. These are development-only tools, not app dependencies:

```bash
.venv/bin/python -m pip install playwright
# Supply the path of your installed Chromium; the tested Linux machine has /usr/bin/chromium.
CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/browser_smoke.py
```

The browser check submits five outcomes, opens history and policy details, searches sources, uploads a real reference and checks mobile overflow and JavaScript errors. It adds synthetic history records and one reference document; screenshots go to `/tmp`.

See **VALIDATION.md** for results actually executed in this cloud machine and remaining blockers. A mocked tool-call test is not evidence of a live external LLM. A TF-IDF success is not evidence of MiniLM retrieval.

## Known limitations and next steps

- Actual MiniLM model access and live LLM provider access depend on your network/credential settings. The app remains useful with clearly labeled Workflow Mode and TF-IDF fallback.
- Fictional rules cover only the listed countries, purposes, currencies and documents. They are not real regulatory advice, sanctions screening or legal compliance.
- No authentication, multi-tenant isolation, production upload sandbox, OCR, document deletion UI or distributed index synchronization. Run locally as a single synthetic-data demo, with one worker.
- Report requests are synchronous; the UI displays genuine recorded traces after completion. There is no live streaming progress.
- LLM explanations use grounded selections and templates rather than unrestricted generated prose.
- Source documents are not automatically converted into enforceable rules. Explicit structured policy review remains necessary.
- A future version could add human rule approval, richer policy versioning, OCR, authentication, SSE progress, a vector database, and Airwallex sandbox ingestion. No real banking integration is implemented here.
