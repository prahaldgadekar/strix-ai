"""
fetch_playlist_uris.py — Run this ONCE to get all track URIs from your playlist
Place in E:\Strix\ and run: python fetch_playlist_uris.py

Requires: pip install spotipy python-dotenv
Requires: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env
"""

import os, json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
PLAYLIST_ID   = "6dhvXHh0skhIQm2tL0uJYP"   # your "tired" playlist

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET not set in .env")
    print("   Get them at: https://developer.spotify.com/dashboard")
    input("Press Enter to exit...")
    exit(1)

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    print("❌ spotipy not installed. Run: pip install spotipy")
    input("Press Enter to exit...")
    exit(1)

print("Connecting to Spotify API...")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
))

print(f"Fetching playlist: {PLAYLIST_ID}")
results = {}
offset  = 0

while True:
    response = sp.playlist_tracks(PLAYLIST_ID, offset=offset, limit=100)
    items    = response.get("items", [])
    if not items:
        break
    for item in items:
        track = item.get("track")
        if not track:
            continue
        name   = track["name"].lower()
        artist = track["artists"][0]["name"] if track["artists"] else ""
        uri    = track["uri"]   # e.g. spotify:track:XXXXXXXX
        results[name] = {"uri": uri, "artist": artist}
        print(f"  ✓ {track['name']} — {artist}")
    offset += len(items)
    if not response.get("next"):
        break

# Save as JSON
out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playlist_uris.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n✅ Saved {len(results)} tracks to: {out_file}")
print("   STRIX will now auto-play all songs directly!")
input("\nPress Enter to exit...")
