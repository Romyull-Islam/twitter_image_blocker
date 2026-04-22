import config


async def block_user(page, username):
    """Navigate to a profile and block the user. Returns True on success."""
    try:
        await page.goto(f'https://x.com/{username}', wait_until='domcontentloaded')
        await page.wait_for_timeout(config.PAGE_LOAD_DELAY)

        # Open the "..." actions menu on the profile
        more_btn = await page.query_selector('[data-testid="userActions"]')
        if not more_btn:
            print(f"    [block] Could not find actions menu for @{username}")
            return False

        await more_btn.click()
        await page.wait_for_timeout(config.ACTION_DELAY)

        # Click Block
        block_item = await page.query_selector('[data-testid="block"]')
        if not block_item:
            # Menu might use aria label on some versions
            block_item = await page.get_by_text('Block @', exact=False).first.element_handle()
        if not block_item:
            print(f"    [block] Could not find Block option for @{username}")
            # Close menu by pressing Escape
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
        print(f"    [block] Error blocking @{username}: {e}")
        return False
