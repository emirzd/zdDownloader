from flask import Flask, render_template, request, send_file, jsonify, Response
import yt_dlp
import os
import tempfile
import shutil
import glob

app = Flask(__name__)

# =========================================================
# AYARLAR
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

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:
        return ffmpeg

    for root, dirs, files in os.walk(BASE_DIR):

        for filename in files:

            if filename.lower() in [
                "ffmpeg",
                "ffmpeg.exe"
            ]:

                return root

    return None


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# YT-DLP AYARLARI
# =========================================================

YOUTUBE_OPTIONS = {

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
# GOOGLE SEARCH CONSOLE DOĞRULAMA
# =========================================================

@app.route("/googlee4bd61a0bd60b5ec.html")
def google_verification():

    verification_file = os.path.join(
        BASE_DIR,
        "googlee4bd61a0bd60b5ec.html"
    )

    if not os.path.isfile(verification_file):

        return (
            "Google doğrulama dosyası bulunamadı.",
            404
        )

    with open(
        verification_file,
        "r",
        encoding="utf-8"
    ) as file:

        content = file.read()

    return Response(
        content,
        mimetype="text/html"
    )


# =========================================================
# ROBOTS.TXT
# =========================================================

@app.route("/robots.txt")
def robots():

    content = (
        "User-agent: *\n"
        "Allow: /\n"
    )

    return Response(
        content,
        mimetype="text/plain"
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

        print("=" * 50)
        print("VIDEO BİLGİSİ ALINIYOR")
        print(link)
        print("=" * 50)

        options = YOUTUBE_OPTIONS.copy()

        options["skip_download"] = True

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

            if height in [
                360,
                480,
                720,
                1080
            ]:

                qualities.add(
                    height
                )

        qualities = sorted(
            qualities,
            reverse=True
        )

        # -------------------------------------------------
        # KALİTE YOKSA
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

        print("=" * 50)
        print("VIDEO BİLGİSİ HATASI")
        print(e)
        print("=" * 50)

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

        try:

            limit = int(kalite)

        except (
            ValueError,
            TypeError
        ):

            limit = 720

        # -------------------------------------------------
        # ESKİ DOSYALARI TEMİZLE
        # -------------------------------------------------

        for file in glob.glob(
            os.path.join(
                TEMP_FOLDER,
                "*"
            )
        ):

            try:

                if os.path.isfile(file):

                    os.remove(file)

            except Exception:

                pass

        # -------------------------------------------------
        # ÇIKTI
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

        options = YOUTUBE_OPTIONS.copy()

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

        files = [

            file

            for file in glob.glob(
                os.path.join(
                    TEMP_FOLDER,
                    "*"
                )
            )

            if os.path.isfile(file)

        ]

        if not files:

            return (
                "Video indirildi fakat "
                "dosya bulunamadı.",
                500
            )

        file = max(
            files,
            key=os.path.getmtime
        )

        return send_file(

            file,

            as_attachment=True,

            download_name=os.path.basename(
                file
            ),

            mimetype="video/mp4"

        )

    except Exception as e:

        print("=" * 50)
        print("İNDİRME HATASI")
        print(e)
        print("=" * 50)

        return (

            "İndirme sırasında hata oluştu:\n\n"
            + str(e),

            500

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

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
