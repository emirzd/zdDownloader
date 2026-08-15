from flask import Flask, render_template, request, send_file, jsonify, Response
import yt_dlp
import os
import tempfile
import shutil
import glob
from datetime import datetime

app = Flask(__name__)

# =========================================================
# TEMEL AYARLAR
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMP_FOLDER = os.path.join(
    tempfile.gettempdir(),
    "zdDownloader"
)

os.makedirs(TEMP_FOLDER, exist_ok=True)


# =========================================================
# FFMPEG BUL
# =========================================================

def find_ffmpeg():

    # Render / sistem PATH
    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:
        return ffmpeg

    # Proje klasöründe ara
    for root, dirs, files in os.walk(BASE_DIR):

        for filename in files:

            if filename.lower() == "ffmpeg.exe":
                return root

    return None


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# GENEL YT-DLP AYARLARI
# =========================================================

YTDLP_OPTIONS = {
    "noplaylist": True,
    "quiet": False,
    "no_warnings": False,
    "retries": 5,
    "fragment_retries": 5
}


# =========================================================
# ANA SAYFA
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# ROBOTS.TXT
# =========================================================

@app.route("/robots.txt")
def robots_txt():

    robots = """User-agent: *
Allow: /

Sitemap: https://zddownloader.onrender.com/sitemap.xml
"""

    response = Response(
        robots,
        status=200,
        mimetype="text/plain"
    )

    # Google'ın yanlış cache kullanmasını azalt
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# =========================================================
# SITEMAP.XML
# =========================================================

@app.route("/sitemap.xml")
def sitemap():

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://zddownloader.onrender.com/</loc>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>
"""

    return Response(
        xml,
        status=200,
        mimetype="application/xml"
    )


# =========================================================
# GOOGLE SEARCH CONSOLE DOĞRULAMA
# =========================================================

@app.route("/googlee4bd61a0bd60b5ec.html")
def google_verification():

    filename = "googlee4bd61a0bd60b5ec.html"

    filepath = os.path.join(
        BASE_DIR,
        filename
    )

    if not os.path.isfile(filepath):

        return (
            "Google doğrulama dosyası bulunamadı.",
            404
        )

    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as file:

        content = file.read()

    return Response(
        content,
        status=200,
        mimetype="text/html"
    )


# =========================================================
# VIDEO BİLGİSİ
# =========================================================

@app.route(
    "/info",
    methods=["POST"]
)
def video_info():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "error": "Geçersiz istek."
            }), 400

        link = str(
            data.get(
                "link",
                ""
            )
        ).strip()

        if not link:

            return jsonify({
                "success": False,
                "error": "Video linki girilmedi."
            }), 400

        print()
        print("=" * 60)
        print("VIDEO BİLGİSİ")
        print("=" * 60)
        print(link)
        print()

        options = YTDLP_OPTIONS.copy()

        options.update({
            "skip_download": True
        })

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            info = ydl.extract_info(
                link,
                download=False
            )

        title = info.get(
            "title",
            "Video"
        )

        thumbnail = info.get(
            "thumbnail",
            ""
        )

        uploader = info.get(
            "uploader",
            ""
        )

        duration = info.get(
            "duration",
            0
        )

        # -------------------------------------------------
        # SÜRE
        # -------------------------------------------------

        duration_text = ""

        if duration:

            total = int(duration)

            hours = total // 3600

            minutes = (
                total % 3600
            ) // 60

            seconds = total % 60

            if hours:

                duration_text = (
                    f"{hours}:"
                    f"{minutes:02d}:"
                    f"{seconds:02d}"
                )

            else:

                duration_text = (
                    f"{minutes}:"
                    f"{seconds:02d}"
                )

        # -------------------------------------------------
        # KALİTELER
        # -------------------------------------------------

        qualities = set()

        for fmt in info.get(
            "formats",
            []
        ):

            height = fmt.get(
                "height"
            )

            if not height:
                continue

            try:

                height = int(height)

            except (
                ValueError,
                TypeError
            ):

                continue

            if height in (
                360,
                480,
                720,
                1080
            ):

                qualities.add(
                    height
                )

        qualities = sorted(
            qualities,
            reverse=True
        )

        # -------------------------------------------------
        # KALİTE BULUNAMAZSA
        # -------------------------------------------------

        if not qualities:

            all_heights = []

            for fmt in info.get(
                "formats",
                []
            ):

                height = fmt.get(
                    "height"
                )

                if height:

                    try:

                        all_heights.append(
                            int(height)
                        )

                    except (
                        ValueError,
                        TypeError
                    ):

                        pass

            if all_heights:

                qualities = [
                    max(all_heights)
                ]

        # -------------------------------------------------
        # VARSAYILAN KALİTE
        # -------------------------------------------------

        if qualities:

            default_quality = max(
                qualities
            )

        else:

            default_quality = 360

        print("Başlık:", title)
        print("Kullanıcı:", uploader)
        print("Süre:", duration_text)
        print("Kaliteler:", qualities)
        print()

        return jsonify({

            "success": True,

            "title": title,

            "thumbnail": thumbnail,

            "uploader": uploader,

            "duration": duration_text,

            "qualities": qualities,

            "default_quality":
                default_quality

        })

    except Exception as e:

        print()
        print("=" * 60)
        print("VIDEO BİLGİSİ HATASI")
        print("=" * 60)
        print(str(e))
        print()

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# VIDEO İNDİR
# =========================================================

@app.route(
    "/download",
    methods=["POST"]
)
def download():

    try:

        link = request.form.get(
            "link",
            ""
        ).strip()

        kalite = request.form.get(
            "kalite",
            "720"
        ).strip()

        if not link:

            return (
                "Video linki girilmedi.",
                400
            )

        # -------------------------------------------------
        # KALİTE
        # -------------------------------------------------

        try:

            limit = int(kalite)

        except (
            ValueError,
            TypeError
        ):

            limit = 720

        if limit not in (
            360,
            480,
            720,
            1080
        ):

            limit = 720

        print()
        print("=" * 60)
        print("İNDİRME BAŞLIYOR")
        print("=" * 60)
        print("Link:", link)
        print("Kalite:", str(limit) + "p")
        print("FFmpeg:", FFMPEG_PATH)
        print()

        # -------------------------------------------------
        # ESKİ DOSYALARI TEMİZLE
        # -------------------------------------------------

        for old_file in glob.glob(
            os.path.join(
                TEMP_FOLDER,
                "*"
            )
        ):

            try:

                if os.path.isfile(old_file):

                    os.remove(old_file)

            except Exception:

                pass

        # -------------------------------------------------
        # ÇIKTI DOSYASI
        # -------------------------------------------------

        output = os.path.join(

            TEMP_FOLDER,

            "%(title)s_%(id)s.%(ext)s"

        )

        # -------------------------------------------------
        # FORMAT
        # -------------------------------------------------

        format_secimi = (

            f"bestvideo[height<={limit}]"
            f"+bestaudio/"
            f"best[height<={limit}]/"
            "best"

        )

        # -------------------------------------------------
        # YT-DLP
        # -------------------------------------------------

        options = YTDLP_OPTIONS.copy()

        options.update({

            "format":
                format_secimi,

            "outtmpl":
                output,

            "merge_output_format":
                "mp4"

        })

        if FFMPEG_PATH:

            options[
                "ffmpeg_location"
            ] = FFMPEG_PATH

        # -------------------------------------------------
        # İNDİR
        # -------------------------------------------------

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            ydl.download([
                link
            ])

        # -------------------------------------------------
        # DOSYAYI BUL
        # -------------------------------------------------

        downloaded_files = [

            file

            for file in glob.glob(
                os.path.join(
                    TEMP_FOLDER,
                    "*"
                )
            )

            if os.path.isfile(file)

        ]

        if not downloaded_files:

            return (
                "Video indirildi fakat dosya bulunamadı.",
                500
            )

        downloaded_file = max(
            downloaded_files,
            key=os.path.getmtime
        )

        print()
        print("=" * 60)
        print("İNDİRME BAŞARILI")
        print(downloaded_file)
        print("=" * 60)
        print()

        # -------------------------------------------------
        # DOSYAYI GÖNDER
        # -------------------------------------------------

        return send_file(

            downloaded_file,

            as_attachment=True,

            download_name=os.path.basename(
                downloaded_file
            ),

            mimetype="video/mp4"

        )

    except Exception as e:

        print()
        print("=" * 60)
        print("İNDİRME HATASI")
        print("=" * 60)
        print(str(e))
        print()

        return (

            "İndirme sırasında hata oluştu:\n\n"
            + str(e),

            500

        )


# =========================================================
# SAĞLIK KONTROLÜ
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "zdDownloader"
    })


# =========================================================
# HATA SAYFASI
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return (
        "Sayfa bulunamadı.",
        404
    )


# =========================================================
# BAŞLAT
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print()
    print("=" * 60)
    print("                 zdDownloader")
    print("=" * 60)
    print()
    print("Port:", port)
    print("FFmpeg:", FFMPEG_PATH or "Bulunamadı")
    print()
    print("http://127.0.0.1:" + str(port))
    print()

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
