"""Backend di persistenza su SQLite.

Usa solo la libreria standard ``sqlite3`` (nessun DBMS esterno). I dati vanno in un file
``users.db`` in ``DATA_DIR``. La colonna ``email_lower`` è indicizzata per la ricerca e
l'unicità case-insensitive (REQ-USR-B01/B02).
"""

from __future__ import annotations

import os
import sqlite3

from ..domain.models import User
from .base import UserRepository


def _role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else user.role


class SqliteUserRepository(UserRepository):
    """Repository utenti persistito su SQLite."""

    def __init__(self, data_dir: str, filename: str = "users.db") -> None:
        os.makedirs(data_dir, exist_ok=True)
        self._path = os.path.join(data_dir, filename)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                first_name  TEXT NOT NULL,
                last_name   TEXT NOT NULL,
                email       TEXT NOT NULL,
                email_lower TEXT NOT NULL,
                company     TEXT,
                role        TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(email_lower)"
        )
        self._conn.commit()

    # --- mapping -----------------------------------------------------------
    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User.from_dict(
            {
                "id": row["id"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "email": row["email"],
                "company": row["company"],
                "role": row["role"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    def _upsert(self, user: User) -> None:
        self._conn.execute(
            """
            INSERT INTO users
                (id, first_name, last_name, email, email_lower, company, role,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                email=excluded.email,
                email_lower=excluded.email_lower,
                company=excluded.company,
                role=excluded.role,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                user.id,
                user.first_name,
                user.last_name,
                user.email,
                user.email.lower(),
                user.company,
                _role_value(user),
                user.created_at,
                user.updated_at,
            ),
        )
        self._conn.commit()

    # --- API ---------------------------------------------------------------
    def add(self, user: User) -> None:
        self._upsert(user)

    def get(self, user_id: str) -> User | None:
        cur = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return self._row_to_user(row) if row else None

    def list(
        self,
        page: int,
        page_size: int,
        role: str | None = None,
        email: str | None = None,
    ) -> tuple[list[User], int]:
        clauses: list[str] = []
        params: list[str] = []
        if role is not None:
            clauses.append("role = ?")
            params.append(role)
        if email is not None:
            clauses.append("email_lower = ?")
            params.append(email.lower())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

        total = self._conn.execute(
            f"SELECT COUNT(*) AS c FROM users{where}", params
        ).fetchone()["c"]

        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"SELECT * FROM users{where} ORDER BY created_at, id LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        return [self._row_to_user(r) for r in rows], total

    def replace(self, user: User) -> None:
        self._upsert(user)

    def update(self, user: User) -> None:
        self._upsert(user)

    def delete(self, user_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def find_by_email(self, email_lower: str) -> User | None:
        cur = self._conn.execute(
            "SELECT * FROM users WHERE email_lower = ?", (email_lower,)
        )
        row = cur.fetchone()
        return self._row_to_user(row) if row else None
