#!/bin/bash
# One-shot startup script. Pre-built DB ships with the zip,
# so this just installs deps and starts the API.
set -e

echo "→ Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "→ Verifying database..."
if [ ! -f db/neet.db ]; then
    echo "  DB not found, building..."
    python etl/generate_curated_data.py
    python -m etl.load
    python -m etl.export_samples
else
    echo "  ✓ db/neet.db found ($(du -h db/neet.db | cut -f1))"
fi

echo ""
echo "→ Running smoke test..."
python smoke_test.py | tail -20

echo ""
echo "→ Starting API on http://localhost:8000"
echo "  OpenAPI docs: http://localhost:8000/docs"
echo "  Press Ctrl+C to stop"
echo ""
uvicorn api.main:app --host 0.0.0.0 --port 8000
