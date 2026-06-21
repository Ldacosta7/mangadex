"""
app/database.py
Module de gestion de la base de données SQLite.
Remplace data/my_mangas.json
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "data/mangabot.db")


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite avec Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db():
    """Context manager — ouvre et ferme la connexion proprement."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crée les tables si elles n'existent pas encore."""
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS mangas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment     TEXT    DEFAULT '',
                mangadex_id TEXT    DEFAULT '',
                url         TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tags (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT    NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS manga_tags (
                manga_id INTEGER NOT NULL REFERENCES mangas(id) ON DELETE CASCADE,
                tag_id   INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
                PRIMARY KEY (manga_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    NOT NULL UNIQUE,
                history    TEXT    NOT NULL DEFAULT '[]',
                updated_at TEXT    DEFAULT (datetime('now'))
            );
        """)


def insert_manga(title: str, rating: int, comment: str = "",
                 mangadex_id: str = "", url: str = "",
                 tags: list = []) -> dict:
    """Insère un manga et ses tags. Retourne le manga inséré."""
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO mangas (title, rating, comment, mangadex_id, url)
               VALUES (?, ?, ?, ?, ?)""",
            (title.strip(), rating, comment.strip(), mangadex_id, url)
        )
        manga_id = cur.lastrowid

        for tag_name in tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,)
            )
            row = conn.execute(
                "SELECT id FROM tags WHERE name = ?", (tag_name,)
            ).fetchone()
            conn.execute(
                "INSERT OR IGNORE INTO manga_tags (manga_id, tag_id) VALUES (?, ?)",
                (manga_id, row["id"])
            )

        return get_manga_by_id(manga_id, conn)


def get_manga_by_id(manga_id: int, conn=None) -> dict:
    """Retourne un manga avec ses tags."""
    def _fetch(c):
        row = c.execute(
            "SELECT * FROM mangas WHERE id = ?", (manga_id,)
        ).fetchone()
        if not row:
            return None
        tags = [r["name"] for r in c.execute(
            """SELECT t.name FROM tags t
               JOIN manga_tags mt ON mt.tag_id = t.id
               WHERE mt.manga_id = ?""", (manga_id,)
        ).fetchall()]
        return {**dict(row), "tags": tags}

    if conn:
        return _fetch(conn)
    with db() as c:
        return _fetch(c)


def get_all_mangas() -> list:
    """Retourne tous les mangas avec leurs tags."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM mangas ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for row in rows:
            tags = [r["name"] for r in conn.execute(
                """SELECT t.name FROM tags t
                   JOIN manga_tags mt ON mt.tag_id = t.id
                   WHERE mt.manga_id = ?""", (row["id"],)
            ).fetchall()]
            result.append({**dict(row), "tags": tags})
        return result


def delete_manga(manga_id: int) -> bool:
    """Supprime un manga (cascade sur manga_tags)."""
    with db() as conn:
        cur = conn.execute("DELETE FROM mangas WHERE id = ?", (manga_id,))
        return cur.rowcount > 0


def get_history(session_id: str) -> list:
    """Retourne l'historique de conversation pour une session."""
    import json
    with db() as conn:
        row = conn.execute(
            "SELECT history FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        return json.loads(row["history"]) if row else []


def save_history(session_id: str, history: list):
    """Sauvegarde l'historique de conversation."""
    import json
    with db() as conn:
        conn.execute("""
            INSERT INTO sessions (session_id, history, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(session_id)
            DO UPDATE SET history = excluded.history,
                          updated_at = excluded.updated_at
        """, (session_id, json.dumps(history, ensure_ascii=False)))


def clear_history(session_id: str):
    """Vide l'historique d'une session."""
    with db() as conn:
        conn.execute(
            "UPDATE sessions SET history = '[]' WHERE session_id = ?",
            (session_id,)
        )


def build_profile_from_db() -> dict:
    """Construit le profil utilisateur depuis SQLite."""
    mangas = get_all_mangas()

    liked    = [m for m in mangas if m["rating"] >= 4]
    disliked = [m for m in mangas if m["rating"] <= 2]
    neutral  = [m for m in mangas if m["rating"] == 3]

    liked_tags = {}
    for m in liked:
        for tag in m.get("tags", []):
            liked_tags[tag] = liked_tags.get(tag, 0) + 1

    disliked_tags = {}
    for m in disliked:
        for tag in m.get("tags", []):
            disliked_tags[tag] = disliked_tags.get(tag, 0) + 1

    return {
        "liked":             liked,
        "disliked":          disliked,
        "neutral":           neutral,
        "top_liked_tags":    sorted(liked_tags,    key=liked_tags.get,    reverse=True)[:5],
        "top_disliked_tags": sorted(disliked_tags, key=disliked_tags.get, reverse=True)[:3],
    }