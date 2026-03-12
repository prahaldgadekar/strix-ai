"""
spotify_controller.py — STRIX v4.1
====================================
FIX: When song is NOT in playlist, now uses Spotipy API search
     to find the exact track URI and plays it directly.
     No more coordinate-clicking the artist page.

Priority order for playing a song:
  1. playlist_uris.json  (auto-fetched real URIs — most reliable)
  2. MY_PLAYLIST_SONGS   (hardcoded URIs — instant play)
  3. Spotipy API search  (find any track by name → direct URI play) ← NEW
  4. Search + auto-click (last resort if no API credentials)
"""

import os, subprocess, time, json, ctypes, threading
_os = os

try:
    from dotenv import load_dotenv as _ldenv
    _ldenv(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

CLIENT_ID     = _os.environ.get("SPOTIFY_CLIENT_ID",     "")
CLIENT_SECRET = _os.environ.get("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI  = _os.environ.get("SPOTIFY_REDIRECT_URI",  "http://127.0.0.1:8888/callback")
CACHE_PATH    = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".spotify_cache")

# ── Your playlist ID ─────────────────────────────────────────
PLAYLIST_URI = "spotify:playlist:6dhvXHh0skhIQm2tL0uJYP"
PLAYLIST_ID  = "6dhvXHh0skhIQm2tL0uJYP"

# ── Shared Spotipy client (reused to avoid re-auth every time) ─
_sp = None

def _get_spotipy():
    """Get or create a Spotipy client. Returns None if no credentials."""
    global _sp
    if not (CLIENT_ID and CLIENT_SECRET):
        return None
    if _sp is not None:
        return _sp
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope="user-modify-playback-state user-read-playback-state streaming",
            cache_path=CACHE_PATH,
            open_browser=False,
        ))
        return _sp
    except Exception as e:
        print(f"[Spotify] Spotipy init failed: {e}")
        return None


# ── Playback Controls ─────────────────────────────────────────

def pause_music() -> str:
    """Pause/Resume Spotify."""
    sp = _get_spotipy()
    if sp:
        try:
            state = sp.current_playback()
            if state and state.get("is_playing"):
                sp.pause_playback()
                return "Music paused, Boss."
            elif state and not state.get("is_playing"):
                sp.start_playback()
                return "Music resumed, Boss."
        except Exception:
            pass
    # Fallback — send Space key to Spotify window
    try:
        subprocess.Popen([
            "powershell", "-Command",
            "$wsh = New-Object -ComObject WScript.Shell; "
            "$wsh.AppActivate('Spotify'); "
            "Start-Sleep -Milliseconds 200; "
            "$wsh.SendKeys(' ')"
        ], shell=False)
        return "Music paused/resumed, Boss."
    except Exception as e:
        return f"Couldn't pause: {e}"


def stop_music() -> str:
    """Stop Spotify completely."""
    sp = _get_spotipy()
    if sp:
        try:
            sp.pause_playback()
        except Exception:
            pass
    try:
        subprocess.Popen(["taskkill", "/F", "/IM", "Spotify.exe"], shell=False)
        return "Spotify stopped, Boss."
    except Exception as e:
        return f"Couldn't stop Spotify: {e}"


def next_track() -> str:
    """Skip to next track."""
    sp = _get_spotipy()
    if sp:
        try:
            sp.next_track()
            return "Next track, Boss."
        except Exception:
            pass
    try:
        subprocess.Popen([
            "powershell", "-Command",
            "$wsh = New-Object -ComObject WScript.Shell; "
            "$wsh.AppActivate('Spotify'); "
            "Start-Sleep -Milliseconds 200; "
            "$wsh.SendKeys('^{RIGHT}')"
        ], shell=False)
        return "Skipped to next track, Boss."
    except Exception as e:
        return f"Couldn't skip: {e}"


def prev_track() -> str:
    """Go to previous track."""
    sp = _get_spotipy()
    if sp:
        try:
            sp.previous_track()
            return "Previous track, Boss."
        except Exception:
            pass
    try:
        subprocess.Popen([
            "powershell", "-Command",
            "$wsh = New-Object -ComObject WScript.Shell; "
            "$wsh.AppActivate('Spotify'); "
            "Start-Sleep -Milliseconds 200; "
            "$wsh.SendKeys('^{LEFT}')"
        ], shell=False)
        return "Previous track, Boss."
    except Exception as e:
        return f"Couldn't go back: {e}"


# ── Full Playlist Song URIs ───────────────────────────────────
MY_PLAYLIST_SONGS = {
    # ── Bollywood Classics ────────────────────────────────────
    "pal pal dil ke paas":              "spotify:track:71j40GUuIgwpEGmoupat2O",
    "mera mann kehne laga":             "spotify:track:1niVgR76UPobOED5cXfADq",
    "tu jaane na":                      "spotify:track:5vGiuYFSGekGLgbxhV1rD5",
    "monta re":                         "spotify:track:5UHvVfewZKxwoB6gdhSFtr",
    "paro":                             "spotify:track:6nRGPf5tpeJtKpXZO5cgIT",
    "kase sartil saye":                 "spotify:track:1r5vcVkV5zZeCC77KmwF7S",
    "kehna galat galat":                "spotify:track:78CHk5OPRMsm30e5q9Jm8h",
    "halka halka suroor":               "spotify:track:78CHk5OPRMsm30e5q9Jm8h",
    "ik kudi":                          "spotify:track:7mTaeqTfEbbFpeG2JqQlkf",
    "dil to bachcha hai":               "spotify:track:3EFGRGsshk0NWidcXfhKvw",
    "dil to bachha hai":                "spotify:track:3EFGRGsshk0NWidcXfhKvw",
    "ransom":                           "spotify:track:1lOe9qE0vR9zwWQAOk6CoO",
    "toxic":                            "spotify:track:3M214U0mwSm041GsQR3nrO",
    "understand":                       "spotify:track:6dGqGkYDoRrKh5UiIcTT22",
    "alag aasmaan":                     "spotify:track:3bQsp4Vr9Rg4fNCx6HPOgX",
    "kisi ki muskurahaton pe":          "spotify:track:7rkkhMxGDlfpHtV9Y9bKsC",
    "haule haule":                      "spotify:track:2UKK9UEbKlykbmLVP1zWIQ",
    "kabhi kabhi aditi":                "spotify:track:3APdIdF8H0jsxSuGOqXedS",
    "bulleya":                          "spotify:track:3tgdOveYac7YMEAQD9sGLf",
    "a man without love":               "spotify:track:0oUBuOO4g9P4lREqfqR5nq",
    "man without love":                 "spotify:track:0oUBuOO4g9P4lREqfqR5nq",
    "just the two of us":               "spotify:track:1ko2lVN0vKGUl9zrU0qSlT",
    "mere mehboob qayamat hogi":        "spotify:track:6a9JaoHp5F9lVA7dCjfIHk",
    "javeda zindagi":                   "spotify:track:04FnSzoogJD1iQbghug23K",
    "javeda zindagi tose naina lage":   "spotify:track:04FnSzoogJD1iQbghug23K",
    "kal chaudhvin ki raat thi":        "spotify:track:72lVn67bCaZLJmw5XsPOBn",
    "dil kya kare":                     "spotify:track:0rIy3nxtNP0oqOfYRr6kGg",
    "abhi na jao chhod kar":            "spotify:track:0C47mkZ7VGcnKBvEG7PiAP",
    "co2":                              "spotify:track:6XirXsNe0OVII0tncUOGGZ",
    "isq risk":                         "spotify:track:0rxEPf4Y6uBmV3hkrV340a",
    "meri kahani":                      "spotify:track:0ShD5dxdAfDHx01sm20ybX",
    "choo lo":                          "spotify:track:0rlLBWFFTQiOWi963SH9bb",
    "let her go":                       "spotify:track:2pUpNOgJBIBCcjyQZQ00qU",
    "beqarar karke hamen yun na jaiye": "spotify:track:7ukboFFuDuxKWRdxahmth7",
    "beqarar karke":                    "spotify:track:7ukboFFuDuxKWRdxahmth7",
    # ── English / International ───────────────────────────────
    "line without a hook":              "spotify:track:12HXHMDQTen0cwNTKFAb7e",
    "until i found you":                "spotify:track:4GNcxBEPHfbFAVRuOjGCWX",
    "end of beginning":                 "spotify:track:3yfqSUWxFvZELEM4PmlwIR",
    "i wanna be yours":                 "spotify:track:4e2KGSB0z5JMdslaqKRtRN",
    "i love you so":                    "spotify:track:6nGeLlakfzlBCKFgbFlxZu",
    "sailor song":                      "spotify:track:6TDpm99sNDKu3AVAYEsGqN",
    "back to friends":                  "spotify:track:7sFHHkj0kNdkAr5DKOJNRs",
    "no one noticed":                   "spotify:track:6LEJrKxPrqhFWflnJkSJQg",
    "i think they call this love":      "spotify:track:3QHuSiJEoO1DFb4QLJoxeZ",
    "all i need":                       "spotify:track:2BkbsYEFHGnNiJuHbTWVOm",
    "favorite peeps":                   "spotify:track:0Q7jNVWtQMqSR4OwPq5MEL",
    "hollow":                           "spotify:track:5yKqpAA5DmVqCoCzX3JNFM",
}


# ── Load JSON URIs if they exist ──────────────────────────────
_JSON_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "playlist_uris.json")

def _load_json_uris() -> dict:
    if _os.path.exists(_JSON_PATH):
        try:
            with open(_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: v["uri"] for k, v in data.items() if "uri" in v}
        except Exception:
            pass
    return {}


# ── Spotify window helpers ────────────────────────────────────

def _find_spotify_hwnd():
    found = []
    def _cb(hwnd, _):
        try:
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if "Spotify" in title and title != "Spotify Premium":
                    found.append(hwnd)
        except Exception:
            pass
    try:
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(_cb), 0)
    except Exception:
        pass
    return found[0] if found else None


def _bring_spotify_front():
    hwnd = _find_spotify_hwnd()
    if hwnd:
        try:
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            return True
        except Exception:
            pass
    return False


def _launch_spotify():
    """Launch Spotify if not running."""
    paths = [
        _os.path.join(_os.environ.get("APPDATA", ""),  "Spotify\\Spotify.exe"),
        _os.path.join(_os.environ.get("LOCALAPPDATA", ""), "Microsoft\\WindowsApps\\Spotify.exe"),
    ]
    for p in paths:
        if _os.path.exists(p):
            subprocess.Popen([p])
            time.sleep(4)
            return True
    subprocess.Popen(["cmd", "/c", "start", "", "spotify:"])
    time.sleep(4)
    return True


def _ensure_spotify_open():
    hwnd = _find_spotify_hwnd()
    if not hwnd:
        _launch_spotify()
    _bring_spotify_front()
    time.sleep(0.5)


# ── NEW: Spotipy API search — finds any track by name, plays via URI ──────
def _spotipy_search_play(query: str) -> str:
    """
    Use Spotipy search to find a track by name and play it directly via URI.
    This is the correct fix — no coordinate clicking, no artist page opening.
    Returns a result string or None if it fails.
    """
    sp = _get_spotipy()
    if not sp:
        return None

    try:
        # Make sure Spotify is open first
        _ensure_spotify_open()
        time.sleep(1)

        # Check if there's an active device
        devices = sp.devices()
        active = [d for d in devices.get("devices", []) if d.get("is_active")]
        if not active and devices.get("devices"):
            # Pick the first available device
            device_id = devices["devices"][0]["id"]
            sp.transfer_playback(device_id, force_play=False)
            time.sleep(1)

        # Search Spotify for the track
        results = sp.search(q=query, type="track", limit=10)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            print(f"[Spotify] No API results for: {query}")
            return None

        # Pick best match — prefer exact/partial name match
        best_track = None
        ql = query.lower()
        for t in tracks:
            tname = t["name"].lower()
            if ql in tname or tname in ql or ql == tname:
                best_track = t
                break
        if not best_track:
            best_track = tracks[0]  # Take first result if no name match

        track_uri  = best_track["uri"]
        track_name = best_track["name"]
        artist     = best_track["artists"][0]["name"]

        print(f"[Spotify] API found: {track_name} by {artist} → {track_uri}")

        # Play via URI (starts song immediately, no clicking needed)
        sp.start_playback(uris=[track_uri])
        return f"Playing {track_name} by {artist}, Boss. 🎵"

    except Exception as e:
        print(f"[Spotify] API search/play failed: {e}")
        return None


# ── Legacy: Search + auto-click (last resort) ─────────────────
def _click_first_result(delay=3.5):
    """Fallback: click first search result in Spotify UI."""
    def _do():
        time.sleep(delay)
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            _bring_spotify_front()
            time.sleep(0.5)
            hwnd = _find_spotify_hwnd()
            if hwnd:
                import ctypes.wintypes
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                win_x = rect.left
                win_y = rect.top
                win_w = rect.right - rect.left
                win_h = rect.bottom - rect.top
                if win_x < 0: win_x = 0
                if win_w < 400:
                    print("[Spotify] Window too small, skipping click")
                    return
                # Click first song in Songs section
                click_x = win_x + int(win_w * 0.53)
                click_y = win_y + int(win_h * 0.28)
                print(f"[Spotify] Clicking first song at ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.3)
                time.sleep(0.15)
                pyautogui.doubleClick(click_x, click_y)
            else:
                try:
                    import keyboard
                    keyboard.press_and_release("enter")
                except Exception:
                    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
        except Exception as e:
            print(f"[Spotify] Click failed: {e}")
    threading.Thread(target=_do, daemon=True).start()


def _search_and_click(query: str) -> str:
    """Open Spotify search and auto-click — last resort fallback."""
    _ensure_spotify_open()
    search_uri = f"spotify:search:{query.replace(' ', '%20')}"
    subprocess.Popen(["cmd", "/c", "start", "", search_uri], shell=False)
    print(f"[Spotify] Fallback search: {query}")
    _click_first_result(delay=3.5)
    return f"Searching for {query} and playing first result, Boss. 🎵"


# ── Score-based matching ──────────────────────────────────────
def _best_match(query: str, song_dict: dict):
    ql = query.lower().strip()
    best_name, best_uri, best_score = None, None, 0
    for name, uri in song_dict.items():
        score = 0
        if ql == name:                     score = 100
        elif ql in name or name in ql:     score = 80
        else:
            q_words = set(ql.split())
            n_words = set(name.split())
            overlap = q_words & n_words
            if overlap:
                score = 20 * len(overlap)
        if score > best_score:
            best_score = score
            best_name  = name
            best_uri   = uri
    return best_name, best_uri, best_score


# ── Direct URI play ───────────────────────────────────────────
def _play_uri(uri: str, name: str) -> str:
    """Play a track/playlist directly via Spotify URI."""
    try:
        subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)
        print(f"[Spotify] Playing URI: {uri}")
        return f"Playing {name}, Boss. 🎵"
    except Exception as e:
        return f"Couldn't launch Spotify URI: {e}"


# ── Main public function ──────────────────────────────────────
def play_song(query: str) -> str:
    """
    Play a song. NEW priority order:
    1. playlist_uris.json  — all your playlist songs (exact URIs)
    2. MY_PLAYLIST_SONGS   — hardcoded known URIs
    3. Spotipy API search  — searches ALL of Spotify, plays exact track URI  ← FIX
    4. Search + auto-click — last resort if no API credentials
    """
    ql = query.lower().strip()

    # Remove trigger words
    for prefix in ("play ", "put on ", "start playing ", "start ", "play the "):
        if ql.startswith(prefix):
            ql = ql[len(prefix):].strip()

    print(f"[Spotify] play_song: '{ql}'")

    # ── 1. Check JSON URIs first ──────────────────────────────
    json_uris = _load_json_uris()
    if json_uris:
        name, uri, score = _best_match(ql, json_uris)
        if score >= 20 and uri:
            print(f"[Spotify] Found in JSON playlist: {name} (score={score})")
            return _play_uri(uri, name)

    # ── 2. Check hardcoded playlist ───────────────────────────
    name, uri, score = _best_match(ql, MY_PLAYLIST_SONGS)
    if score >= 20 and uri:
        print(f"[Spotify] Found in hardcoded list: {name} (score={score})")
        return _play_uri(uri, name)

    # ── 3. Spotipy API search → direct URI play ───────────────
    print(f"[Spotify] Not in playlist, trying API search: '{ql}'")
    result = _spotipy_search_play(ql)
    if result:
        return result

    # ── 4. Last resort — search + auto-click ─────────────────
    print(f"[Spotify] API unavailable, using search+click fallback")
    return _search_and_click(ql)


def play_playlist(name: str = "tired") -> str:
    """Play your full playlist directly."""
    return _play_uri(PLAYLIST_URI, f"your {name} playlist")


if __name__ == "__main__":
    song = input("Test song name: ").strip()
    print(play_song(song))