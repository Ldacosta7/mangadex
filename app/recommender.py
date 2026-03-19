import json
import os
import ollama
from app.mangadex import search_manga, get_manga_by_tags
from dotenv import load_dotenv

load_dotenv()

MANGAS_FILE = "data/my_mangas.json"
MODEL = "llama3.2"


def load_mangas() -> dict:
    with open(MANGAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_mangas(data: dict):
    with open(MANGAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_manga(title: str, rating: int, comment: str = "") -> dict:
    data = load_mangas()
    results = search_manga(title, limit=1)
    tags = results[0]["tags"] if results else []
    entry = {"title": title, "rating": rating, "tags": tags, "comment": comment}
    data["mangas"].append(entry)
    save_mangas(data)
    return entry


def build_user_profile(data: dict) -> dict:
    liked    = [m for m in data["mangas"] if m["rating"] >= 4]
    disliked = [m for m in data["mangas"] if m["rating"] <= 2]
    neutral  = [m for m in data["mangas"] if m["rating"] == 3]

    liked_tags = {}
    for m in liked:
        for tag in m.get("tags", []):
            liked_tags[tag] = liked_tags.get(tag, 0) + 1

    disliked_tags = {}
    for m in disliked:
        for tag in m.get("tags", []):
            disliked_tags[tag] = disliked_tags.get(tag, 0) + 1

    return {
        "liked": liked,
        "disliked": disliked,
        "neutral": neutral,
        "top_liked_tags":    sorted(liked_tags,    key=liked_tags.get,    reverse=True)[:5],
        "top_disliked_tags": sorted(disliked_tags, key=disliked_tags.get, reverse=True)[:3],
    }


def build_context(profile: dict, mangadex_results: list = []) -> str:
    liked_titles    = [m["title"] for m in profile["liked"]]
    disliked_titles = [m["title"] for m in profile["disliked"]]
    all_titles      = [m["title"] for m in profile["liked"] + profile["disliked"] + profile["neutral"]]

    context = f"""
=== PROFIL UTILISATEUR ===
✅ Mangas AIMÉS (note 4-5/5)    : {', '.join(liked_titles) if liked_titles else 'Aucun encore'}
❌ Mangas PAS AIMÉS (note 1-2/5): {', '.join(disliked_titles) if disliked_titles else 'Aucun encore'}
🏷️ Tags favoris                  : {', '.join(profile['top_liked_tags']) if profile['top_liked_tags'] else 'Aucun encore'}
🚫 Tags à éviter                 : {', '.join(profile['top_disliked_tags']) if profile['top_disliked_tags'] else 'Aucun encore'}

⛔ LISTE NOIRE — NE JAMAIS RECOMMANDER CES TITRES :
{chr(10).join(f'- {t}' for t in all_titles) if all_titles else 'Aucun encore'}
"""
    if mangadex_results:
        filtered = [m for m in mangadex_results if m["title"] not in all_titles]
        context += "\n=== MANGAS DISPONIBLES SUR MANGADEX ===\n"
        for m in filtered[:5]:
            context += f"- {m['title']} ({m['year']}) | Tags: {', '.join(m['tags'][:4])} | {m['url']}\n"

    return context


def get_recommendations_context(profile: dict) -> list:
    return get_manga_by_tags(
        included_tags=profile["top_liked_tags"],
        excluded_tags=profile["top_disliked_tags"],
        limit=8
    )


def extract_titles_from_response(response: str, mangadex_results: list) -> str:
    for manga in mangadex_results:
        title = manga["title"]
        url   = manga["url"]
        if title.lower() in response.lower():
            response = response.replace(title, f"{title} ([MangaDex]({url}))")
    return response


def chat(user_message: str, history: list) -> tuple:
    data    = load_mangas()
    profile = build_user_profile(data)

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
- INTERDIT de recommander un manga de la LISTE NOIRE (déjà lus par l'utilisateur)
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
        assistant_message = extract_titles_from_response(assistant_message, mangadex_results)

    history.append({"role": "assistant", "content": assistant_message})

    return assistant_message, history