import os
import ffmpeg

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def merge_audio_video(video_path, audio_path):
    try:
        video_name = os.path.splitext(os.path.basename(video_path))[0]

        output_path = os.path.join(
            OUTPUT_DIR,
            f"{video_name}_dubbed.mp4"
        )

        video = ffmpeg.input(video_path)
        audio = ffmpeg.input(audio_path)

        (
            ffmpeg
            .output(
                video.video,
                audio.audio,
                output_path,
                vcodec="copy",
                acodec="aac"
            )
            .overwrite_output()
            .run()
        )

        return output_path

    except Exception as e:
        raise Exception(f"Merge failed: {e}")