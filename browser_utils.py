"""
Browser detection and installation utilities.
Handles both development and PyInstaller frozen contexts.
"""

import os
import shutil
import sys


def find_system_chrome():
    """Return path to system Chrome/Chromium if installed, else None."""
    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\Chromium\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path

    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path

    # Linux or fallback — check PATH
    for name in ["google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "chrome"]:
        found = shutil.which(name)
        if found:
            return found

    return None


def playwright_chromium_installed():
    """Return True if Playwright's own bundled Chromium is downloaded."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return os.path.exists(p.chromium.executable_path)
    except Exception:
        return False


def any_browser_available():
    """Return True if any usable browser exists (system or Playwright)."""
    return find_system_chrome() is not None or playwright_chromium_installed()


def install_playwright_chromium():
    """
    Download Playwright's Chromium.
    Uses the playwright driver directly when running inside a PyInstaller bundle,
    because sys.executable is the frozen EXE (not Python) in that context.
    """
    if getattr(sys, "frozen", False):
        from playwright._impl._driver import compute_driver_executable
        driver_executable, driver_cli = compute_driver_executable()
        import subprocess
        subprocess.run(
            [str(driver_executable), driver_cli, "install", "chromium"],
            check=True,
        )
    else:
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )
