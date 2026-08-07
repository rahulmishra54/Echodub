import os
import edge_tts


async def generate_speech(segments, voice, output_folder):
    try:
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(output_folder, "dubbed_audio.mp3")

        # Join all translated text into one string
        full_text = " ".join(segment["text"] for segment in segments)

        communicate = edge_tts.Communicate(
            full_text,
            voice
        )

        await communicate.save(output_file)

        return output_file

    except Exception as e:
        raise Exception(f"TTS failed: {e}")