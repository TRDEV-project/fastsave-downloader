from flask import Flask, request, jsonify, send_file
from urllib.parse import urlparse
from pathlib import Path
import tempfile
import shutil
import yt_dlp

app = Flask(__name__, static_folder=".", static_url_path="")

@app.get("/")
def home():
    return app.send_static_file("index.html")

def valid_video_url(url, platform):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https"):
            return False
        if platform == "tiktok":
            return host == "tiktok.com" or host.endswith(".tiktok.com")
        if platform == "instagram":
            return host == "instagram.com" or host.endswith(".instagram.com")
    except Exception:
        return False
    return False

@app.post("/api/extract")
def extract_video():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    platform = (data.get("platform") or "").lower().strip()

    if platform not in ("tiktok", "instagram"):
        return jsonify(error="Unsupported platform"), 400

    if not url or len(url) > 2048:
        return jsonify(error="Invalid URL"), 400

    if not valid_video_url(url, platform):
        return jsonify(error="Invalid platform URL"), 400

    temp_dir = tempfile.mkdtemp(prefix="fastsave_")
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': str(Path(temp_dir) / 'video.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Referer': 'https://www.tiktok.com/',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = info.get('filepath') or ydl.prepare_filename(info)

        video_path = Path(filepath)
        if not video_path.is_file():
            candidates = list(Path(temp_dir).glob("video.*"))
            if not candidates:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return jsonify(error="Could not download video file."), 400
            video_path = candidates[0]

        filename = f"{platform}-video{video_path.suffix}"
        
        # Safe send file and cleanup after close
        response = send_file(
            str(video_path),
            as_attachment=True,
            download_name=filename,
            mimetype="application/octet-stream"
        )
        
        @response.call_on_close
        def cleanup():
            shutil.rmtree(temp_dir, ignore_errors=True)

        return response

    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify(error=str(exc)), 500

if __name__ == "__main__":
    print("FastSave Robust Mode running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)