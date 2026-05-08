import subprocess
import os
from faster_whisper import WhisperModel

print("Loading WhisperModel (base/cpu)...")
model = WhisperModel("base", device="cpu", compute_type="int8")

def process_audio(video_path, audio_output_path):
    """
    Extracts audio from video and sends it to OpenAI Whisper for word-level transcription.
    """
    local_ffmpeg = os.path.join(os.path.dirname(__file__), '..', 'ffmpeg.exe')
    ffmpeg_exe = local_ffmpeg if os.path.isfile(local_ffmpeg) else 'ffmpeg'
    # 1. Extract audio and compress as mp3 using ffmpeg
    command = [
        ffmpeg_exe, "-y", "-i", video_path,
        "-q:a", "0", "-map", "a", audio_output_path
    ]
    # Capture output in case of error
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg audio extraction failed: {result.stderr}")

    # 2. Transcribe locally using faster-whisper
    segments, info = model.transcribe(audio_output_path, word_timestamps=True)
    
    word_segments = []
    # faster-whisper returns a generator, so we iterate through it
    for segment in segments:
        for word in segment.words:
            word_segments.append({
                "word": word.word.strip(),
                "start": word.start,
                "end": word.end
            })
            
    return word_segments
