import config


async def block_user(page, username, log=print):
    """Navigate to a profile and block the user. Returns True on success."""
    try:
        await page.goto(f'https://x.com/{username}', wait_until='domcontentloaded')
        await page.wait_for_timeout(config.PAGE_LOAD_DELAY)

        # Open the "..." actions menu on the profile
        more_btn = await page.query_selector('[data-testid="userActions"]')
        if not more_btn:
            log(f"    [block] Could not find actions menu for @{username}")
            return False

        await more_btn.click()
        await page.wait_for_timeout(config.ACTION_DELAY)

        # Click Block (primary selector)
        block_item = await page.query_selector('[data-testid="block"]')

        # Fallback: match any menu item starting with "Block @"
        if not block_item:
            try:
                block_item = await page.locator('div[role="menuitem"]:has-text("Block @")').first.element_handle(timeout=2000)
            except Exception:
                block_item = None

        if not block_item:
            log(f"    [block] Could not find Block option for @{username}")
            await page.keyboard.press('Escape')
            return False

        await block_item.click()
        await page.wait_for_timeout(config.ACTION_DELAY)

        # Confirm the block dialog
        confirm_btn = await page.query_selector('[data-testid="confirmationSheetConfirm"]')
        if confirm_btn:
            await confirm_btn.click()
            await page.wait_for_timeout(1000)

        return True

    except Exception as e:
        log(f"    [block] Error blocking @{username}: {e}")
        return False
