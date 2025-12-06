
# core_recommender.py
from typing import List, Tuple
from spotify_client import SpotifyClient

def recommend_from_favorites(
    client_id: str,
    client_secret: str,
    market: str,
    favorites: List[Tuple[str, str]],
    max_recs: int = 3,
) -> List[Tuple[str, str]]:
    """
    favorites: [(title, artist), ...]
    returns: [(display_text, spotify_url), ...]
    """
    sp = SpotifyClient(client_id, client_secret, market=market or "US")

    # Normalize input & guard against blanks
    favorites = [(t.strip(), a.strip()) for (t, a) in favorites if t and a]
    fav_keys = {(t.lower(), a.lower()) for (t, a) in favorites}

    # Resolve each favorite to an artist (Search -> Track -> Primary Artist)
    artist_infos = []
    for (title, artist) in favorites:
        try:
            items = sp.search_track(title, artist, limit=1)
            if items:
                _, _, aid, aname, _ = sp.extract_track_core(items[0])
                if aid:
                    adata = sp.get_artist(aid)  # allowed endpoint
                    a_genres = adata.get("genres", []) or []
                    artist_infos.append((aid, aname, a_genres))
        except Exception:
            # Continue on individual failures
            continue

    # Pull top tracks per artist; skip exact duplicates of favorites
    candidates = []
    for (aid, aname, _g) in artist_infos:
        try:
            top = sp.get_artist_top_tracks(aid, limit=10)  # allowed endpoint; requires market
            for tr in top:
                _, tname, _, pa_name, turl = sp.extract_track_core(tr)
                key = (tname.strip().lower(), pa_name.strip().lower())
                if key in fav_keys:
                    continue
                candidates.append((f"{tname} — {pa_name}", turl))
        except Exception:
            continue

    # Deduplicate & take first N
    seen, recs = set(), []
    for (text, url) in candidates:
        if text not in seen:
            seen.add(text)
            recs.append((text, url))
        if len(recs) >= max_recs:
            break
    return recs
