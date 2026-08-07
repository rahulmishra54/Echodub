from faster_whisper import WhisperModel

model = WhisperModel("base")


def transcribe_audio(audio_path):
    try:
        segments, info = model.transcribe(audio_path)

        for segment in segments:
            yield {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "language": info.language
            }

    except FileNotFoundError:
        raise Exception("Audio file not found.")

    except Exception as e:
        raise Exception(f"Transcription failed: {e}")