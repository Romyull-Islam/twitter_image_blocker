# PyInstaller spec file — run with: pyinstaller build.spec

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all assets for packages that ship data/JS/binaries
ctk_datas,      ctk_binaries,      ctk_hidden      = collect_all("customtkinter")
stealth_datas,  stealth_binaries,  stealth_hidden  = collect_all("playwright_stealth")
pw_datas,       pw_binaries,       pw_hidden       = collect_all("playwright")

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=ctk_binaries + stealth_binaries + pw_binaries,
    datas=ctk_datas + stealth_datas + pw_datas + [("icon.ico", ".")],
    hiddenimports=ctk_hidden + stealth_hidden + pw_hidden + [
        "PIL",
        "PIL._tkinter_finder",
        "imagehash",
        "requests",
        "browser_utils",
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
    console=False,
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
