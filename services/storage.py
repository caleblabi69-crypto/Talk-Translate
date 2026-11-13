"""Persistance SQLite de l'historique et des favoris."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Ouvre une connexion avec les options adaptées à SQLite."""
    connection = sqlite3.connect(str(database_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _connection(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_path: str | Path) -> None:
    """Crée les tables nécessaires si elles n'existent pas encore."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connection(path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                translation TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS history_created_at_idx
                ON history(created_at DESC);
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                translation TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(text, translation, source, target)
            );
            """
        )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def add_history(
    database_path: str | Path,
    text: str,
    translation: str,
    source: str,
    target: str,
    limit: int,
) -> int:
    """Enregistre la traduction et supprime les entrées les plus anciennes."""
    with _connection(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO history(text, translation, source, target, created_at) VALUES (?, ?, ?, ?, ?)",
            (text, translation, source, target, _timestamp()),
        )
        item_id = int(cursor.lastrowid)
        connection.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)", (limit,))
        return item_id


def list_history(database_path: str | Path, limit: int) -> list[dict[str, Any]]:
    with _connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, text, translation, source, target, created_at "
            "FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_as_dict(row) for row in rows]


def delete_history_item(database_path: str | Path, item_id: int) -> bool:
    with _connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM history WHERE id = ?", (item_id,))
        return cursor.rowcount > 0


def clear_history(database_path: str | Path) -> int:
    with _connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM history")
        return cursor.rowcount


def add_favorite(
    database_path: str | Path, text: str, translation: str, source: str, target: str
) -> tuple[int, bool]:
    """Ajoute un favori ou renvoie le favori identique déjà présent."""
    with _connection(database_path) as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO favorites(text, translation, source, target, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (text, translation, source, target, _timestamp()),
        )
        row = connection.execute(
            "SELECT id FROM favorites WHERE text = ? AND translation = ? AND source = ? AND target = ?",
            (text, translation, source, target),
        ).fetchone()
    if row is None:
        raise RuntimeError("Le favori enregistré est introuvable.")
    return int(row["id"]), cursor.rowcount > 0


def list_favorites(database_path: str | Path) -> list[dict[str, Any]]:
    with _connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, text, translation, source, target, created_at "
            "FROM favorites ORDER BY id DESC"
        ).fetchall()
    return [_as_dict(row) for row in rows]


def delete_favorite(database_path: str | Path, item_id: int) -> bool:
    with _connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM favorites WHERE id = ?", (item_id,))
        return cursor.rowcount > 0


def clear_favorites(database_path: str | Path) -> int:
    with _connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM favorites")
        return cursor.rowcount
