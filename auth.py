import json
import os
import config


async def login(playwright):
    """Launch browser, restore session if available, otherwise prompt manual login."""
    browser = await playwright.chromium.launch(headless=False, slow_mo=50)

    # Try restoring saved session
    if os.path.exists(config.SESSION_FILE):
        with open(config.SESSION_FILE) as f:
            storage_state = json.load(f)
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()
        await page.goto('https://x.com/home', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        if 'login' not in page.url and 'x.com' in page.url:
            print("[auth] Restored saved session.")
            return browser, context, page

        print("[auth] Saved session expired.")
        await context.close()

    # Fresh login
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto('https://x.com/login', wait_until='domcontentloaded')

    print("\n[auth] Please log in to X.com in the browser window that just opened.")
    print("[auth] The script will continue automatically once you are logged in.\n")

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
    print("[auth] Session saved for future runs.")

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
