
# song_recommender_spotify_addon.py
bl_info = {
    "name": "Song Recommendation Generator (Spotify, compliant)",
    "author": "You + M365 Copilot",
    "version": (1, 3, 1),
    "blender": (2, 93, 0),
    "location": "3D Viewport > N-panel > Music",
    "description": "Enter 3 favorite songs and get Spotify-based recommendations using allowed endpoints only.",
    "category": "3D View",
}

import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import StringProperty, EnumProperty, PointerProperty
import os, sys, webbrowser

# --- Safe import of local client ---
addon_dir = os.path.dirname(os.path.abspath(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)
try:
    from spotify_client import SpotifyClient
except Exception as e:
    SpotifyClient = None
    print("Failed to import spotify_client.py:", e)

# --- Static lists (no callbacks) ---
ALL_GENRES = [
    "pop","rock","hip-hop","r&b","electronic","country","jazz",
    "classical","indie","metal","reggae","k-pop","latin",
]
ALL_KINDS = [
    "upbeat","chill","dance","acoustic","anthem",
    "energetic","melancholy","romantic","workout","focus",
]

GENRE_ITEMS = [(g, g, f"Genre: {g}") for g in ALL_GENRES]
KIND_ITEMS  = [(k, k, f"Kind/mood: {k}") for k in ALL_KINDS]

class MusicPrefs(PropertyGroup):
    # Credentials
    client_id:     StringProperty(name="Client ID", default="")
    client_secret: StringProperty(name="Client Secret", default="", subtype='PASSWORD')
    market:        StringProperty(name="Market (country code)", default="US")

    # Favorites (static Enum items + valid defaults)
    s1_title:  StringProperty(name="Title",  default="")
    s1_artist: StringProperty(name="Artist", default="")
    s1_genre:  EnumProperty(name="Genre", items=GENRE_ITEMS, default="pop")
    s1_kind:   EnumProperty(name="Kind",  items=KIND_ITEMS,  default="upbeat")

    s2_title:  StringProperty(name="Title",  default="")
    s2_artist: StringProperty(name="Artist", default="")
    s2_genre:  EnumProperty(name="Genre", items=GENRE_ITEMS, default="rock")
    s2_kind:   EnumProperty(name="Kind",  items=KIND_ITEMS,  default="energetic")

    s3_title:  StringProperty(name="Title",  default="")
    s3_artist: StringProperty(name="Artist", default="")
    s3_genre:  EnumProperty(name="Genre", items=GENRE_ITEMS, default="hip-hop")
    s3_kind:   EnumProperty(name="Kind",  items=KIND_ITEMS,  default="chill")

    # Output
    result_1: StringProperty(name="1", default="")
    result_2: StringProperty(name="2", default="")
    result_3: StringProperty(name="3", default="")
    url_1:    StringProperty(name="URL 1", default="")
    url_2:    StringProperty(name="URL 2", default="")
    url_3:    StringProperty(name="URL 3", default="")

class MUSIC_OT_recommend_spotify(Operator):
    bl_idname = "music.recommend_spotify"
    bl_label = "Recommend (Spotify)"
    bl_description = "Compliant recommendations via Search + Artist Top Tracks"

    def execute(self, context):
        # Guard against restricted contexts (no scene)
        scene = getattr(context, "scene", None)
        if scene is None or not hasattr(scene, "music_prefs"):
            self.report({'ERROR'}, "Scene not available. Open a 3D Viewport and try again.")
            return {'CANCELLED'}

        prefs: MusicPrefs = scene.music_prefs

        # Import guard
        if SpotifyClient is None:
            self.report({'ERROR'}, "spotify_client.py not found/importable.")
            return {'CANCELLED'}

        # Credentials guard
        if not prefs.client_id or not prefs.client_secret:
            self.report({'ERROR'}, "Enter Spotify Client ID and Secret.")
            return {'CANCELLED'}

        # Create client
        sp = SpotifyClient(prefs.client_id, prefs.client_secret, market=prefs.market or "US")

        # Collect favorites
        favorites = [
            (prefs.s1_title.strip(), prefs.s1_artist.strip()),
            (prefs.s2_title.strip(), prefs.s2_artist.strip()),
            (prefs.s3_title.strip(), prefs.s3_artist.strip()),
        ]
        favorites = [(t, a) for (t, a) in favorites if t and a]
        fav_keys = {(t.lower(), a.lower()) for (t, a) in favorites}

        # Resolve artists
        artist_infos = []
        for (title, artist) in favorites:
            try:
                items = sp.search_track(title, artist, limit=1)
                if items:
                    tid, tname, aid, aname, _ = sp.extract_track_core(items[0])
                    if aid:
                        adata = sp.get_artist(aid)  # allowed endpoint
                        a_genres = adata.get("genres", []) or []
                        artist_infos.append((aid, aname, a_genres))
            except Exception as e:
                self.report({'WARNING'}, f"Search failed for {title} — {artist}: {e}")

        # Build candidates from top tracks
        candidates = []
        for (aid, aname, a_genres) in artist_infos:
            try:
                top = sp.get_artist_top_tracks(aid, limit=10)
                for tr in top:
                    tid, tname, pa_id, pa_name, turl = sp.extract_track_core(tr)
                    key = (tname.strip().lower(), pa_name.strip().lower())
                    if key in fav_keys:
                        continue
                    candidates.append((f"{tname} — {pa_name}", turl))
            except Exception as e:
                self.report({'WARNING'}, f"Top tracks failed for artist {aname}: {e}")

        # Dedup & pick 3
        seen = set(); recs = []
        for (text, url) in candidates:
            if text not in seen:
                seen.add(text)
                recs.append((text, url))
            if len(recs) >= 3:
                break

        # Update UI
        prefs.result_1 = recs[0][0] if len(recs) > 0 else "—"
        prefs.url_1    = recs[0][1] if len(recs) > 0 else ""
        prefs.result_2 = recs[1][0] if len(recs) > 1 else "—"
        prefs.url_2    = recs[1][1] if len(recs) > 1 else ""
        prefs.result_3 = recs[2][0] if len(recs) > 2 else "—"
        prefs.url_3    = recs[2][1] if len(recs) > 2 else ""

        if len(recs) == 0:
            self.report({'WARNING'}, "No compliant recommendations found—try different titles/artists.")
        else:
            self.report({'INFO'}, "Recommendations updated via Spotify (compliant).")
        return {'FINISHED'}

class MUSIC_OT_open_url(Operator):
    bl_idname = "music.open_url"
    bl_label = "Open in Browser"
    url: StringProperty(default="")
    def execute(self, context):
        if self.url:
            webbrowser.open(self.url)
            return {'FINISHED'}
        return {'CANCELLED'}

class MUSIC_PT_recommender_spotify(Panel):
    bl_idname = "MUSIC_PT_recommender_spotify"
    bl_label = "Song Recommendation (Spotify, compliant)"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Music"

    def draw(self, context):
        # Guard against restricted contexts
        scene = getattr(context, "scene", None)
        if scene is None or not hasattr(scene, "music_prefs"):
            self.layout.label(text="Scene not available. Open a 3D Viewport and re-enable the add-on.")
            return

        layout = self.layout
        prefs: MusicPrefs = scene.music_prefs

        # Credentials
        box = layout.box()
        box.label(text="Spotify Credentials")
        box.prop(prefs, "client_id")
        box.prop(prefs, "client_secret")
        box.prop(prefs, "market")

        # Favorites
        layout.label(text="Favorite Song #1")
        b1 = layout.box(); col = b1.column(align=True)
        col.prop(prefs, "s1_title"); col.prop(prefs, "s1_artist"); col.prop(prefs, "s1_genre"); col.prop(prefs, "s1_kind")

        layout.label(text="Favorite Song #2")
        b2 = layout.box(); col = b2.column(align=True)
        col.prop(prefs, "s2_title"); col.prop(prefs, "s2_artist"); col.prop(prefs, "s2_genre"); col.prop(prefs, "s2_kind")

        layout.label(text="Favorite Song #3")
        b3 = layout.box(); col = b3.column(align=True)
        col.prop(prefs, "s3_title"); col.prop(prefs, "s3_artist"); col.prop(prefs, "s3_genre"); col.prop(prefs, "s3_kind")

        layout.separator()
        layout.operator(MUSIC_OT_recommend_spotify.bl_idname, icon='SOUND')

        # Output
        layout.separator()
        layout.label(text="Recommendations")
        for res_prop, url_prop in [("result_1","url_1"), ("result_2","url_2"), ("result_3","url_3")]:
            row = layout.row()
            row.label(text=getattr(prefs, res_prop) or "—")
            url = getattr(prefs, url_prop)
            if url:
                op = row.operator(MUSIC_OT_open_url.bl_idname, text="Open")
                op.url = url

# --- Registration ---
classes = (MusicPrefs, MUSIC_OT_recommend_spotify, MUSIC_OT_open_url, MUSIC_PT_recommender_spotify)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Attach property to Scene (safe, no context access)
    bpy.types.Scene.music_prefs = PointerProperty(type=MusicPrefs)

def unregister():
    if hasattr(bpy.types.Scene, "music_prefs"):
        del bpy.types.Scene.music_prefs
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
