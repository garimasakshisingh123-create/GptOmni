FROM python:3.11-slim

# Install system dependencies needed for compiling certain packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Optimize PyTorch installation: Install CPU-only version first to save ~2GB of image space,
# then install the rest of requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose port (7860 is Hugging Face Spaces default; Render/Koyeb will set PORT environment variable)
EXPOSE 7860

# Run uvicorn server, falling back to port 7860 if PORT is not set
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
