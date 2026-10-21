import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi.encoders import jsonable_encoder


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "policyguard.sqlite3"
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS verifications (
                    id TEXT PRIMARY KEY, timestamp TEXT NOT NULL,
                    assessment TEXT NOT NULL, report TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS verification_time ON verifications(timestamp DESC);
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, metadata TEXT NOT NULL, chunks TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self):
        with sqlite3.connect(self.path, timeout=15) as db:
            db.row_factory = sqlite3.Row
            yield db

    def save_report(self, report):
        data = jsonable_encoder(report)
        with self.connection() as db:
            db.execute(
                "INSERT INTO verifications VALUES (?,?,?,?)",
                (data["id"], data["timestamp"], data["assessment"], json.dumps(data)),
            )

    def get_report(self, id):
        with self.connection() as db:
            row = db.execute("SELECT report FROM verifications WHERE id=?", (id,)).fetchone()
        return json.loads(row["report"]) if row else None

    def history(self, assessment=None, limit=100, offset=0):
        query = "SELECT report FROM verifications"
        args = []
        if assessment:
            query += " WHERE assessment=?"
            args.append(assessment)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        args.extend([limit, offset])
        with self.connection() as db:
            return [json.loads(r["report"]) for r in db.execute(query, args).fetchall()]

    def stats(self):
        with self.connection() as db:
            return dict(
                db.execute(
                    "SELECT assessment, COUNT(*) FROM verifications GROUP BY assessment"
                ).fetchall()
            )

    def save_document(self, meta, chunks):
        with self.connection() as db:
            db.execute(
                "INSERT INTO documents VALUES (?,?,?)",
                (meta["policy_id"], json.dumps(meta), json.dumps(chunks)),
            )

    def documents(self):
        with self.connection() as db:
            return [
                (json.loads(r["metadata"]), json.loads(r["chunks"]))
                for r in db.execute("SELECT * FROM documents").fetchall()
            ]
