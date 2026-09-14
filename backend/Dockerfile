FROM python:3.11-slim

# Prevent Python from creating .pyc files
# and make logs appear immediately.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System dependencies required by:
# - OpenCV
# - Ultralytics / YOLO
# - audio processing through ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Backend working directory
WORKDIR /app

# Copy dependency file first so Docker can cache
# the dependency installation layer.
COPY requirements.txt .

# Install Python dependencies.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend.
COPY . .

# Render supplies the actual PORT at runtime.
EXPOSE 10000

# Start FastAPI.
# Render's PORT takes precedence; 10000 is the fallback.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]