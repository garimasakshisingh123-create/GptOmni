FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements first for caching
COPY backend/requirements.txt ./backend/

# Install PyTorch CPU-only first to save space, then the rest
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r backend/requirements.txt

# Copy all source code (including backend and config files)
COPY . .

# Keep working directory at /app so Python can resolve the "backend" package import path
WORKDIR /app

# Expose port (7860 is Hugging Face Spaces default)
EXPOSE 7860

# Run uvicorn server, falling back to port 7860 if PORT is not set
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
