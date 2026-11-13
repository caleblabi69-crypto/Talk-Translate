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
    """Crée les tables et migre les données historiques vers un compartiment isolé."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connection(path) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                translation TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT 'legacy-unassigned'
            )
            """
        )
        history_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(history)").fetchall()
        }
        if "owner_id" not in history_columns:
            connection.execute(
                "ALTER TABLE history ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'legacy-unassigned'"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS history_owner_created_at_idx ON history(owner_id, id DESC)"
        )

        favorite_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(favorites)").fetchall()
        }
        if favorite_columns and "owner_id" not in favorite_columns:
            connection.execute("ALTER TABLE favorites RENAME TO favorites_legacy")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                translation TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner_id TEXT NOT NULL DEFAULT 'legacy-unassigned',
                UNIQUE(owner_id, text, translation, source, target)
            )
            """
        )
        if favorite_columns and "owner_id" not in favorite_columns:
            connection.execute(
                """
                INSERT INTO favorites(id, text, translation, source, target, created_at, owner_id)
                SELECT id, text, translation, source, target, created_at, 'legacy-unassigned'
                FROM favorites_legacy
                """
            )
            connection.execute("DROP TABLE favorites_legacy")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def add_history(
    database_path: str | Path,
    owner_id: str,
    text: str,
    translation: str,
    source: str,
    target: str,
    limit: int,
) -> int:
    """Enregistre la traduction et supprime les entrées les plus anciennes."""
    with _connection(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO history(text, translation, source, target, created_at, owner_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (text, translation, source, target, _timestamp(), owner_id),
        )
        item_id = int(cursor.lastrowid)
        connection.execute(
            "DELETE FROM history WHERE owner_id = ? AND id NOT IN "
            "(SELECT id FROM history WHERE owner_id = ? ORDER BY id DESC LIMIT ?)",
            (owner_id, owner_id, limit),
        )
        return item_id


def list_history(database_path: str | Path, owner_id: str, limit: int) -> list[dict[str, Any]]:
    with _connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, text, translation, source, target, created_at "
            "FROM history WHERE owner_id = ? ORDER BY id DESC LIMIT ?",
            (owner_id, limit),
        ).fetchall()
    return [_as_dict(row) for row in rows]


def delete_history_item(database_path: str | Path, owner_id: str, item_id: int) -> bool:
    with _connection(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM history WHERE owner_id = ? AND id = ?", (owner_id, item_id)
        )
        return cursor.rowcount > 0


def clear_history(database_path: str | Path, owner_id: str) -> int:
    with _connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM history WHERE owner_id = ?", (owner_id,))
        return cursor.rowcount


def add_favorite(
    database_path: str | Path, owner_id: str, text: str, translation: str, source: str, target: str
) -> tuple[int, bool]:
    """Ajoute un favori ou renvoie le favori identique déjà présent."""
    with _connection(database_path) as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO favorites(text, translation, source, target, created_at, owner_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (text, translation, source, target, _timestamp(), owner_id),
        )
        row = connection.execute(
            "SELECT id FROM favorites WHERE owner_id = ? AND text = ? AND translation = ? "
            "AND source = ? AND target = ?",
            (owner_id, text, translation, source, target),
        ).fetchone()
    if row is None:
        raise RuntimeError("Le favori enregistré est introuvable.")
    return int(row["id"]), cursor.rowcount > 0


def list_favorites(database_path: str | Path, owner_id: str) -> list[dict[str, Any]]:
    with _connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, text, translation, source, target, created_at "
            "FROM favorites WHERE owner_id = ? ORDER BY id DESC",
            (owner_id,),
        ).fetchall()
    return [_as_dict(row) for row in rows]


def delete_favorite(database_path: str | Path, owner_id: str, item_id: int) -> bool:
    with _connection(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM favorites WHERE owner_id = ? AND id = ?", (owner_id, item_id)
        )
        return cursor.rowcount > 0


def clear_favorites(database_path: str | Path, owner_id: str) -> int:
    with _connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM favorites WHERE owner_id = ?", (owner_id,))
        return cursor.rowcount
