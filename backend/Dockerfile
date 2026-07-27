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

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
