"""
Optional helper: download a YouTube video locally with yt-dlp.

This is NOT part of the main dubbing workflow. The application always
processes a local video file — this module simply gives the user a
convenient way to obtain one from a YouTube URL before running the
pipeline.
"""

from __future__ import annotations

from pathlib import Path

import config
from tools.utils import get_logger, new_job_id

log = get_logger(__name__)


def download_youtube_video(url: str, output_dir: str | Path | None = None) -> Path:
    """
    Download a YouTube video as an mp4 using yt-dlp and return the local
    file path.

    Raises:
        RuntimeError: if yt-dlp is not installed or the download fails.
    """
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is not installed. Run `pip install yt-dlp` to use this helper."
        ) from exc

    output_dir = Path(output_dir or config.TEMP_DIR / new_job_id())
    output_dir.mkdir(parents=True, exist_ok=True)

    outtmpl = str(output_dir / "%(title).80s.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    log.info("Downloading YouTube video: %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        # merge_output_format guarantees mp4 container
        filepath = str(Path(filepath).with_suffix(".mp4"))

    result_path = Path(filepath)
    if not result_path.exists():
        raise RuntimeError("yt-dlp reported success but output file was not found.")

    log.info("Downloaded to %s", result_path)
    return result_path
