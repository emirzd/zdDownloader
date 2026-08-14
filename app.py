from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import tempfile
import glob
import imageio_ffmpeg

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
# FFMPEG
# =========================================================

def find_ffmpeg():
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        if ffmpeg and os.path.exists(ffmpeg):
            return ffmpeg

    except Exception as e:
        print("FFmpeg bulunamadı:", e)

    return None


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# YOUTUBE AYARLARI
# =========================================================

BASE_OPTIONS = {
    "noplaylist": True,
    "quiet": False,
    "no_warnings": False,
    "retries": 3,
    "fragment_retries": 3,
}


# =========================================================
# YOUTUBE SEÇENEKLERİ
# =========================================================

def youtube_options(client):

    options = BASE_OPTIONS.copy()

    options["extractor_args"] = {
        "youtube": {
            "player_client": [client]
        }
    }

    return options


# =========================================================
# SÜREYİ DÜZENLE
# =========================================================

def format_duration(duration):

    if not duration:
        return ""

    try:
        total = int(duration)
    except (ValueError, TypeError):
        return ""

    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60

    if hours:
        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes}:"
        f"{seconds:02d}"
    )


# =========================================================
# VİDEO BİLGİSİ AL
# =========================================================

def extract_video_info(link):

    errors = []

    # İlk yöntem
    clients = [
        "android_vr",
        "web_embedded"
    ]

    for client in clients:

        try:

            print()
            print("=" * 55)
            print("VIDEO BİLGİSİ")
            print("Client:", client)
            print("URL:", link)
            print("=" * 55)

            options = youtube_options(client)

            options["skip_download"] = True

            with yt_dlp.YoutubeDL(options) as ydl:

                info = ydl.extract_info(
                    link,
                    download=False
                )

            if info:
                return info

        except Exception as e:

            print(
                f"{client} başarısız:",
                str(e)
            )

            errors.append(
                f"{client}: {str(e)}"
            )

    raise Exception(
        "Video bilgisi alınamadı.\n\n"
        + "\n".join(errors)
    )


# =========================================================
# VİDEO İNDİR
# =========================================================

def download_video(link, kalite):

    if not FFMPEG_PATH:

        raise Exception(
            "FFmpeg bulunamadı."
        )

    try:
        limit = int(kalite)
    except (ValueError, TypeError):
        limit = 720

    output = os.path.join(
        TEMP_FOLDER,
        "%(title)s_%(id)s.%(ext)s"
    )

    format_secimi = (
        f"bestvideo[height<={limit}]"
        f"+bestaudio/"
        f"best[height<={limit}]/"
        f"best"
    )

    errors = []

    clients = [
        "android_vr",
        "web_embedded"
    ]

    for client in clients:

        try:

            print()
            print("=" * 55)
            print("VİDEO İNDİRİLİYOR")
            print("Client:", client)
            print("Kalite:", str(limit) + "p")
            print("FFmpeg:", FFMPEG_PATH)
            print("=" * 55)

            options = youtube_options(client)

            options.update({

                "format": format_secimi,

                "outtmpl": output,

                "ffmpeg_location": FFMPEG_PATH,

                "merge_output_format": "mp4"

            })

            with yt_dlp.YoutubeDL(options) as ydl:

                ydl.download([
                    link
                ])

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

                raise Exception(
                    "İndirilen dosya bulunamadı."
                )

            return max(
                files,
                key=os.path.getmtime
            )

        except Exception as e:

            print(
                f"{client} indirme başarısız:",
                str(e)
            )

            errors.append(
                f"{client}: {str(e)}"
            )

    raise Exception(
        "Video indirilemedi.\n\n"
        + "\n".join(errors)
    )


# =========================================================
# ANA SAYFA
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
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

                "error":
                    "Geçersiz istek."

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

                "error":
                    "Video linki girilmedi."

            }), 400

        info = extract_video_info(
            link
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

        duration = format_duration(
            info.get(
                "duration",
                0
            )
        )

        # =================================================
        # KALİTELER
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
        # KALİTE YOKSA
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

                qualities = [
                    max(all_heights)
                ]

        default_quality = (
            max(qualities)
            if qualities
            else 360
        )

        print()
        print("BAŞLIK:", title)
        print("SÜRE:", duration)
        print("KALİTELER:", qualities)
        print("VARSAYILAN:", default_quality)
        print()

        return jsonify({

            "success": True,

            "title": title,

            "thumbnail": thumbnail,

            "uploader": uploader,

            "duration": duration,

            "qualities": qualities,

            "default_quality":
                default_quality

        })

    except Exception as e:

        print()
        print("=" * 55)
        print("VIDEO BİLGİSİ HATASI")
        print("=" * 55)
        print(e)
        print()

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# DOWNLOAD
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
        # İNDİR
        # =================================================

        file = download_video(
            link,
            kalite
        )

        if not file or not os.path.exists(file):

            return (
                "Video indirildi fakat dosya bulunamadı.",
                500
            )

        print()
        print("=" * 55)
        print("İNDİRME BAŞARILI")
        print(file)
        print("=" * 55)
        print()

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
        print("=" * 55)
        print("İNDİRME HATASI")
        print("=" * 55)
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
    print("=" * 55)
    print("                 zdDownloader")
    print("=" * 55)
    print()

    print(
        "Python:",
        os.sys.executable
    )

    print(
        "yt-dlp:",
        yt_dlp.version.__version__
    )

    print(
        "FFmpeg:",
        FFMPEG_PATH
        if FFMPEG_PATH
        else "BULUNAMADI"
    )

    print()

    print(
        "http://127.0.0.1:5000"
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
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
