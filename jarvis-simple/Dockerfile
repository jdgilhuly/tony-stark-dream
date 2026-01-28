# JARVIS Simple - Single Container Build
FROM node:20-slim AS base

# Install system dependencies for audio and Whisper
RUN apt-get update && apt-get install -y \
    # Audio recording
    alsa-utils \
    pulseaudio \
    sox \
    libsox-fmt-all \
    # Build tools for native modules
    build-essential \
    python3 \
    # TTS
    espeak \
    # Whisper dependencies
    ffmpeg \
    wget \
    git \
    cmake \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install whisper.cpp
WORKDIR /opt
RUN git clone https://github.com/ggerganov/whisper.cpp.git && \
    cd whisper.cpp && \
    make && \
    # Download base.en model
    bash ./models/download-ggml-model.sh base.en && \
    # Create symlink for easy access
    ln -s /opt/whisper.cpp/main /usr/local/bin/whisper-cpp

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create app directory
WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build

# Create non-root user for security
RUN useradd -m jarvis && \
    chown -R jarvis:jarvis /app

# Set up Whisper model path for the user
RUN mkdir -p /home/jarvis/.whisper && \
    cp /opt/whisper.cpp/models/ggml-base.en.bin /home/jarvis/.whisper/ && \
    chown -R jarvis:jarvis /home/jarvis/.whisper

USER jarvis

# Set working directory to user's workspace (will be mounted)
WORKDIR /workspace

# Environment variables
ENV NODE_ENV=production
ENV WHISPER_MODEL=/home/jarvis/.whisper/ggml-base.en.bin

# Entry point
ENTRYPOINT ["node", "/app/dist/index.js"]
