from flask import Flask, request, jsonify, Response, stream_with_context
import yt_dlp
import re
import requests
import os

app = Flask(__name__)

# -----------------------------
# Utils
# -----------------------------
def is_valid_tiktok_url(url: str) -> bool:
    return bool(re.search(r"(vm\.tiktok\.com|tiktok\.com)", url))


def select_best_format(formats, watermark_required: bool):
    """
    Sélectionne le meilleur format MP4
    Priorité : sans watermark, puis fallback avec watermark
    """
    candidates = []

    for f in formats:
        if f.get("ext") != "mp4":
            continue
        if f.get("vcodec") == "none":
            continue

        has_watermark = f.get("watermark", True)

        if watermark_required or has_watermark is False:
            candidates.append(f)

    if not candidates:
        return None

    return max(candidates, key=lambda f: f.get("height") or 0)


# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "service": "TikTok Downloader API"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/tiktok/stream", methods=["POST"])
def stream_tiktok():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "Missing url"}), 400

    url = data["url"]

    if not is_valid_tiktok_url(url):
        return jsonify({"error": "Invalid TikTok URL"}), 400

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "extract_flat": False,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
            "Mobile/15E148 Safari/604.1"
        ),
    }

    try:
        # 1️⃣ Extraction des infos TikTok
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats")
        if not formats:
            return jsonify({"error": "No formats found"}), 404

        # 2️⃣ Priorité sans watermark
        selected = select_best_format(formats, watermark_required=False)
        watermark = False

        if not selected:
            selected = select_best_format(formats, watermark_required=True)
            watermark = True

        if not selected or "url" not in selected:
            return jsonify({"error": "No playable video"}), 404

        video_url = selected["url"]

        # 3️⃣ Headers réalistes (obligatoire pour TikTok CDN)
        headers = {
            "User-Agent": ydl_opts["user_agent"],
            "Referer": "https://www.tiktok.com/",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
        }

        # 4️⃣ Connexion au CDN TikTok
        r = requests.get(
            video_url,
            headers=headers,
            stream=True,
            timeout=30,
            allow_redirects=True,
        )

        content_type = r.headers.get("Content-Type", "")
        if r.status_code != 200 or "video" not in content_type:
            r.close()
            return jsonify({
                "error": "TikTok CDN blocked this server/IP",
                "status_code": r.status_code,
                "content_type": content_type,
            }), 403

        # 5️⃣ Streaming des chunks
        def generate():
            try:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                r.close()

        return Response(
            stream_with_context(generate()),
            content_type="video/mp4",
            headers={
                "Content-Disposition": "attachment; filename=tiktok.mp4",
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
                "X-Watermark": str(watermark).lower(),
            },
        )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({
            "error": "TikTok blocked or video unavailable",
            "details": str(e),
        }), 403

    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "details": str(e),
        }), 500


# -----------------------------
# Run (local uniquement)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)






