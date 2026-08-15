from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import tempfile
import shutil
import glob

app = Flask(__name__)

# =========================================================
# GEÇİCİ KLASÖR
# =========================================================

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

    downloads = os.path.join(
        os.path.expanduser("~"),
        "Downloads"
    )

    if os.path.exists(downloads):

        for root, dirs, files in os.walk(downloads):

            if "ffmpeg.exe" in files:
                return root

    project = os.path.dirname(
        os.path.abspath(__file__)
    )

    for root, dirs, files in os.walk(project):

        if "ffmpeg.exe" in files:
            return root

    return None


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# YOUTUBE AYARLARI
# =========================================================

YOUTUBE_OPTIONS = {

    "js_runtimes": {
        "node": {}
    },

    "extractor_args": {
        "youtube": {
            "player_client": [
                "android_vr"
            ]
        }
    },

    "noplaylist": True,

    "quiet": False,

    "no_warnings": False,

    "retries": 5,

    "fragment_retries": 5,

    "http_headers": {
        "User-Agent": (
            "com.google.android.youtube/"
            "21.26.36 "
            "(Linux; U; Android 11) "
            "gzip"
        )
    }
}


# =========================================================
# ANA SAYFA
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# GOOGLE / ARAMA MOTORLARI ROBOTS.TXT
# =========================================================

@app.route("/robots.txt")
def robots():

    return (
        "User-agent: *\n"
        "Allow: /\n",
        200,
        {
            "Content-Type": "text/plain"
        }
    )


# =========================================================
# VIDEO BİLGİSİ + GERÇEK KALİTELER
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
        print("=" * 50)
        print("VIDEO BİLGİSİ ALINIYOR")
        print("=" * 50)
        print(link)
        print()


        options = YOUTUBE_OPTIONS.copy()

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


        # =================================================
        # TEMEL BİLGİLER
        # =================================================

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


        # =================================================
        # SÜRE
        # =================================================

        duration_text = ""

        if duration:

            total = int(duration)

            hours = total // 3600

            minutes = (
                total % 3600
            ) // 60

            seconds = (
                total % 60
            )

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


        # =================================================
        # GERÇEK MEVCUT KALİTELER
        # =================================================

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


        # =================================================
        # HİÇBİR KALİTE BULUNAMAZSA
        # =================================================

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

                en_yuksek = max(
                    all_heights
                )

                qualities = [
                    en_yuksek
                ]


        # =================================================
        # EN YÜKSEK KALİTE
        # =================================================

        if qualities:

            default_quality = max(
                qualities
            )

        else:

            default_quality = 360


        print("Başlık:", title)
        print("Süre:", duration_text)
        print(
            "Mevcut kaliteler:",
            qualities
        )
        print(
            "Varsayılan:",
            default_quality
        )
        print("BAŞARILI")
        print()


        # =================================================
        # JSON
        # =================================================

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
        print("=" * 50)
        print("VIDEO BİLGİSİ HATASI")
        print("=" * 50)
        print(e)
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


        if not FFMPEG_PATH:

            return (
                "FFmpeg bulunamadı.",
                500
            )


        # =================================================
        # KALİTE
        # =================================================

        try:

            limit = int(kalite)

        except (
            ValueError,
            TypeError
        ):

            limit = 720


        print()
        print("=" * 50)
        print("İNDİRME BAŞLIYOR")
        print("=" * 50)
        print("Kalite:", str(limit) + "p")
        print("FFmpeg:", FFMPEG_PATH)
        print()


        # =================================================
        # ESKİ DOSYALARI TEMİZLE
        # =================================================

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


        # =================================================
        # DOSYA
        # =================================================

        output = os.path.join(

            TEMP_FOLDER,

            "%(title)s_%(id)s.%(ext)s"

        )


        # =================================================
        # FORMAT
        # =================================================

        format_secimi = (

            f"bestvideo[height<={limit}]"
            f"+bestaudio/"
            f"best[height<={limit}]/"
            "best"

        )


        # =================================================
        # YT-DLP
        # =================================================

        options = YOUTUBE_OPTIONS.copy()

        options.update({

            "format":
                format_secimi,

            "outtmpl":
                output,

            "ffmpeg_location":
                FFMPEG_PATH,

            "merge_output_format":
                "mp4"

        })


        # =================================================
        # İNDİR
        # =================================================

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            ydl.download([
                link
            ])


        # =================================================
        # DOSYAYI BUL
        # =================================================

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


        print()
        print("=" * 50)
        print("İNDİRME BAŞARILI")
        print(file)
        print("=" * 50)
        print()


        # =================================================
        # DOSYAYI GÖNDER
        # =================================================

        return send_file(

            file,

            as_attachment=True,

            download_name=os.path.basename(
                file
            ),

            mimetype="video/mp4"

        )


    except Exception as e:

        print()
        print("=" * 50)
        print("İNDİRME HATASI")
        print("=" * 50)
        print(e)
        print()


        return (

            "İndirme sırasında hata oluştu:\n\n"
            + str(e),

            500

        )


# =========================================================
# BAŞLAT
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 50)
    print("             zdDownloader")
    print("=" * 50)
    print()

    print(
        "Python:",
        os.sys.executable
    )

    print(
        "yt-dlp:",
        yt_dlp.__file__
    )

    print(
        "FFmpeg:",
        FFMPEG_PATH
        if FFMPEG_PATH
        else "BULUNAMADI"
    )

    print()

    print(
        "zdDownloader başlatılıyor..."
    )

    print()

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )
            )
        ),
        debug=False
    )
