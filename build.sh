#!/usr/bin/env bash
set -euo pipefail
# Build usado no Render — instala frontend + API Python
npm ci
npm run build
pip install -r python-api/requirements.txt
