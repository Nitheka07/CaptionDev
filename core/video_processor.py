import subprocess
import os
import shutil

def burn_subtitles(input_video_path, ass_subtitle_path, output_video_path):
    """
    Uses FFmpeg to burn .ass subtitles into the video track.
    Assumes FFmpeg is available in the system PATH.
    """
    
    ffmpeg_exe = os.path.join(os.path.dirname(__file__), '..', 'ffmpeg.exe')
    
    # We must ensure path format for ASS filter is correct, especially on Windows
    # ASS filter requires escaping colons/backslashes if using absolute paths
    ass_path_escaped = ass_subtitle_path.replace('\\', '\\\\').replace(':', '\\:')
    
    # 1. Build Isolated Fontconfig cache XML to circumvent permissions
    fonts_dir = os.path.join(os.path.dirname(__file__), '..', 'fonts')
    fonts_conf_path = os.path.join(fonts_dir, 'fonts.conf')
    # Use forward slashes for fontconfig formatting
    safe_fonts_dir = fonts_dir.replace('\\', '/')
    
    with open(fonts_conf_path, 'w', encoding='utf-8') as f:
        f.write(f'''<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <dir>{safe_fonts_dir}</dir>
    <cachedir>{safe_fonts_dir}/cache</cachedir>
</fontconfig>''')
    
    # 2. Inject FONTCONFIG_FILE into execution environment mapping
    proc_env = os.environ.copy()
    proc_env['FONTCONFIG_FILE'] = fonts_conf_path.replace('\\', '/')
    proc_env['FONTCONFIG_PATH'] = fonts_dir.replace('\\', '/')
    
    command = [
        ffmpeg_exe, 
        "-y",               # Overwrite
        "-i", input_video_path,
        "-vf", f"ass='{ass_path_escaped}'",
        "-c:v", "libx264",  # Use x264 for encoding
        "-crf", "23",       # Balance size/quality
        "-c:a", "copy",     # Don't re-encode audio!
        output_video_path
    ]
    
    try:
        subprocess.run(command, env=proc_env, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error burning subtitles: {e}")
        raise Exception(f"Video processing failed: {e}")
