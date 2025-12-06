
# app.py
import streamlit as st
from core_recommender import recommend_from_favorites

st.set_page_config(page_title="Song Recommendation (Spotify)", page_icon="🎵")

# --- Branding/Attribution (recommended) ---
st.markdown("### !Spotify Logo Song Recommendations")
st.caption("Uses Spotify metadata and links; content attributed and linked back to Spotify. Click 'Open in Spotify' for each recommendation.")

# --- Secrets: set these in Streamlit Cloud (Settings → Secrets) ---
CLIENT_ID = st.secrets.get("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = st.secrets.get("SPOTIFY_CLIENT_SECRET", "")

with st.sidebar:
    st.header("Settings")
    market = st.text_input("Market (country code)", value="US", help="e.g., US, GB, KR, JP")

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

run = st.button("Recommend", type="primary")

if run:
    if not CLIENT_ID or not CLIENT_SECRET:
        st.error("Server is missing Spotify Client ID/Secret. Configure `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in app secrets.")
    else:
        favorites = [
            (s1_title.strip(), s1_artist.strip()),
            (s2_title.strip(), s2_artist.strip()),
            (s3_title.strip(), s3_artist.strip()),
        ]
        favorites = [(t, a) for (t, a) in favorites if t and a]
        if not favorites:
            st.warning("Please enter at least one valid Title + Artist pair.")
        else:
            with st.spinner("Fetching recommendations..."):
                recs = recommend_from_favorites(CLIENT_ID, CLIENT_SECRET, market, favorites, max_recs=3)

            st.subheader("Recommendations")
            if not recs:
                st.info("No compliant recommendations found—try different titles/artists.")
            else:
                for i, (text, url) in enumerate(recs, start=1):
                    # Metadata + link back to Spotify (compliance)
                    st.write(f"**{i}. {text}**")
                    if url:
                        st.link_button("Open in Spotify", url)
