"""
app/recommender.py — v2
Utilise SQLite via app.database à la place de my_mangas.json
"""

import os
import ollama
from app.mangadex import search_manga, get_manga_by_tags
from app.database import (
    init_db,
    insert_manga,
    build_profile_from_db,
    get_history,
    save_history,
)
from dotenv import load_dotenv

load_dotenv()
init_db()  # Crée les tables au démarrage si elles n'existent pas

MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


# ── MANGA ──────────────────────────────────────────────────

def add_manga(title: str, rating: int, comment: str = "") -> dict:
    """Ajoute un manga avec ses tags récupérés depuis MangaDex."""
    results    = search_manga(title, limit=1)
    tags       = results[0]["tags"] if results else []
    mangadex_id = results[0]["id"]  if results else ""
    url        = results[0]["url"]  if results else ""
    return insert_manga(title, rating, comment, mangadex_id, url, tags)


# ── RAG ────────────────────────────────────────────────────

def build_context(profile: dict, mangadex_results: list = []) -> str:
    """Construit le contexte RAG à injecter dans le prompt Llama."""
    liked_titles    = [m["title"] for m in profile["liked"]]
    disliked_titles = [m["title"] for m in profile["disliked"]]
    all_titles      = [m["title"] for m in
                       profile["liked"] + profile["disliked"] + profile["neutral"]]

    context = f"""
=== PROFIL UTILISATEUR ===
✅ Mangas AIMÉS (note 4-5/5)    : {', '.join(liked_titles) or 'Aucun encore'}
❌ Mangas PAS AIMÉS (note 1-2/5): {', '.join(disliked_titles) or 'Aucun encore'}
🏷️ Tags favoris                  : {', '.join(profile['top_liked_tags']) or 'Aucun encore'}
🚫 Tags à éviter                 : {', '.join(profile['top_disliked_tags']) or 'Aucun encore'}

⛔ LISTE NOIRE — NE JAMAIS RECOMMANDER :
{chr(10).join(f'- {t}' for t in all_titles) or 'Aucun encore'}
"""
    if mangadex_results:
        filtered = [m for m in mangadex_results if m["title"] not in all_titles]
        context += "\n=== MANGAS DISPONIBLES SUR MANGADEX ===\n"
        for m in filtered[:5]:
            context += f"- {m['title']} ({m['year']}) | Tags: {', '.join(m['tags'][:4])}\n"

    return context


def extract_titles_from_response(response: str, mangadex_results: list) -> str:
    """Injecte les vrais liens MangaDex dans la réponse — jamais Llama."""
    for manga in mangadex_results:
        title = manga["title"]
        url   = manga["url"]
        if title.lower() in response.lower():
            response = response.replace(title, f"{title} ([MangaDex]({url}))")
    return response


def get_recommendations_context(profile: dict) -> list:
    """Récupère des mangas pertinents depuis MangaDex selon le profil."""
    return get_manga_by_tags(
        included_tags=profile["top_liked_tags"],
        excluded_tags=profile["top_disliked_tags"],
        limit=8
    )


# ── CHAT ───────────────────────────────────────────────────

def chat(user_message: str, session_id: str) -> str:
    """
    Envoie un message à Llama avec contexte RAG.
    L'historique est persisté en SQLite par session_id.
    """
    profile  = build_profile_from_db()
    history  = get_history(session_id)

    # Fetch MangaDex uniquement si demande de recommandation
    mangadex_results = []
    keywords = ["recommand", "suggest", "propose", "similaire", "similar",
                "conseil", "trouv", "like", "cherch"]
    if any(kw in user_message.lower() for kw in keywords):
        mangadex_results = get_recommendations_context(profile)

    context = build_context(profile, mangadex_results)

    system_prompt = f"""Tu es MangaBot, un expert passionné de manga qui fait des recommandations ultra-personnalisées.
Tu connais parfaitement le profil de l'utilisateur grâce à ces données :

{context}

RÈGLES STRICTES :
- INTERDIT de recommander un manga de la LISTE NOIRE
- Recommande uniquement des mangas qui correspondent aux tags favoris
- Évite absolument les tags de la liste à éviter
- N'invente JAMAIS de liens, ne mets AUCUN lien dans ta réponse
- Justifie chaque recommandation en lien avec les goûts de l'utilisateur
- Réponds dans la langue de l'utilisateur (français ou anglais)
- Sois précis, enthousiaste et concis
"""

    history.append({"role": "user", "content": user_message})

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}] + history
    )

    assistant_message = response["message"]["content"]

    if mangadex_results:
        assistant_message = extract_titles_from_response(
            assistant_message, mangadex_results
        )

    history.append({"role": "assistant", "content": assistant_message})
    save_history(session_id, history)

    return assistant_message