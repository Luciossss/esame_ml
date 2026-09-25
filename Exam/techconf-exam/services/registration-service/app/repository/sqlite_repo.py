"""Backend di persistenza su SQLite (stdlib sqlite3)."""

from __future__ import annotations

import os
import sqlite3

from ..domain.models import Registration, RegistrationStatus
from .base import RegistrationRepository


def _status_value(r: Registration) -> str:
    return r.status.value if hasattr(r.status, "value") else r.status


class SqliteRegistrationRepository(RegistrationRepository):
    def __init__(self, data_dir: str, filename: str = "registrations.db") -> None:
        os.makedirs(data_dir, exist_ok=True)
        self._path = os.path.join(data_dir, filename)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                id         TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                event_id   TEXT NOT NULL,
                amount     REAL NOT NULL,
                status     TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_reg_event ON registrations(event_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_reg_user ON registrations(user_id)")
        self._conn.commit()

    @staticmethod
    def _row(r: sqlite3.Row) -> Registration:
        return Registration.from_dict(
            {
                "id": r["id"], "user_id": r["user_id"], "event_id": r["event_id"],
                "amount": r["amount"], "status": r["status"],
                "created_at": r["created_at"], "updated_at": r["updated_at"],
            }
        )

    def _upsert(self, r: Registration) -> None:
        self._conn.execute(
            """
            INSERT INTO registrations
                (id, user_id, event_id, amount, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id=excluded.user_id, event_id=excluded.event_id,
                amount=excluded.amount, status=excluded.status,
                created_at=excluded.created_at, updated_at=excluded.updated_at
            """,
            (
                r.id, r.user_id, r.event_id, float(r.amount), _status_value(r),
                r.created_at, r.updated_at,
            ),
        )
        self._conn.commit()

    def add(self, registration: Registration) -> None:
        self._upsert(registration)

    def get(self, registration_id: str) -> Registration | None:
        row = self._conn.execute(
            "SELECT * FROM registrations WHERE id = ?", (registration_id,)
        ).fetchone()
        return self._row(row) if row else None

    def list(self, page, page_size, user_id=None, event_id=None, status=None):
        clauses: list[str] = []
        params: list[object] = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if event_id is not None:
            clauses.append("event_id = ?")
            params.append(event_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        total = self._conn.execute(
            f"SELECT COUNT(*) AS c FROM registrations{where}", params
        ).fetchone()["c"]
        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"SELECT * FROM registrations{where} ORDER BY created_at, id LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        return [self._row(r) for r in rows], total

    def update(self, registration: Registration) -> None:
        self._upsert(registration)

    def delete(self, registration_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM registrations WHERE id = ?", (registration_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def count_confirmed(self, event_id: str) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) AS c FROM registrations WHERE event_id = ? AND status = ?",
            (event_id, RegistrationStatus.CONFIRMED.value),
        ).fetchone()["c"]

    def find_confirmed(self, user_id: str, event_id: str) -> Registration | None:
        row = self._conn.execute(
            "SELECT * FROM registrations WHERE user_id = ? AND event_id = ? AND status = ?",
            (user_id, event_id, RegistrationStatus.CONFIRMED.value),
        ).fetchone()
        return self._row(row) if row else None
