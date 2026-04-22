import os
import sys

# Image similarity threshold (perceptual hash distance)
# 0 = identical images only, 5 = very similar, 10 = broadly similar
HASH_THRESHOLD = 8

# Delays in milliseconds to avoid bot detection
SCROLL_DELAY = 1500
ACTION_DELAY = 2000
PAGE_LOAD_DELAY = 3000

# How many users to scan per category
MAX_FOLLOWERS_SCAN = 300
MAX_FOLLOWING_SCAN = 300

# Second-level scanning
MAX_SECOND_LEVEL_USERS = 15
MAX_SECOND_LEVEL_PER_USER = 50

# ── Paths ─────────────────────────────────────────────────────────────────────
# Store user data in AppData (Windows) or ~/.config (Linux/Mac)
# so data survives app updates and reinstalls.

def _user_data_root():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/.config")
    path = os.path.join(base, "XPhotoBlocker")
    os.makedirs(path, exist_ok=True)
    return path

_ROOT = _user_data_root()

REFERENCE_IMAGES_DIR = os.path.join(_ROOT, "reference_images")
DATA_DIR             = os.path.join(_ROOT, "data")
BLOCKED_USERS_FILE   = os.path.join(DATA_DIR, "blocked_users.json")
SCANNED_USERS_FILE   = os.path.join(DATA_DIR, "scanned_users.json")
SESSION_FILE         = os.path.join(DATA_DIR, "session.json")
