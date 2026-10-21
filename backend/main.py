import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from backend.agents.orchestrator import Orchestrator
from backend.config import ROOT, Settings
from backend.database.store import Store
from backend.models.schemas import (
    Assessment,
    SearchRequest,
    Transaction,
    VerificationReport,
)
from backend.rag.index import PolicyIndex
from backend.rules.engine import RuleEngine

MAX_UPLOAD = 5 * 1024 * 1024


def create_app(settings=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        store = Store(settings.data_dir)
        engine = RuleEngine(ROOT / "data/rules/rules.json")
        index = await run_in_threadpool(PolicyIndex, settings, store, ROOT / "data/policies")
        app.state.store, app.state.engine, app.state.index = store, engine, index
        app.state.orchestrator = Orchestrator(settings, engine, index, store)
        yield

    app = FastAPI(
        title="PolicyGuard AI",
        version="1.0.0",
        description="Fictional advisory compliance demonstration. Synthetic data only.",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path not in {"/docs", "/redoc", "/docs/oauth2-redirect"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
            )
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "advisory_only": True}

    @app.get("/api/system/status")
    def status():
        with app.state.store.connection() as db:
            db.execute("SELECT 1").fetchone()
        index = app.state.index
        return {
            "database": "operational",
            "llm_configured": settings.llm_configured,
            "execution_mode": "Agent Mode available (requires successful tool calls)"
            if settings.llm_configured
            else "Workflow Mode",
            "llm_status": app.state.orchestrator.last_llm_status,
            "retrieval_mode": index.mode,
            "retrieval_warning": index.warning,
            "embedding_model": settings.embedding_model,
            "policy_count": len(index.policies),
            "chunk_count": len(index.chunks),
            "statistics": app.state.store.stats(),
            "synthetic_only": True,
        }

    @app.get("/api/transactions/samples")
    def samples():
        return json.loads((ROOT / "data/sample_transactions/samples.json").read_text())

    @app.post("/api/transactions/verify", response_model=VerificationReport)
    def verify(transaction: Transaction):
        return app.state.orchestrator.verify(transaction)

    @app.get("/api/verifications")
    def history(
        assessment: Assessment | None = None,
        limit: int = Query(100, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        return [
            {
                "id": r["id"],
                "transaction_id": r["transaction_id"],
                "timestamp": r["timestamp"],
                "transaction": r["transaction"],
                "assessment": r["assessment"],
                "execution_mode": r["execution_mode"],
            }
            for r in app.state.store.history(assessment, limit, offset)
        ]

    @app.get("/api/verifications/{id}", response_model=VerificationReport)
    def report(id: str):
        result = app.state.store.get_report(id)
        if not result:
            raise HTTPException(404, "Verification not found")
        return result

    @app.get("/api/policies")
    def policies():
        return app.state.index.policies

    # Static action routes precede the dynamic policy-id route.
    @app.post("/api/policies/search")
    def search(request: SearchRequest):
        return app.state.index.search(request.query, request.top_k)

    @app.post("/api/policies/upload", status_code=201)
    async def upload(file: UploadFile):
        try:
            content = await file.read(MAX_UPLOAD + 1)
            if len(content) > MAX_UPLOAD:
                raise HTTPException(413, "Maximum upload size is 5 MiB.")
            return await run_in_threadpool(app.state.index.upload, file.filename or "", content)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            await file.close()

    @app.get("/api/policies/{id}")
    def policy(id: str):
        p = next((p for p in app.state.index.policies if p["policy_id"] == id), None)
        if not p:
            raise HTTPException(404, "Policy not found")
        return p | {
            "rules": [
                r.model_dump()
                for r in app.state.engine.rules
                if r.rule_id in p["associated_rule_ids"]
            ]
        }

    app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(ROOT / "frontend/index.html")

    return app


app = create_app()
