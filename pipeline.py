import ffmpeg
import config

from tools.transcriber import transcribe_audio
from tools.translator import translate_text
from tools.tts import generate_speech
from tools.merger import merge_audio_video


async def run_pipeline(video_path, language):


    probe = ffmpeg.probe(video_path)
    duration = float(probe["format"]["duration"])

    if duration > config.MAX_VIDEO_DURATION:
        raise Exception("Video must be less than 10 minutes.")

    
    segments = transcribe_audio(video_path)

    
    translated = translate_text(
        segments,
        config.SUPPORTED_LANGUAGES[language]["code"]
    )

    
    audio_path = await generate_speech(
        translated,
        config.SUPPORTED_LANGUAGES[language]["voice"],
        "temp/audio"
    )

    
    output = merge_audio_video(
        video_path,
        audio_path
    )

    return output