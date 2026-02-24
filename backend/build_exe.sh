#!/bin/sh
# Build backend binary using PyInstaller (Unix/mac)
set -e
python3 -m pip install -r requirements.txt
pyinstaller --onefile --name api api.py
if [ -f dist/api ]; then
  echo "api binary created at $(pwd)/dist/api"
  exit 0
else
  echo "ERROR: api binary not found in $(pwd)/dist"
  exit 1
fi
