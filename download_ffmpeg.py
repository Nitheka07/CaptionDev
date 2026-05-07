import urllib.request
import zipfile
import os

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
zip_path = "ffmpeg_temp.zip"
print(f"Downloading FFmpeg from {url}...")
urllib.request.urlretrieve(url, zip_path)

print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    # Find the ffmpeg.exe inside the zip
    for file_info in zip_ref.infolist():
        if file_info.filename.endswith('ffmpeg.exe'):
            # Extract it locally
            file_info.filename = 'ffmpeg.exe' # Flat extraction
            zip_ref.extract(file_info, '.')
            print("Successfully extracted ffmpeg.exe to current directory!")
            break

print("Cleaning up...")
os.remove(zip_path)
print("Done!")
