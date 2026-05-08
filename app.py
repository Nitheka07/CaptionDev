import os
import uuid
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from threading import Thread
import time

from core.whisper_transcriber import process_audio
from core.subtitle_generator import TextToAssGenerator
from core.video_processor import burn_subtitles

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 130 * 1024 * 1024 # 130 MB max
ALLOWED_EXTENSIONS = {'mp4', 'mov'}

# Ensure directories exist
for folder in ['raw', 'audio', 'subs', 'output']:
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], folder), exist_ok=True)

tasks = {}
MAX_WORDS_PER_REQUEST = 5000


def fail_task(task_id, message):
    tasks[task_id] = {'status': 'error', 'message': message, 'progress': 0}


def parse_words(raw_words):
    if not isinstance(raw_words, list):
        raise ValueError("Words payload must be an array.")
    if len(raw_words) == 0:
        raise ValueError("No words available to burn into subtitles.")
    if len(raw_words) > MAX_WORDS_PER_REQUEST:
        raise ValueError("Transcription is too large to process in one request.")

    normalized = []
    for idx, item in enumerate(raw_words):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid word payload at index {idx}.")
        word = str(item.get('word', '')).strip()
        start = item.get('start')
        end = item.get('end')
        if not word:
            continue
        if start is None or end is None:
            raise ValueError(f"Missing timestamps at word index {idx}.")
        try:
            start_f = float(start)
            end_f = float(end)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid timestamps at word index {idx}.")
        if end_f <= start_f:
            raise ValueError(f"End time must be greater than start time at word index {idx}.")
        normalized.append({"word": word, "start": start_f, "end": end_f})

    if not normalized:
        raise ValueError("All subtitle words were empty after cleanup.")
    return normalized


def recover_filename_from_task_id(task_id):
    raw_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'raw')
    if not os.path.isdir(raw_dir):
        return None
    prefix = f"{task_id}_"
    for entry in os.listdir(raw_dir):
        if entry.startswith(prefix):
            return entry
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

def background_transcribe(task_id, filename):
    tasks[task_id] = {'status': 'processing', 'message': 'Extracting audio & Transcribing with AI...', 'progress': 30}
    try:
        raw_video_path = os.path.join(app.config['UPLOAD_FOLDER'], 'raw', filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', f"{task_id}.mp3")
        
        word_segments = process_audio(raw_video_path, audio_path)
        
        # We now just return the words to the frontend!
        tasks[task_id]['status'] = 'transcription_ready'
        tasks[task_id]['message'] = 'Transcription complete!'
        tasks[task_id]['progress'] = 50
        tasks[task_id]['words'] = word_segments
        tasks[task_id]['filename'] = filename # Save for step 2

    except Exception as e:
        fail_task(task_id, str(e))

def background_burn(task_id, filename, words, style, position, font_name, hl_enable=True, custom_color='#00ffff', bg_enable=True, bg_color='#000000', bg_opacity=50):
    tasks[task_id] = {'status': 'processing', 'message': 'Generating Subtitles and Burning (this takes time)...', 'progress': 75}
    try:
        raw_video_path = os.path.join(app.config['UPLOAD_FOLDER'], 'raw', filename)
        ass_path = os.path.join(app.config['UPLOAD_FOLDER'], 'subs', f"{task_id}.ass")
        
        generator = TextToAssGenerator(word_segments=words, style=style, position=position, font_name=font_name, hl_enable=hl_enable, custom_color=custom_color, bg_enable=bg_enable, bg_color=bg_color, bg_opacity=bg_opacity)
        generator.generate_ass(ass_path)
        
        output_filename = f"captioned_{filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output', output_filename)
        
        burn_subtitles(raw_video_path, ass_path, output_path)
        
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['message'] = 'Video processing complete!'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['download_url'] = f"/download/{output_filename}"

    except Exception as e:
        fail_task(task_id, str(e))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file part'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        task_id = str(uuid.uuid4())
        unique_filename = f"{task_id}_{filename}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'raw', unique_filename)
        file.save(filepath)
        
        tasks[task_id] = {'status': 'queued', 'message': 'Upload complete. Queuing task...', 'progress': 10}
        
        thread = Thread(target=background_transcribe, args=(task_id, unique_filename))
        thread.start()
        
        return jsonify({'task_id': task_id}), 202
        
    return jsonify({'error': 'Invalid file type. Only MP4 and MOV allowed.'}), 400

@app.route('/burn', methods=['POST'])
def render_burn():
    data = request.get_json(silent=True) or {}
    task_id = data.get('task_id')

    if not task_id:
        return jsonify({'error': 'Missing task ID'}), 400

    if task_id not in tasks or 'filename' not in tasks.get(task_id, {}):
        recovered_filename = recover_filename_from_task_id(task_id)
        if recovered_filename:
            tasks[task_id] = {
                'status': 'recovered',
                'message': 'Recovered session after server restart.',
                'progress': 60,
                'filename': recovered_filename
            }
        else:
            return jsonify({'error': 'Invalid session or task ID'}), 400

    if task_id not in tasks or 'filename' not in tasks[task_id]:
        return jsonify({'error': 'Invalid session or task ID'}), 400
    if tasks[task_id].get('status') == 'processing':
        return jsonify({'error': 'Task is already processing. Please wait.'}), 409
        
    try:
        words = parse_words(data.get('words', []))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    style = data.get('style', 'karaoke')
    position = data.get('position', 'middle')
    font = data.get('font', 'Arial')
    color = data.get('color', '#00ffff')
    hl_enable = data.get('hl_enable', True)
    bg_enable = data.get('bg_enable', True)
    bg_color = data.get('bg_color', '#000000')
    bg_opacity = data.get('bg_opacity', 50)
    filename = tasks[task_id]['filename']
    
    tasks[task_id]['status'] = 'queued_burn'
    tasks[task_id]['progress'] = 60
    
    thread = Thread(target=background_burn, args=(task_id, filename, words, style, position, font, hl_enable, color, bg_enable, bg_color, bg_opacity))
    thread.start()
    
    return jsonify({'status': 'burning'}), 200

@app.route('/status/<task_id>')
def task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'output'), filename, as_attachment=True)

if __name__ == '__main__':
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, port=port, threaded=True, use_reloader=False)
