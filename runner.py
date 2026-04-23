"""
Async scanning logic — runs in a background thread.
Communicates with the GUI via log_queue.
"""

import asyncio
import json
import os
import queue as q_module

import config
from auth import login, get_my_username
from scraper import get_followers, get_following
from blocker import block_user
from image_matcher import ImageMatcher


def _load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


async def run_scan(log_queue: q_module.Queue, stop_event):
    def log(msg):
        log_queue.put({'type': 'log', 'message': msg})

    def status(msg):
        log_queue.put({'type': 'status', 'message': msg})

    def stats(scanned, blocked):
        log_queue.put({'type': 'stats', 'scanned': scanned, 'blocked': blocked})

    def done(msg):
        log_queue.put({'type': 'done', 'message': msg})

    def error(msg):
        log_queue.put({'type': 'error', 'message': msg})

    # Load reference images
    log("Loading reference images...")
    matcher = ImageMatcher(log=log)
    if not matcher.reference_hashes:
        error("No reference images found. Add images in the app first.")
        return
    log(f"Loaded {len(matcher.reference_hashes)} reference image(s).\n")

    blocked_users = _load_json(config.BLOCKED_USERS_FILE)
    scanned_users = _load_json(config.SCANNED_USERS_FILE)

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:

        # ── Auth ──────────────────────────────────────────────────────────────
        log("Opening browser for login...")
        status("Authenticating")
        browser, context, page, my_username = await login(pw, log=log)

        if not my_username:
            my_username = await get_my_username(page)
        if not my_username:
            error("Could not detect your username.\nPlease log in again.")
            await browser.close()
            return
        log(f"Logged in as: @{my_username}\n")

        if stop_event.is_set():
            await browser.close()
            done("Stopped.")
            return

        # ── Collect users ─────────────────────────────────────────────────────
        users_to_scan = {}

        status("Collecting followers")
        log(f"Fetching your followers (up to {config.MAX_FOLLOWERS_SCAN})...")
        followers = await get_followers(page, my_username, config.MAX_FOLLOWERS_SCAN)
        for u in followers:
            users_to_scan[u['username']] = u
        log(f"→ {len(followers)} followers collected")

        if stop_event.is_set():
            await browser.close()
            done("Stopped.")
            return

        status("Collecting following")
        log(f"\nFetching accounts you follow (up to {config.MAX_FOLLOWING_SCAN})...")
        following = await get_following(page, my_username, config.MAX_FOLLOWING_SCAN)
        for u in following:
            users_to_scan[u['username']] = u
        log(f"→ {len(following)} following collected")

        # ── Second-level expansion ────────────────────────────────────────────
        # Fetch both followers AND following of each first-level account
        status("Expanding network")
        expand_targets = [
            u for u in list(users_to_scan.values())[:config.MAX_SECOND_LEVEL_USERS]
            if u['username'] not in scanned_users
        ]
        log(f"\nExpanding {len(expand_targets)} accounts one level deeper "
            f"(followers + following of each)...")

        def _add_users(user_list):
            added = 0
            for u in user_list:
                if u['username'] not in users_to_scan:
                    users_to_scan[u['username']] = u
                    added += 1
            return added

        for i, user in enumerate(expand_targets, 1):
            if stop_event.is_set():
                break
            uname = user['username']

            # Followers of this account
            log(f"[{i}/{len(expand_targets)}] @{uname} — fetching followers...")
            try:
                sub = await get_followers(page, uname, config.MAX_SECOND_LEVEL_PER_USER)
                log(f"   → {_add_users(sub)} new accounts from followers")
            except Exception as e:
                log(f"   → followers skipped ({e})")

            if stop_event.is_set():
                break

            # Following of this account
            log(f"[{i}/{len(expand_targets)}] @{uname} — fetching following...")
            try:
                sub = await get_following(page, uname, config.MAX_SECOND_LEVEL_PER_USER)
                log(f"   → {_add_users(sub)} new accounts from following")
            except Exception as e:
                log(f"   → following skipped ({e})")

        users_to_scan.pop(my_username, None)
        total = len(users_to_scan)
        log(f"\nTotal unique accounts to scan: {total}")
        log("─" * 48)

        # ── Scan & match ──────────────────────────────────────────────────────
        status("Scanning")
        scan_count = 0
        block_count = 0

        for username, user_data in users_to_scan.items():
            if stop_event.is_set():
                break
            if username in scanned_users or username in blocked_users:
                continue

            img_url = user_data.get('profile_image_url', '')
            if not img_url:
                scanned_users[username] = True
                continue

            is_match, matched_ref = matcher.is_match(img_url)
            scanned_users[username] = True
            scan_count += 1

            if is_match:
                log(f"[MATCH] @{username}  →  '{matched_ref}'")
                success = await block_user(page, username, log=log)
                if success:
                    blocked_users[username] = matched_ref
                    block_count += 1
                    log(f"        ✓ Blocked")
                else:
                    log(f"        ✗ Block failed")
            else:
                log(f"[ ok  ] @{username}")

            stats(scan_count, block_count)

        # ── Save & finish ─────────────────────────────────────────────────────
        _save_json(config.BLOCKED_USERS_FILE, blocked_users)
        _save_json(config.SCANNED_USERS_FILE, scanned_users)

        await browser.close()

        if stop_event.is_set():
            done(f"Stopped early.  Scanned: {scan_count}  |  Blocked: {block_count}")
        else:
            done(f"Scan complete.  Scanned: {scan_count}  |  Blocked: {block_count}")
