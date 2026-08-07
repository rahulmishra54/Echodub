"""
Lightweight sanity tests for the dubbing pipeline's building blocks.

These deliberately avoid downloading Whisper models or calling
external services (Edge-TTS, Google Translate) so they can run quickly
and offline. They check configuration, validation logic, subtitle
formatting, and timestamp-based audio assembly — the parts that are
easy to get subtly wrong.

Run with:  python test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import config
from pipeline import PipelineError, validate_video_duration
from tools.subtitle import _srt_timestamp, generate_srt
from tools.transcriber import TranscriptSegment
from tools.utils import format_seconds, validate_extension

PASSED = 0
FAILED = 0


def check(description: str, condition: bool) -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✔ {description}")
    else:
        FAILED += 1
        print(f"  ✘ {description}")


def test_config_sanity():
    print("config sanity")
    check("supported languages is non-empty", len(config.SUPPORTED_LANGUAGES) > 0)
    check("every language has at least one voice", all(
        len(v["voices"]) > 0 for v in config.SUPPORTED_LANGUAGES.values()
    ))
    check("demo duration limit is positive", config.MAX_DEMO_DURATION_SECONDS > 0)


def test_extension_validation():
    print("extension validation")
    check("accepts .mp4", validate_extension("clip.mp4"))
    check("accepts .MOV (case-insensitive)", validate_extension("clip.MOV"))
    check("rejects .txt", not validate_extension("notes.txt"))


def test_duration_validation():
    print("duration validation")
    original_demo_mode = config.DEMO_MODE
    original_limit = config.MAX_DEMO_DURATION_SECONDS
    try:
        config.DEMO_MODE = True
        config.MAX_DEMO_DURATION_SECONDS = 480  # 8 minutes

        raised = False
        try:
            validate_video_duration(600)
        except PipelineError:
            raised = True
        check("raises PipelineError for videos over the demo limit", raised)

        raised = False
        try:
            validate_video_duration(120)
        except PipelineError:
            raised = True
        check("does not raise for videos under the demo limit", not raised)

        config.DEMO_MODE = False
        raised = False
        try:
            validate_video_duration(9999)
        except PipelineError:
            raised = True
        check("limit is bypassed when DEMO_MODE is False", not raised)
    finally:
        config.DEMO_MODE = original_demo_mode
        config.MAX_DEMO_DURATION_SECONDS = original_limit


def test_format_seconds():
    print("time formatting")
    check("formats under a minute", format_seconds(45) == "0:45")
    check("formats minutes:seconds", format_seconds(125) == "2:05")
    check("formats hours:minutes:seconds", format_seconds(3725) == "1:02:05")


def test_srt_generation(tmp_path: Path):
    print("subtitle generation")
    check("timestamp formatting has correct shape", _srt_timestamp(65.5) == "00:01:05,500")

    segments = [
        TranscriptSegment(index=0, start=0.0, end=2.5, text="Hello there"),
        TranscriptSegment(index=1, start=2.5, end=5.0, text="General Kenobi"),
    ]
    srt_path = generate_srt(segments, tmp_path / "test.srt")
    content = srt_path.read_text(encoding="utf-8")
    check("srt file was created", srt_path.exists())
    check("srt contains both cues", "Hello there" in content and "General Kenobi" in content)
    check("srt uses sequential cue numbers", content.strip().startswith("1"))


def main():
    tmp_path = config.TEMP_DIR / "test_run"
    tmp_path.mkdir(parents=True, exist_ok=True)

    test_config_sanity()
    test_extension_validation()
    test_duration_validation()
    test_format_seconds()
    test_srt_generation(tmp_path)

    print(f"\n{PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
