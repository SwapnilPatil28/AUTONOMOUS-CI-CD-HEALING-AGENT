import json
import sqlite3
import threading
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


class StorageService:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[2]
        self.data_dir = root / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "runs.db"
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert_run(self, run_id: str, payload: dict[str, Any]) -> None:
        with self.lock:
            now = datetime.now(UTC).isoformat()
            serialized = json.dumps(payload)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO runs(run_id, payload, updated_at)
                    VALUES(?, ?, ?)
                    ON CONFLICT(run_id)
                    DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
                    """,
                    (run_id, serialized, now),
                )
                conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT payload FROM runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
        if row is None:
            raise KeyError(f"Run {run_id} not found")
        return json.loads(row[0])

    def write_results_file(self, run_id: str, payload: dict[str, Any]) -> str:
        results_path = self.data_dir / f"results_{run_id}.json"
        with open(results_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
        latest_path = self.data_dir / "results.json"
        with open(latest_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
        return str(results_path)
