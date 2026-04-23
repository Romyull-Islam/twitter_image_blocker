import json
import os
import config
from browser_utils import find_system_chrome
from playwright_stealth import stealth_async

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

PROFILE_SELECTOR = '[data-testid="AppTabBar_Profile_Link"]'


async def login(playwright, log=print):
    launch_kwargs = {
        "headless": False,
        "slow_mo": 50,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    }

    system_chrome = find_system_chrome()
    if system_chrome:
        launch_kwargs["executable_path"] = system_chrome
        log(f"[browser] Using system Chrome: {system_chrome}")
    else:
        log("[browser] Using Playwright's Chromium")

    browser = await playwright.chromium.launch(**launch_kwargs)
    context_kwargs = {"user_agent": USER_AGENT}

    # ── Try restoring saved session ───────────────────────────────────────────
    if os.path.exists(config.SESSION_FILE):
        try:
            with open(config.SESSION_FILE) as f:
                storage_state = json.load(f)
            ctx = await browser.new_context(storage_state=storage_state, **context_kwargs)
            page = await ctx.new_page()
            await stealth_async(page)
            await page.goto('https://x.com/home', wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)

            # Confirm login by checking for the profile link
            link = await page.query_selector(PROFILE_SELECTOR)
            if link:
                href = await link.get_attribute('href')
                username = href.strip('/')
                log(f"[auth] Session restored — logged in as @{username}")
                return browser, ctx, page, username

            log("[auth] Session expired — please log in again.")
            await ctx.close()
        except Exception as e:
            log(f"[auth] Could not restore session ({e}) — starting fresh login.")

    # ── Fresh login ───────────────────────────────────────────────────────────
    ctx = await browser.new_context(**context_kwargs)
    page = await ctx.new_page()
    await stealth_async(page)
    await page.goto('https://x.com/login', wait_until='domcontentloaded')

    log("[auth] Browser opened — please log in to X.com.")
    log("[auth] Use your email/phone and password. Do NOT use 'Sign in with Google'.")
    log("[auth] This window will stay open until you finish logging in.")

    # Wait until the profile link appears = user is fully logged in (3 min timeout)
    await page.wait_for_selector(PROFILE_SELECTOR, timeout=180_000)
    await page.wait_for_timeout(1000)

    # Read username directly — no extra navigation needed
    link = await page.query_selector(PROFILE_SELECTOR)
    href = await link.get_attribute('href')
    username = href.strip('/')
    log(f"[auth] Login successful — logged in as @{username}")

    # Save session
    os.makedirs(config.DATA_DIR, exist_ok=True)
    state = await ctx.storage_state()
    with open(config.SESSION_FILE, 'w') as f:
        json.dump(state, f)
    log("[auth] Session saved — no login needed next time.")

    return browser, ctx, page, username


async def get_my_username(page):
    """Fallback username detection if not returned by login()."""
    try:
        await page.wait_for_selector(PROFILE_SELECTOR, timeout=10_000)
        link = await page.query_selector(PROFILE_SELECTOR)
        if link:
            href = await link.get_attribute('href')
            return href.strip('/')
    except Exception:
        pass
    return None
