#!/usr/bin/env bash
# Rebuild from data/ and push to GitHub Pages.
set -euo pipefail
cd "$(dirname "$0")"
python3 build.py
git add -A
git commit -m "${1:-Update caravan site}" || echo "Nothing new to commit."
git push
