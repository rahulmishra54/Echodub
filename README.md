# 🤖 AI Video Dubbing Studio

Translate and dub videos into multiple languages while preserving natural
timing — built with Faster-Whisper, Google Translate, and Edge-TTS, wrapped
in a Streamlit UI styled like a modern AI product.

This is a portfolio/demo project showcasing an end-to-end speech AI
pipeline: transcription → translation → speech synthesis → timestamp-accurate
re-assembly → video muxing.

---

## Features

- 🎥 **Local video upload** — mp4, mov, avi, mkv
- 📝 **Automatic transcription** with word/segment-level timestamps via
  [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)
- 🌍 **Segment-level translation** via `deep-translator` (Google Translate)
- 🎙 **Natural AI voices** per target language via
  [edge-tts](https://github.com/rany2/edge-tts)
- ⏱ **Timestamp-preserving synchronization** — translated speech is placed
  at the *original* Whisper timestamps, with silence padding for short
  segments and mild time-compression (via FFmpeg `atempo`) for long ones
- 📄 **Optional subtitle generation** (SRT, with burn-in support)
- 🧪 **Translate-only mode** for a fast, TTS-free preview of the translation
- ⬇️ **YouTube helper** — optional, standalone utility to pull a local copy
  of a YouTube video via `yt-dlp` before running the main pipeline
- 🖥 **Polished dark-themed Streamlit UI** — custom CSS, live progress
  streaming, animated status timeline, and a SaaS-style result screen

## Demo limitation

Because this is deployed as a public demo, videos longer than **8 minutes**
are rejected with a clear error before any processing starts. This limit is
fully configurable (and easy to disable) in `config.py` — see
[Configuration](#configuration).

---

## Processing pipeline

```
Local video file
      │
      ▼
1. Validate duration (demo limit)
      │
      ▼
2. Extract audio (FFmpeg)
      │
      ▼
3. Transcribe with timestamps (Faster-Whisper)
      │
      ▼
4. Translate each segment independently (deep-translator)
      │
      ▼
5. Generate speech per segment (edge-tts)
      │
      ▼
6. Time-stretch each clip to fit its original slot (FFmpeg atempo, capped)
      │
      ▼
7. Assemble a single dubbed track at original timestamps (pydub overlay)
      │
      ▼
8. Replace / mix original audio into the video (FFmpeg)
      │
      ▼
9. (Optional) Burn in translated subtitles
      │
      ▼
Final dubbed video → output/
```

### Synchronization strategy

Naively concatenating translated speech clips drifts out of sync almost
immediately, because translations are rarely the same length as the
original. Instead:

- Every segment keeps its **original Whisper start/end timestamps**.
- The final track starts as silence the length of the whole video; each
  generated clip is **overlaid at its original start time**.
- If a translated clip would run *longer* than its original slot, it's
  sped up (never slowed down) via FFmpeg's `atempo` filter — capped at
  `MAX_SPEECH_SPEEDUP` (default `1.35x`) so speech doesn't get distorted.
- If it finishes early, the silence already in the base track naturally
  pads the gap.

This keeps lip-sync as close as reasonably possible without resorting to
per-frame video retiming, which is out of scope for this project.

---

## Folder structure

```
video-dubbing-ai/
│
├── tools/
│   ├── downloader.py     # optional YouTube download helper (yt-dlp)
│   ├── transcriber.py    # audio extraction + Faster-Whisper transcription
│   ├── translator.py     # segment-level translation
│   ├── tts.py             # edge-tts speech generation + time-fitting
│   ├── merger.py          # timestamp-accurate audio assembly + video mux
│   ├── subtitle.py        # SRT generation
│   └── utils.py            # logging, ffprobe metadata, job/temp helpers
│
├── temp/                  # per-job scratch space (cleaned up automatically)
├── output/                # final dubbed videos land here
│
├── app.py                 # Streamlit UI
├── pipeline.py             # orchestrates the full workflow, streams progress
├── config.py                # all configurable values in one place
├── requirements.txt
├── test.py                  # offline sanity tests (no model downloads)
└── README.md
```

---

## Installation

**Prerequisites:** Python 3.10+, FFmpeg installed and on your `PATH`.

```bash
git clone <this-repo>
cd video-dubbing-ai

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Verify FFmpeg is available:

```bash
ffmpeg -version
```

## Usage

```bash
streamlit run app.py
```

Then, in the browser tab that opens:

1. Upload a local video (mp4 / mov / avi / mkv).
2. Choose a target language and voice.
3. (Optional) Open **Advanced Settings** to pick a Whisper model size,
   adjust speech rate, preserve background audio, enable subtitles, or
   run in translate-only mode.
4. Click **🚀 Start Dubbing** and watch live progress and logs.
5. Preview and download the finished video once processing completes.

### Optional: pull a video from YouTube first

```python
from tools.downloader import download_youtube_video

local_path = download_youtube_video("https://youtube.com/watch?v=...")
# then upload `local_path` through the Streamlit UI, or feed it into
# pipeline.run_pipeline() directly
```

This is a convenience helper only — the pipeline always operates on a
local file, whether it came from your computer or was fetched this way.

### Running the sanity tests

```bash
python test.py
```

These tests check configuration, validation, formatting, and subtitle
generation without downloading any models or calling external services,
so they run in a couple of seconds.

---

## Configuration

All tunables live in `config.py`:

| Setting | Purpose |
|---|---|
| `WHISPER_MODEL` | Whisper model size (`tiny` → `large-v3`) |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | CPU/GPU + quantization |
| `DEMO_MODE` / `MAX_DEMO_DURATION_SECONDS` | Demo length cap — set `DEMO_MODE = False` (or export `DEMO_MODE=false`) to remove it for local use |
| `SUPPORTED_LANGUAGES` | Target languages and their Edge-TTS voice options |
| `MAX_SPEECH_SPEEDUP` | Ceiling on how much a translated clip can be sped up to fit its slot |
| `FFMPEG_PATH` / `FFPROBE_PATH` | Override if FFmpeg isn't on your default `PATH` |

Every value can also be overridden via environment variable (see
`config.py` for the exact names).

---

## Architecture notes

- **`pipeline.py`** is a generator (`run_pipeline`) that yields structured
  progress updates (`{"stage", "message", "percent", "status", "result"}`)
  at each stage. `app.py` consumes this generator directly to drive the
  progress bar, status timeline, and live log — there's no polling or
  background threading involved.
- **`tools/`** modules are independent and import only `config` + stdlib
  (plus their one relevant third-party library), so each one is easy to
  unit test or reuse outside the Streamlit app.
- Whisper models are loaded lazily and cached per model size, so switching
  sizes between runs in the same session doesn't require a restart.
- Every job gets a unique ID and its own temp subfolder, which is deleted
  automatically once the job finishes (success or failure).

## Screenshots

_Add screenshots of the running app here:_

- `docs/screenshot-upload.png` — upload + settings screen
- `docs/screenshot-processing.png` — live processing view
- `docs/screenshot-result.png` — final result screen

## Future improvements

- Word-level (rather than segment-level) timestamp alignment for tighter
  lip-sync on longer segments
- Speaker diarization for multi-speaker dubbing with per-speaker voices
- A queue/worker setup to support longer videos and concurrent jobs
- Caching translated/synthesized segments to allow re-runs with different
  voices without re-transcribing
- Support for additional TTS backends (e.g. ElevenLabs) as pluggable voice
  providers

---

## Disclaimer

This is a portfolio/demo project, not a production platform. Translation
quality depends on Google Translate, and timing accuracy depends on how
close a translation's natural spoken length is to the original — some
drift is expected on long or dense segments.
