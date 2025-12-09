import sqlite3
from typing import Iterable, Dict, Any, List


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS skills (
            skill_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source_span TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS series (
            series_id TEXT PRIMARY KEY,
            skill_id TEXT NOT NULL,
            label TEXT NOT NULL,
            units TEXT NOT NULL,
            meta TEXT,
            FOREIGN KEY(skill_id) REFERENCES skills(skill_id)
        );
        CREATE TABLE IF NOT EXISTS values_tbl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT NOT NULL,
            level_index INTEGER NOT NULL,
            value REAL NOT NULL,
            diff_to_prev REAL,
            is_jump INTEGER NOT NULL,
            FOREIGN KEY(series_id) REFERENCES series(series_id)
        );
        CREATE INDEX IF NOT EXISTS idx_values_series_level ON values_tbl(series_id, level_index);
        CREATE TABLE IF NOT EXISTS analysis (
            series_id TEXT PRIMARY KEY,
            is_linear INTEGER NOT NULL,
            trend TEXT NOT NULL,
            min REAL,
            max REAL,
            count INTEGER NOT NULL,
            jump_points TEXT NOT NULL,
            FOREIGN KEY(series_id) REFERENCES series(series_id)
        );
        """
    )


def upsert_skill(conn: sqlite3.Connection, skill_id: str, name: str, source_span: str) -> None:
    conn.execute(
        """
        INSERT INTO skills(skill_id, name, source_span)
        VALUES (?, ?, ?)
        ON CONFLICT(skill_id) DO UPDATE SET name=excluded.name, source_span=excluded.source_span, updated_at=CURRENT_TIMESTAMP
        """,
        (skill_id, name, source_span),
    )


def upsert_series(conn: sqlite3.Connection, series_id: str, skill_id: str, label: str, units: str, meta_json: str) -> None:
    conn.execute(
        """
        INSERT INTO series(series_id, skill_id, label, units, meta)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(series_id) DO UPDATE SET label=excluded.label, units=excluded.units, meta=excluded.meta
        """,
        (series_id, skill_id, label, units, meta_json),
    )


def replace_values(conn: sqlite3.Connection, series_id: str, rows: Iterable[Dict[str, Any]]) -> None:
    conn.execute("DELETE FROM values_tbl WHERE series_id=?", (series_id,))
    conn.executemany(
        """
        INSERT INTO values_tbl(series_id, level_index, value, diff_to_prev, is_jump)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                series_id,
                r["level_index"],
                r["value"],
                r.get("diff_to_prev"),
                1 if r.get("is_jump") else 0,
            )
            for r in rows
        ],
    )


def upsert_analysis(conn: sqlite3.Connection, series_id: str, a: Dict[str, Any], jump_points_json: str) -> None:
    conn.execute(
        """
        INSERT INTO analysis(series_id, is_linear, trend, min, max, count, jump_points)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(series_id) DO UPDATE SET is_linear=excluded.is_linear, trend=excluded.trend, min=excluded.min, max=excluded.max, count=excluded.count, jump_points=excluded.jump_points
        """,
        (
            series_id,
            1 if a.get("is_linear") else 0,
            a.get("trend") or "mixed",
            a.get("min"),
            a.get("max"),
            a.get("count") or 0,
            jump_points_json,
        ),
    )

