import os
import ffmpeg

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def merge_audio_video(video_path, audio_stream):

    if not os.path.isfile(video_path):
        raise RuntimeError("Video not found.")

    video_name = os.path.splitext(os.path.basename(video_path))[0]

    output_path = os.path.join(
        OUTPUT_DIR,
        f"{video_name}_dubbed.mp4"
    )

    video = ffmpeg.input(video_path)

    probe = ffmpeg.probe(video_path)
    duration = float(probe["format"]["duration"])

    # Create silent audio
    audio = ffmpeg.input(
        f"anullsrc=r=44100:cl=stereo",
        f="lavfi",
        t=duration,
    )

    current_audio = audio.audio

    for segment in audio_stream:

        audio_path = segment.get("audio_path")

        if not audio_path or not os.path.isfile(audio_path):
            continue

        delay = int(segment["start"] * 1000)

        clip = (
            ffmpeg
            .input(audio_path)
            .audio
            .filter("adelay", f"{delay}|{delay}")
        )

        current_audio = ffmpeg.filter(
            [current_audio, clip],
            "amix",
            inputs=2,
            duration="longest",
        )

    (
        ffmpeg
        .output(
            video.video,
            current_audio,
            output_path,
            vcodec="copy",
            acodec="aac",
        )
        .overwrite_output()
        .run()
    )

    return output_path