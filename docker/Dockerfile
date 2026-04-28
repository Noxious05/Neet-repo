FROM python:3.11-slim

WORKDIR /app

# System packages (none needed for SQLite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Build the SQLite DB at image build time (deterministic)
RUN python etl/generate_curated_data.py && python -m etl.load && python -m etl.export_samples

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
