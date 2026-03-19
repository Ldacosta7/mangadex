import requests

BASE_URL = "https://api.mangadex.org"


def search_manga(title: str, limit: int = 5) -> list:
    """Cherche des mangas par titre sur MangaDex."""
    try:
        r = requests.get(f"{BASE_URL}/manga", params={
            "title": title,
            "limit": limit,
            "availableTranslatedLanguage[]": ["en", "fr"],
            "order[relevance]": "desc"
        }, timeout=10)
        r.raise_for_status()

        results = []
        for manga in r.json().get("data", []):
            attrs = manga.get("attributes", {})
            title_data = attrs.get("title", {})
            desc_data = attrs.get("description", {})
            results.append({
                "id": manga.get("id"),
                "title": title_data.get("en") or title_data.get("fr") or next(iter(title_data.values()), "Unknown"),
                "description": (desc_data.get("en") or desc_data.get("fr") or next(iter(desc_data.values()), ""))[:300],
                "tags": [
                    tag["attributes"]["name"].get("en", "")
                    for tag in attrs.get("tags", [])
                    if tag.get("attributes", {}).get("name")
                ],
                "status": attrs.get("status", ""),
                "year": attrs.get("year", ""),
                "url": f"https://mangadex.org/title/{manga.get('id')}"
            })
        return results

    except Exception as e:
        print(f"[MangaDex Error] search_manga: {e}")
        return []


def get_manga_by_tags(included_tags: list, excluded_tags: list = [], limit: int = 8) -> list:
    """Cherche des mangas par tags sur MangaDex."""
    try:
        # Récupère tous les tags disponibles sur MangaDex
        tag_resp = requests.get(f"{BASE_URL}/manga/tag", timeout=10)
        tag_resp.raise_for_status()
        all_tags = tag_resp.json().get("data", [])

        # Crée un dictionnaire nom -> id
        tag_map = {
            t["attributes"]["name"]["en"].lower(): t["id"]
            for t in all_tags
            if "en" in t.get("attributes", {}).get("name", {})
        }

        included_ids = [tag_map[t.lower()] for t in included_tags if t.lower() in tag_map]
        excluded_ids = [tag_map[t.lower()] for t in excluded_tags if t.lower() in tag_map]

        params = {
            "limit": limit,
            "order[followedCount]": "desc",
            "availableTranslatedLanguage[]": ["en", "fr"]
        }
        for i, tid in enumerate(included_ids[:5]):
            params[f"includedTags[{i}]"] = tid
        for i, tid in enumerate(excluded_ids[:5]):
            params[f"excludedTags[{i}]"] = tid

        r = requests.get(f"{BASE_URL}/manga", params=params, timeout=10)
        r.raise_for_status()

        results = []
        for manga in r.json().get("data", []):
            attrs = manga.get("attributes", {})
            title_data = attrs.get("title", {})
            desc_data = attrs.get("description", {})
            results.append({
                "id": manga.get("id"),
                "title": title_data.get("en") or title_data.get("fr") or next(iter(title_data.values()), "Unknown"),
                "description": (desc_data.get("en") or desc_data.get("fr") or next(iter(desc_data.values()), ""))[:300],
                "tags": [
                    tag["attributes"]["name"].get("en", "")
                    for tag in attrs.get("tags", [])
                    if tag.get("attributes", {}).get("name")
                ],
                "status": attrs.get("status", ""),
                "year": attrs.get("year", ""),
                "url": f"https://mangadex.org/title/{manga.get('id')}"
            })
        return results

    except Exception as e:
        print(f"[MangaDex Error] get_manga_by_tags: {e}")
        return []