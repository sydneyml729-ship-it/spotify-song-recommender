
# app.py
import os
import streamlit as st
from core_recommender import recommend_from_favorites, build_recommendation_buckets

# ---------------------------- Page & Branding ---------------------------- #
st.set_page_config(page_title="Song Recommendation (Spotify)", page_icon="🎵")

st.markdown("### 🎵 Song Recommendations")
st.caption("Each item includes an 'Open in Spotify' button for attribution.")
st.caption("Tip: typos are okay — we’ll fuzzy‑match your Title and Artist.")

# ---------------------------- Secrets / Env ------------------------------ #
def _get_secret(name: str) -> str:
    # Prefer Streamlit secrets; fall back to environment variables
    val = st.secrets.get(name, "") or os.getenv(name, "")
    return val.strip()

CLIENT_ID = _get_secret("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = _get_secret("SPOTIFY_CLIENT_SECRET")

# ------------------------------ Sidebar --------------------------------- #
with st.sidebar:
    st.header("Settings")
    market = st.text_input("Market (country code)", value="US", help="e.g., US, GB, KR, JP")

    st.divider()
    st.header("Mode")
    # Use a radio as a robust switch across Streamlit versions
    mode = st.radio("Choose recommendation mode", ["Standard", "Niche"], index=0, horizontal=True)

    # Show Niche controls only when Niche is selected
    if mode == "Niche":
        st.divider()
        st.header("Niche controls")
        track_pop_max = st.slider(
            "Max track popularity (hidden gems)", 0, 100, 35, help="Lower = more niche"
        )
        artist_pop_max = st.slider(
            "Max artist popularity (artists/rising stars)", 0, 100, 45, help="Lower = more niche"
        )
        per_bucket = st.slider("Items per bucket", 1, 10, 5)

# ------------------------------- Inputs ---------------------------------- #
col1, col2 = st.columns(2)
with col1:
    s1_title = st.text_input("Favorite #1 — Title", placeholder="e.g., Blinding Lights")
with col2:
    s1_artist = st.text_input("Favorite #1 — Artist", placeholder="e.g., The Weeknd")

col1, col2 = st.columns(2)
with col1:
    s2_title = st.text_input("Favorite #2 — Title", placeholder="e.g., Yellow")
with col2:
    s2_artist = st.text_input("Favorite #2 — Artist", placeholder="e.g., Coldplay")

col1, col2 = st.columns(2)
with col1:
    s3_title = st.text_input("Favorite #3 — Title", placeholder="e.g., Bad Guy")
with col2:
    s3_artist = st.text_input("Favorite #3 — Artist", placeholder="e.g., Billie Eilish")

# One button: mode decides the logic
run = st.button("Recommend", type="primary")

# ------------------------------ Helpers ---------------------------------- #
def _collect_favorites_with_feedback() -> list[tuple[str, str]]:
    rows = [
        ("Favorite #1", s1_title.strip(), s1_artist.strip()),
        ("Favorite #2", s2_title.strip(), s2_artist.strip()),
        ("Favorite #3", s3_title.strip(), s3_artist.strip()),
    ]
    valid = []
    for label, t, a in rows:
        if t and a:
            valid.append((t, a))
        elif t and not a:
            st.warning(f"{label}: Title entered but Artist is missing.")
        elif a and not t:
            st.warning(f"{label}: Artist entered but Title is missing.")
    return valid

def _ensure_creds() -> bool:
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error(
            "No Spotify credentials found.\n\n"
            "Add them to **Settings → Secrets** in Streamlit Cloud using TOML:\n\n"
            "```toml\nSPOTIFY_CLIENT_ID = \"your-client-id\"\nSPOTIFY_CLIENT_SECRET = \"your-client-secret\"\n```"
        )
        return False
    return True

# ------------------------------- Handler --------------------------------- #
if run:
    if not _ensure_creds():
        st.stop()

    favorites = _collect_favorites_with_feedback()
    if not favorites:
        st.warning("Please enter at least one valid Title + Artist pair.")
        st.stop()

    if mode == "Standard":
        with st.spinner("Fetching recommendations..."):
            recs = recommend_from_favorites(CLIENT_ID, CLIENT_SECRET, market, favorites, max_recs=3)

        st.subheader("Recommendations")
        if not recs:
            st.info("No compliant recommendations found—try different titles/artists.")
        else:
            for i, (text, url) in enumerate(recs, start=1):
                st.write(f"**{i}. {text}**")
                if url:
                    st.link_button("Open in Spotify", url)

    else:  # Niche
        # Default values if someone toggled mode mid-run (defensive)
        track_pop = locals().get("track_pop_max", 35)
        artist_pop = locals().get("artist_pop_max", 45)
        per_bucket_val = locals().get("per_bucket", 5)

        with st.spinner("Fetching niche recommendations..."):
            buckets = build_recommendation_buckets(
                CLIENT_ID,
                CLIENT_SECRET,
                market,
                favorites,
                track_pop_max=track_pop,
                artist_pop_max=artist_pop,
                per_bucket=per_bucket_val,
            )

        st.subheader("Recommendations")
        for title, items in buckets.items():
            st.markdown(f"#### {title}")
            if not items:
                st.info(
                    "No items found—try raising the popularity thresholds or change favorites/market."
                )
            else:
                for text, url in items:
                    st.write(f"- **{text}**")
                    if url:
                        st.link_button("Open in Spotify", url)
            st.divider()
