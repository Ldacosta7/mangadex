"""
migrate.py
Migre les données de data/my_mangas.json vers SQLite.
À lancer une seule fois.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, insert_manga

JSON_FILE = "data/my_mangas.json"
DB_FILE   = "data/mangabot.db"


def migrate():
    if not os.path.exists(JSON_FILE):
        print(f"[SKIP] {JSON_FILE} introuvable — rien à migrer.")
        return

    if os.path.exists(DB_FILE):
        answer = input(f"[WARN] {DB_FILE} existe déjà. Écraser ? (o/N) : ")
        if answer.lower() != "o":
            print("Migration annulée.")
            return
        os.remove(DB_FILE)

    init_db()

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    mangas = data.get("mangas", [])
    print(f"[INFO] {len(mangas)} mangas à migrer...")

    for m in mangas:
        insert_manga(
            title   = m.get("title", ""),
            rating  = m.get("rating", 3),
            comment = m.get("comment", ""),
            tags    = m.get("tags", []),
        )
        print(f"  ✓ {m.get('title')}")

    print(f"\n[OK] Migration terminée — {len(mangas)} mangas importés dans {DB_FILE}")


if __name__ == "__main__":
    migrate()