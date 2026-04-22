"""
X.com Profile Photo Blocker
----------------------------
Automatically blocks accounts whose profile photo matches
one of your reference images.

Usage:
  1. Put reference images in the  reference_images/  folder
  2. Run:  python main.py
  3. Log in when the browser opens (skipped on subsequent runs)
"""

import asyncio
import json
import os

from playwright.async_api import async_playwright

import config
from auth import login, get_my_username
from scraper import get_followers, get_following
from blocker import block_user
from image_matcher import ImageMatcher


# ── helpers ──────────────────────────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def print_banner():
    print("=" * 55)
    print("  X.com Profile Photo Blocker")
    print("=" * 55)


# ── main ─────────────────────────────────────────────────────────────────────

async def run():
    print_banner()

    # Load reference images
    print("\n[1/5] Loading reference images...")
    matcher = ImageMatcher()
    if not matcher.reference_hashes:
        print("\n  ERROR: No reference images found.")
        print(f"  Put .jpg/.png images in the '{config.REFERENCE_IMAGES_DIR}/' folder and re-run.\n")
        return

    # Load persistent state
    blocked_users = load_json(config.BLOCKED_USERS_FILE)   # {username: ref_filename}
    scanned_users = load_json(config.SCANNED_USERS_FILE)   # {username: True}

    async with async_playwright() as pw:

        # Auth
        print("\n[2/5] Authenticating...")
        browser, context, page = await login(pw)

        my_username = await get_my_username(page)
        if not my_username:
            print("  ERROR: Could not detect your username. Please re-run and log in again.")
            await browser.close()
            return
        print(f"  Logged in as: @{my_username}")

        # ── Collect users to scan ─────────────────────────────────────────────

        print("\n[3/5] Collecting accounts to scan...")
        users_to_scan = {}   # {username: {username, profile_image_url}}

        # Your followers
        print(f"  Fetching your followers (up to {config.MAX_FOLLOWERS_SCAN})...")
        followers = await get_followers(page, my_username, config.MAX_FOLLOWERS_SCAN)
        for u in followers:
            users_to_scan[u['username']] = u
        print(f"  → {len(followers)} followers found")

        # Accounts you follow
        print(f"  Fetching accounts you follow (up to {config.MAX_FOLLOWING_SCAN})...")
        following = await get_following(page, my_username, config.MAX_FOLLOWING_SCAN)
        for u in following:
            users_to_scan[u['username']] = u
        print(f"  → {len(following)} following found")

        # Second level: followers/following of the accounts above
        print(f"\n  Expanding {config.MAX_SECOND_LEVEL_USERS} accounts one level deeper...")
        first_level = [u for u in list(users_to_scan.values())[:config.MAX_SECOND_LEVEL_USERS]
                       if u['username'] not in scanned_users]

        for i, user in enumerate(first_level, 1):
            uname = user['username']
            print(f"  [{i}/{len(first_level)}] Fetching followers of @{uname}...")
            try:
                sub = await get_followers(page, uname, config.MAX_SECOND_LEVEL_PER_USER)
                added = 0
                for u in sub:
                    if u['username'] not in users_to_scan:
                        users_to_scan[u['username']] = u
                        added += 1
                print(f"    → {added} new accounts added")
            except Exception as e:
                print(f"    → Skipped ({e})")

        # Remove self
        users_to_scan.pop(my_username, None)

        print(f"\n  Total unique accounts to scan: {len(users_to_scan)}")

        # ── Scan & match ──────────────────────────────────────────────────────

        print("\n[4/5] Scanning profile photos...\n")
        block_count = 0
        scan_count = 0

        for username, user_data in users_to_scan.items():
            if username in scanned_users:
                continue
            if username in blocked_users:
                continue

            img_url = user_data.get('profile_image_url', '')
            if not img_url:
                scanned_users[username] = True
                continue

            scan_count += 1
            is_match, matched_ref = matcher.is_match(img_url)
            scanned_users[username] = True

            if is_match:
                print(f"  [MATCH] @{username}  →  matches '{matched_ref}'")
                success = await block_user(page, username)
                if success:
                    blocked_users[username] = matched_ref
                    block_count += 1
                    print(f"          Blocked successfully.")
                else:
                    print(f"          Block failed (see above).")
            else:
                print(f"  [ ok  ] @{username}")

        # ── Save state ────────────────────────────────────────────────────────

        print("\n[5/5] Saving results...")
        save_json(config.BLOCKED_USERS_FILE, blocked_users)
        save_json(config.SCANNED_USERS_FILE, scanned_users)

        print(f"\n  Scanned : {scan_count} accounts")
        print(f"  Blocked : {block_count} accounts")
        print(f"\n  Full block log: {config.BLOCKED_USERS_FILE}")
        print("=" * 55)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(run())
