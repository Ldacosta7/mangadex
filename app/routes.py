"""
app/routes.py — v2
- Historique par session (Flask-Session) au lieu de variable globale
- Validation des inputs
- Gestion d'erreurs explicite
"""

from flask import Blueprint, render_template, request, jsonify, session
from app.recommender import chat, add_manga
from app.database import (
    get_all_mangas,
    build_profile_from_db,
    clear_history,
    delete_manga,
)

bp = Blueprint("main", __name__)


# ── HELPERS ────────────────────────────────────────────────

def get_session_id() -> str:
    """Retourne l'identifiant de session courant (créé si inexistant)."""
    if "session_id" not in session:
        import uuid
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def validate_manga_input(data: dict):
    """
    Valide les inputs d'ajout de manga.
    Lève une ValueError si les données sont invalides.
    """
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("Le titre est requis.")
    if len(title) > 200:
        raise ValueError("Titre trop long (200 caractères max).")

    try:
        rating = int(data.get("rating", 3))
    except (TypeError, ValueError):
        raise ValueError("La note doit être un entier.")
    if not 1 <= rating <= 5:
        raise ValueError("La note doit être entre 1 et 5.")

    comment = (data.get("comment") or "").strip()
    if len(comment) > 500:
        raise ValueError("Commentaire trop long (500 caractères max).")

    return title, rating, comment


# ── ROUTES ─────────────────────────────────────────────────

@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/chat", methods=["POST"])
def chat_endpoint():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON invalide"}), 400

    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Message vide"}), 400
    if len(user_message) > 1000:
        return jsonify({"error": "Message trop long (1000 caractères max)"}), 400

    try:
        session_id = get_session_id()
        response   = chat(user_message, session_id)
        return jsonify({"response": response})
    except ConnectionError:
        return jsonify({"error": "Ollama est inaccessible. Vérifiez qu'il tourne."}), 503
    except Exception as e:
        return jsonify({"error": f"Erreur serveur : {str(e)}"}), 500


@bp.route("/add_manga", methods=["POST"])
def add_manga_endpoint():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON invalide"}), 400

    try:
        title, rating, comment = validate_manga_input(data)
        entry = add_manga(title, rating, comment)
        return jsonify({"success": True, "manga": entry})
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Erreur serveur : {str(e)}"}), 500


@bp.route("/delete_manga/<int:manga_id>", methods=["DELETE"])
def delete_manga_endpoint(manga_id: int):
    try:
        ok = delete_manga(manga_id)
        if not ok:
            return jsonify({"error": "Manga introuvable"}), 404
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/profile")
def profile_endpoint():
    try:
        mangas  = get_all_mangas()
        profile = build_profile_from_db()
        return jsonify({
            "total":    len(mangas),
            "liked":    len(profile["liked"]),
            "disliked": len(profile["disliked"]),
            "top_tags": profile["top_liked_tags"],
            "mangas":   mangas,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/reset", methods=["POST"])
def reset_conversation():
    try:
        session_id = get_session_id()
        clear_history(session_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500