FROM python:3.11-slim

WORKDIR /app

# ffmpeg renders video ads (Ken Burns pans, caption overlays, audio mixing);
# espeak-ng is the free local text-to-speech engine used for voiceovers.
# Both run as plain subprocess calls from video_generator.py, not Python
# packages, so they're installed here rather than in requirements.txt.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg espeak-ng fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud Run injects its own PORT (usually 8080) and expects the container to
# listen on it — shell-form CMD so $PORT actually expands; 8000 is only the
# fallback for docker-compose/local runs where PORT isn't set.
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
