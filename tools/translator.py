from deep_translator import GoogleTranslator


def translate_text(segments, target_language):
    try:
        translator = GoogleTranslator(
            source="auto",
            target=target_language
        )

        for segment in segments:
            translated_text = translator.translate(segment["text"])

            yield {
                "start": segment["start"],
                "end": segment["end"],
                "text": translated_text
            }

    except Exception as e:
        raise Exception(f"Translation failed: {e}")