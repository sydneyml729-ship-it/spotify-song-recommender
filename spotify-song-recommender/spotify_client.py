
# ---------------------------------
# spotify_client.py (Compliant Client)
# ---------------------------------
import base64
import json
import time
import urllib.parse
import urllib.request
from typing import Optional, Dict, List, Tuple

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

class SpotifyClient:
    """
    Allowed endpoints for new apps:
      - GET /v1/search
      - GET /v1/artists/{id}
      - GET /v1/artists/{id}/top-tracks
    Auth: OAuth 2.0 Client Credentials (no user scopes).
    """

    def __init__(self, client_id: str, client_secret: str, market: str = "US"):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.market = market
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    # --- Auth: Client Credentials (1-hour token) ---
    def _fetch_access_token(self) -> None:
        # Basic auth: base64(client_id:client_secret)
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("utf-8")
        data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")
        req = urllib.request.Request(
            SPOTIFY_TOKEN_URL,
            data=data,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        self._access_token = payload["access_token"]
        # refresh slightly early
        self._expires_at = time.time() + float(payload.get("expires_in", 3600)) * 0.95

    def _ensure_token(self) -> str:
        if not self._access_token or time.time() >= self._expires_at:
            self._fetch_access_token()
        return self._access_token

    def _api_get(self, path: str, params: Dict[str, str] = None) -> Dict:
        token = self._ensure_token()
        url = f"{SPOTIFY_API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")

        # Basic rate-limit/backoff handling
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", "2"))
                time.sleep(retry_after)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            elif e.code in (401, 403):
                raise
            else:
                raise

    # --- Search for track by title + artist ---
    def search_track(self, title: str, artist: str, limit: int = 3) -> List[Dict]:
        # Use field filters for precision: track:"..." artist:"..."
        q = f'track:"{title.strip()}" artist:"{artist.strip()}"'
        params = {"q": q, "type": "track", "limit": str(limit), "market": self.market}
        data = self._api_get("/search", params)
        return data.get("tracks", {}).get("items", [])

    # --- Get artist info (genres, etc.) ---
    def get_artist(self, artist_id: str) -> Dict:
        return self._api_get(f"/artists/{artist_id}", {})

    # --- Get an artist's top tracks (market) ---
    def get_artist_top_tracks(self, artist_id: str, limit: int = 10) -> List[Dict]:
        data = self._api_get(f"/artists/{artist_id}/top-tracks", {"market": self.market})
        items = data.get("tracks", []) or []
        return items[:limit]

    # Helper: extract core fields from a track
    @staticmethod
    def extract_track_core(track: Dict) -> Tuple[str, str, str, str, str]:
        tid = track.get("id") or ""
        tname = track.get("name") or ""
        artists = track.get("artists") or []
        a_id = artists[0].get("id") if artists else ""
        a_name = artists[0].get("name") if artists else ""
        turl = (track.get("external_urls") or {}).get("spotify") or (f"https://open.spotify.com/track/{tid}" if tid else "")
        return tid, tname, a_id, a_name, turl
