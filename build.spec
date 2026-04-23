# PyInstaller spec file — run with: pyinstaller build.spec

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect all customtkinter assets (themes, fonts, images)
ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

# Collect playwright_stealth JS files
stealth_datas, stealth_binaries, stealth_hiddenimports = collect_all("playwright_stealth")

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=ctk_binaries + stealth_binaries,
    datas=ctk_datas + stealth_datas + [("icon.ico", ".")],
    hiddenimports=ctk_hiddenimports + stealth_hiddenimports + [
        "PIL",
        "PIL._tkinter_finder",
        "imagehash",
        "playwright",
        "playwright._impl._driver",
        "requests",
        "browser_utils",
        "playwright_stealth",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="XPhotoBlocker",
    debug=False,
    strip=False,
    upx=True,
    console=False,          # no black terminal window
    icon="icon.ico" if os.path.exists("icon.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="XPhotoBlocker",
)
