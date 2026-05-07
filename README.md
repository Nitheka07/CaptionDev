# CaptionDev

CaptionDev is a local Flask app that creates styled burned-in subtitles for short videos.
It transcribes speech with `faster-whisper`, lets you edit words in-browser, and renders the final output with FFmpeg.

## Features

- Upload MP4/MOV videos (up to 130 MB).
- Local transcription using Whisper word timestamps.
- Word-by-word transcript editing before render.
- Subtitle style controls:
  - Typewriter or normal style
  - Top / middle / bottom position
  - Font selection
  - Active word highlight color
  - Optional background box with opacity control
- Burned-in final video download.

## Tech Stack

- Python + Flask
- `faster-whisper`
- FFmpeg (`ffmpeg.exe`, `ffplay.exe`, `ffprobe.exe`)
- HTML/CSS/Vanilla JavaScript

## Project Structure

- `app.py` - Flask routes and async task flow.
- `core/whisper_transcriber.py` - audio extraction + Whisper transcription.
- `core/subtitle_generator.py` - ASS subtitle generation logic.
- `core/video_processor.py` - FFmpeg subtitle burn step.
- `templates/index.html` - main UI.
- `static/` - frontend assets.
- `uploads/` - temporary processing files and output.

## Setup

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. Open:

`http://127.0.0.1:5000`

## Notes

- This project is intended for local development usage.
- FFmpeg binaries are expected in the project root.
- Uploaded files and generated outputs are stored under `uploads/`.
