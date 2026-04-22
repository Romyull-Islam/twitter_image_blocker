# X Photo Blocker

Automatically block X.com (Twitter) accounts whose profile photo matches a reference image you provide.

## How it works

1. Add reference profile photos in the app
2. Click **Start Scan** and log in to X.com once
3. The app scans your followers, following, and their networks
4. Any account whose profile photo matches is automatically blocked

## Download

Go to the [Releases](../../releases) tab and download the latest `XPhotoBlocker_Setup.exe`.

No Python required — just install and run.

## Run from source

```bash
# Linux / Mac
git clone https://github.com/Romyull-Islam/twitter_image_blocker.git
cd twitter_image_blocker
bash setup.sh
source venv/bin/activate
python app.py

# Windows
git clone https://github.com/Romyull-Islam/twitter_image_blocker.git
cd twitter_image_blocker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python app.py
```

## Notes

- No X API key required — uses browser automation
- Chromium (~170 MB) is downloaded automatically on first launch
- Scan history is saved so re-runs skip already-checked accounts
