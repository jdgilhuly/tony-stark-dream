FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for TTS (espeak) and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    libespeak-ng1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/*/libespeak-ng.so.1 /usr/lib/libespeak.so.1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8002

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
