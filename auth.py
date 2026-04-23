import json
import os
import config
from browser_utils import find_system_chrome


async def login(playwright, log=print):
    """Launch browser, restore session if available, otherwise prompt manual login."""
    launch_kwargs = {"headless": False, "slow_mo": 50}
    system_chrome = find_system_chrome()
    if system_chrome:
        launch_kwargs["executable_path"] = system_chrome
        log(f"[browser] Using system Chrome: {system_chrome}")
    else:
        log("[browser] Using Playwright's Chromium")

    browser = await playwright.chromium.launch(**launch_kwargs)

    # Try restoring saved session
    if os.path.exists(config.SESSION_FILE):
        with open(config.SESSION_FILE) as f:
            storage_state = json.load(f)
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        await page.goto('https://x.com/home', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        if 'login' not in page.url and 'x.com' in page.url:
            log("[auth] Session restored — no login needed.")
            return browser, context, page

        log("[auth] Session expired — please log in again.")
        await context.close()

    # Fresh login
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto('https://x.com/login', wait_until='domcontentloaded')
    log("[auth] Browser opened — please log in to X.com.")
    log("[auth] The scan will start automatically after you log in.")

    # Wait until redirected away from login (up to 3 minutes)
    await page.wait_for_function(
        "() => !window.location.href.includes('/login') && !window.location.href.includes('/i/flow')",
        timeout=180_000
    )
    await page.wait_for_timeout(2000)

    # Persist session
    os.makedirs(config.DATA_DIR, exist_ok=True)
    state = await context.storage_state()
    with open(config.SESSION_FILE, 'w') as f:
        json.dump(state, f)
    log("[auth] Login successful — session saved for future runs.")

    return browser, context, page


async def get_my_username(page):
    """Extract the logged-in user's username from the sidebar profile link."""
    try:
        await page.goto('https://x.com/home', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        link = await page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
        if link:
            href = await link.get_attribute('href')
            return href.strip('/')
    except Exception:
        pass
    return None
