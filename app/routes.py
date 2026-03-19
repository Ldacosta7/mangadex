from flask import Blueprint, render_template, request, jsonify
from app.recommender import chat, add_manga, load_mangas, build_user_profile

bp = Blueprint("main", __name__)

# Historique de conversation en mémoire
conversation_history = []


@bp.route("/")
def index():
    """Page principale — interface chat."""
    return render_template("index.html")


@bp.route("/chat", methods=["POST"])
def chat_endpoint():
    """Reçoit un message et retourne la réponse de Llama."""
    global conversation_history
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message vide"}), 400

    try:
        response, conversation_history = chat(user_message, conversation_history)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/add_manga", methods=["POST"])
def add_manga_endpoint():
    """Ajoute un manga à la liste de l'utilisateur."""
    data = request.get_json()
    title   = data.get("title", "").strip()
    rating  = int(data.get("rating", 3))
    comment = data.get("comment", "")

    if not title:
        return jsonify({"error": "Titre requis"}), 400

    try:
        entry = add_manga(title, rating, comment)
        return jsonify({"success": True, "manga": entry})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/profile")
def profile_endpoint():
    """Retourne le profil complet de l'utilisateur."""
    data    = load_mangas()
    profile = build_user_profile(data)
    return jsonify({
        "total":    len(data["mangas"]),
        "liked":    len(profile["liked"]),
        "disliked": len(profile["disliked"]),
        "top_tags": profile["top_liked_tags"],
        "mangas":   data["mangas"]
    })


@bp.route("/reset", methods=["POST"])
def reset_conversation():
    """Réinitialise l'historique de conversation."""
    global conversation_history
    conversation_history = []
    return jsonify({"success": True})