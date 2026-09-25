"""Backend di persistenza su SQLite (stdlib sqlite3)."""

from __future__ import annotations

import os
import sqlite3

from ..domain.models import Event
from .base import EventRepository


def _status_value(e: Event) -> str:
    return e.status.value if hasattr(e.status, "value") else e.status


class SqliteEventRepository(EventRepository):
    def __init__(self, data_dir: str, filename: str = "events.db") -> None:
        os.makedirs(data_dir, exist_ok=True)
        self._path = os.path.join(data_dir, filename)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id           TEXT PRIMARY KEY,
                title        TEXT NOT NULL,
                description  TEXT,
                organizer_id TEXT NOT NULL,
                venue        TEXT NOT NULL,
                city         TEXT NOT NULL,
                city_lower   TEXT NOT NULL,
                start_date   TEXT NOT NULL,
                end_date     TEXT NOT NULL,
                capacity     INTEGER NOT NULL,
                price        REAL NOT NULL,
                status       TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_city ON events(city_lower)")
        self._conn.commit()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event.from_dict(
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "organizer_id": row["organizer_id"],
                "venue": row["venue"],
                "city": row["city"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "capacity": row["capacity"],
                "price": row["price"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    def _upsert(self, e: Event) -> None:
        self._conn.execute(
            """
            INSERT INTO events
                (id, title, description, organizer_id, venue, city, city_lower,
                 start_date, end_date, capacity, price, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, description=excluded.description,
                organizer_id=excluded.organizer_id, venue=excluded.venue,
                city=excluded.city, city_lower=excluded.city_lower,
                start_date=excluded.start_date, end_date=excluded.end_date,
                capacity=excluded.capacity, price=excluded.price,
                status=excluded.status, created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                e.id, e.title, e.description, e.organizer_id, e.venue, e.city,
                e.city.lower(), e.start_date, e.end_date, int(e.capacity),
                float(e.price), _status_value(e), e.created_at, e.updated_at,
            ),
        )
        self._conn.commit()

    def add(self, event: Event) -> None:
        self._upsert(event)

    def get(self, event_id: str) -> Event | None:
        row = self._conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return self._row_to_event(row) if row else None

    def list(self, page, page_size, status=None, city=None):
        clauses: list[str] = []
        params: list[object] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if city is not None:
            clauses.append("city_lower = ?")
            params.append(city.lower())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        total = self._conn.execute(
            f"SELECT COUNT(*) AS c FROM events{where}", params
        ).fetchone()["c"]
        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"SELECT * FROM events{where} ORDER BY created_at, id LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        return [self._row_to_event(r) for r in rows], total

    def replace(self, event: Event) -> None:
        self._upsert(event)

    def update(self, event: Event) -> None:
        self._upsert(event)

    def delete(self, event_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self._conn.commit()
        return cur.rowcount > 0
