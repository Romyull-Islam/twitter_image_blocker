#!/bin/bash
set -e

echo "=== Setting up X.com Profile Photo Blocker ==="

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install Playwright's Chromium browser (free, no API key needed)
playwright install chromium

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To launch the app:"
echo "  source venv/bin/activate"
echo "  python app.py"
