@echo off
setlocal
echo ============================================
echo   X Photo Blocker -- Windows Build Script
echo ============================================
echo.

:: Install build tools
pip install pyinstaller --quiet

:: Clean previous build
if exist dist\XPhotoBlocker rmdir /s /q dist\XPhotoBlocker
if exist build rmdir /s /q build

echo [1/2] Building with PyInstaller...
pyinstaller build.spec --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Build complete!
echo Output folder: dist\XPhotoBlocker\
echo.
echo Next step: open installer.iss in Inno Setup Compiler
echo and click Build to create the installer .exe
echo.
pause
