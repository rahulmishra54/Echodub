import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

FFMPEG_PATH = "ffmpeg"

WHISPER_MODEL = "base"


MAX_VIDEO_DURATION = 10 * 60


SUPPORTED_LANGUAGES = {
    "English": {
        "code": "en",
        "voice": "en-US-GuyNeural"
    },
    "Hindi": {
        "code": "hi",
        "voice": "hi-IN-MadhurNeural"
    },
    "Spanish": {
        "code": "es",
        "voice": "es-ES-AlvaroNeural"
    }
}


DEFAULT_LANGUAGE = "English"


ALLOWED_VIDEO_EXTENSIONS = (
    ".mp4",
    ".mov",
    ".avi",
    ".mkv"
)