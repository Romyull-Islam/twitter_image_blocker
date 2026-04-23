import config


async def _scroll_and_collect(page, max_count):
    """
    Scroll the current followers/following page and collect user data.
    Returns list of dicts: {username, profile_image_url}
    """
    seen = {}
    no_new_streak = 0

    while len(seen) < max_count:
        cells = await page.query_selector_all('[data-testid="UserCell"]')

        for cell in cells:
            # Profile image
            img = await cell.query_selector('img[src*="pbs.twimg.com/profile_images"]')
            if not img:
                continue
            img_src = await img.get_attribute('src')

            # Username — first anchor whose href looks like /username (no subpaths)
            anchors = await cell.query_selector_all('a[href^="/"]')
            username = None
            for a in anchors:
                href = await a.get_attribute('href')
                if not href:
                    continue
                parts = href.strip('/').split('/')
                # Ignore links like /i/..., /settings/..., etc.
                if len(parts) == 1 and parts[0] and not parts[0].startswith('i'):
                    username = parts[0]
                    break

            if username and username not in seen:
                seen[username] = {
                    'username': username,
                    'profile_image_url': img_src
                }

        # Scroll down
        prev_count = len(seen)
        await page.evaluate('window.scrollBy(0, 800)')
        await page.wait_for_timeout(config.SCROLL_DELAY)

        if len(seen) == prev_count:
            no_new_streak += 1
            if no_new_streak >= 4:
                break  # Nothing new after 4 scrolls — end of list
        else:
            no_new_streak = 0

    return list(seen.values())[:max_count]


async def get_followers(page, username, max_count=None):
    max_count = max_count or config.MAX_FOLLOWERS_SCAN
    url = f'https://x.com/{username}/followers'
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(config.PAGE_LOAD_DELAY)
    return await _scroll_and_collect(page, max_count)


async def get_following(page, username, max_count=None):
    max_count = max_count or config.MAX_FOLLOWING_SCAN
    url = f'https://x.com/{username}/following'
    await page.goto(url, wait_until='domcontentloaded')
    await page.wait_for_timeout(config.PAGE_LOAD_DELAY)
    return await _scroll_and_collect(page, max_count)
