"""
Streamlit UI for the AI Video Dubbing project.

This file ONLY handles presentation. It calls the existing backend
exactly as written:

    pipeline.run_pipeline(video_path, language) -> output_video_path

No backend file is modified. No feature is added that the backend
does not already support (no voice selection, no subtitles download,
no job queue, no history, no auth, no fake progress stages).
"""

from __future__ import annotations

import asyncio
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

try:
    import ffmpeg  # only used here to read file duration/resolution for display
except Exception:  # pragma: no cover
    ffmpeg = None

import config
from pipeline import run_pipeline

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Video Dubbing Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Custom CSS — dark, purple-gradient, glassmorphism theme
# --------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {
    --bg: #0B0F1A;
    --card: rgba(24, 20, 45, 0.55);
    --card-solid: #17142B;
    --border: rgba(168, 139, 250, 0.16);
    --accent: #8B5CF6;
    --accent-2: #C084FC;
    --accent-dim: rgba(139, 92, 246, 0.15);
    --success: #22C55E;
    --error: #F43F5E;
    --text: #F4F2FF;
    --text-muted: #9C96B8;
    --gradient: linear-gradient(90deg, #8B5CF6 0%, #C084FC 100%);
}

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; color: var(--text); }
.stApp {
    background:
        radial-gradient(circle at 15% -10%, rgba(139,92,246,0.18) 0%, transparent 45%),
        radial-gradient(circle at 90% 10%, rgba(192,132,252,0.10) 0%, transparent 40%),
        var(--bg);
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1300px; }

/* ================= HEADER ================= */
.app-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.4rem 0 1.4rem 0; animation: fadeIn 0.5s ease-out;
}
.app-header h1 {
    font-size: 2.1rem; font-weight: 900; margin: 0 0 0.35rem 0;
    background: var(--gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.app-header p { color: var(--text-muted); font-size: 0.95rem; margin: 0; }
.badge-row { display: flex; gap: 0.5rem; }
.pill {
    background: var(--accent-dim); border: 1px solid var(--border); color: var(--accent-2);
    font-size: 0.72rem; font-weight: 700; padding: 0.35rem 0.75rem; border-radius: 999px;
}

/* ================= GLASS CARD ================= */
.card {
    background: var(--card);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.5rem 1.6rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 10px 34px rgba(0,0,0,0.35);
    animation: fadeIn 0.45s ease-out;
}
.card-title {
    font-size: 1rem; font-weight: 800; display: flex; align-items: center; gap: 0.55rem;
    margin-bottom: 1.1rem;
}
.card-title .num {
    background: var(--gradient); color: white; width: 24px; height: 24px; border-radius: 8px;
    display: inline-flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 800;
}

/* ================= UPLOAD ================= */
[data-testid="stFileUploaderDropzone"] {
    background: rgba(139,92,246,0.06) !important;
    border: 1.5px dashed rgba(168,139,250,0.45) !important;
    border-radius: 14px !important;
}
.uploaded-file-card {
    display: flex; align-items: center; justify-content: space-between; gap: 0.6rem;
    background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 12px;
    padding: 0.75rem 1rem; margin-top: 0.75rem;
}
.uploaded-file-card .fname { font-weight: 700; font-size: 0.86rem; }
.uploaded-file-card .fmeta { font-size: 0.74rem; color: var(--text-muted); }
.check-badge {
    width: 24px; height: 24px; border-radius: 50%; background: var(--success);
    display: flex; align-items: center; justify-content: center; color: #06210f; font-size: 0.8rem; flex-shrink: 0;
}

/* ================= INFO ROWS ================= */
.info-row {
    display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;
    padding: 0.55rem 0.1rem; color: var(--text-muted); border-bottom: 1px solid var(--border);
}
.info-row:last-child { border-bottom: none; }
.info-row .val { color: var(--text); font-weight: 700; }

/* ================= VOICE DISPLAY (read-only) ================= */
.voice-box {
    display: flex; align-items: center; gap: 0.7rem; background: rgba(255,255,255,0.03);
    border: 1px solid var(--border); border-radius: 12px; padding: 0.8rem 1rem; margin-top: 0.3rem;
}
.voice-box .icon {
    width: 34px; height: 34px; border-radius: 9px; background: var(--gradient);
    display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0;
}
.voice-box .name { font-weight: 700; font-size: 0.88rem; }
.voice-box .sub { font-size: 0.72rem; color: var(--text-muted); }

/* ================= BUTTONS ================= */
.stButton > button, .stDownloadButton > button {
    background: var(--gradient); color: white; border: none; border-radius: 12px;
    padding: 0.75rem 1.4rem; font-weight: 700; font-size: 0.95rem; width: 100%;
    transition: transform 0.15s ease, box-shadow 0.15s ease; box-shadow: 0 6px 20px rgba(139,92,246,0.28);
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-2px); box-shadow: 0 10px 28px rgba(192,132,252,0.35);
}
.stButton > button:disabled { opacity: 0.4; box-shadow: none; transform: none; }

/* ================= SELECT ================= */
.stSelectbox div[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.03) !important; border-radius: 10px !important; border: 1px solid var(--border) !important;
}

/* ================= PROGRESS ================= */
.stProgress > div > div > div > div { background: var(--gradient); border-radius: 999px; }
.processing-msg {
    font-size: 0.88rem; color: var(--text-muted); margin-bottom: 0.5rem; display: flex;
    align-items: center; gap: 0.5rem;
}
.dot-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: pulse 1.2s infinite; }

/* ================= STATUS CARDS ================= */
.status-success {
    background: linear-gradient(135deg, rgba(34,197,94,0.14), rgba(34,197,94,0.02));
    border: 1px solid rgba(34,197,94,0.35); border-radius: 14px; padding: 1rem 1.2rem;
    display: flex; align-items: center; gap: 0.6rem; font-weight: 700; color: var(--success); margin-bottom: 1rem;
}
.status-error {
    background: linear-gradient(135deg, rgba(244,63,94,0.14), rgba(244,63,94,0.02));
    border: 1px solid rgba(244,63,94,0.35); border-radius: 14px; padding: 1rem 1.2rem;
    color: var(--error); margin-bottom: 0.5rem;
}
.status-error .title { font-weight: 800; margin-bottom: 0.3rem; }
.status-error .detail { font-size: 0.8rem; color: #FCA5A5; font-family: 'SFMono-Regular', Consolas, monospace; }

/* ================= SIDEBAR ================= */
section[data-testid="stSidebar"] { background: #0A0812; border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] > div { padding-top: 1.2rem; }
.sb-logo { display: flex; align-items: center; gap: 0.6rem; padding: 0 0.9rem 1.3rem 0.9rem; }
.sb-logo .box {
    width: 40px; height: 40px; border-radius: 11px; background: var(--gradient);
    display: flex; align-items: center; justify-content: center; font-size: 1.15rem; flex-shrink: 0;
}
.sb-logo .name { font-weight: 800; font-size: 0.95rem; line-height: 1.2; }
.sb-logo .name .sub {
    display: block; font-weight: 700; font-size: 0.95rem;
    background: var(--gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sb-section-label {
    color: var(--text-muted); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em;
    padding: 0 0.9rem; margin: 0.9rem 0 0.5rem 0;
}
.sb-row {
    display: flex; align-items: flex-start; gap: 0.55rem; padding: 0.4rem 0.9rem; font-size: 0.8rem;
}
.sb-row .label { color: var(--text); font-weight: 600; }
.sb-row .value { color: var(--text-muted); font-size: 0.72rem; }

@keyframes fadeIn { from {opacity:0; transform: translateY(8px);} to {opacity:1; transform: translateY(0);} }
@keyframes pulse { 0%{opacity:1;} 50%{opacity:0.35;} 100%{opacity:1;} }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

st.session_state.setdefault("uploaded_video_path", None)
st.session_state.setdefault("uploaded_video_name", None)
st.session_state.setdefault("uploaded_video_size", None)
st.session_state.setdefault("video_meta", None)  # (duration, width, height) via ffprobe, display only
st.session_state.setdefault("result_path", None)
st.session_state.setdefault("result_language", None)
st.session_state.setdefault("result_time", None)
st.session_state.setdefault("error", None)
st.session_state.setdefault("processing", False)

TEMP_UPLOAD_DIR = Path(config.TEMP_DIR) / "uploads"
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def format_seconds(s: float) -> str:
    s = int(round(s))
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {sec}s"
    if m:
        return f"{m}m {sec}s"
    return f"{sec}s"


def probe_video(path: str):
    """Read duration/resolution for display only. Returns None on failure."""
    if ffmpeg is None:
        return None
    try:
        info = ffmpeg.probe(path)
        duration = float(info["format"]["duration"])
        video_stream = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
        width = video_stream.get("width") if video_stream else None
        height = video_stream.get("height") if video_stream else None
        return {"duration": duration, "width": width, "height": height}
    except Exception:
        return None


def run_pipeline_sync(video_path: str, language: str):
    """Run the async run_pipeline() to completion from Streamlit's sync context."""

    def _runner():
        return asyncio.run(run_pipeline(video_path, language))

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_runner)
        return future


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div class="sb-logo">
            <div class="box">🎬</div>
            <div class="name">AI Video<span class="sub">Dubbing Studio</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sb-section-label">SUPPORTED LANGUAGES</div>', unsafe_allow_html=True)
    for lang, meta in config.SUPPORTED_LANGUAGES.items():
        st.markdown(
            f'<div class="sb-row">🌐<div><div class="label">{lang}</div>'
            f'<div class="value">{meta["voice"]}</div></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sb-section-label">LIMITS</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sb-row">⏱<div><div class="label">Max video length</div>'
        f'<div class="value">{format_seconds(config.MAX_VIDEO_DURATION)}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="sb-row">📁<div><div class="label">Allowed formats</div>'
        f'<div class="value">{", ".join(config.ALLOWED_VIDEO_EXTENSIONS)}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="sb-row">🤖<div><div class="label">Whisper model</div>'
        f'<div class="value">{config.WHISPER_MODEL}</div></div></div>',
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------

st.markdown(
    """
    <div class="app-header">
        <div>
            <h1>AI Video Dubbing Studio</h1>
            <p>Upload a video, choose a target language, and get it dubbed automatically.</p>
        </div>
        <div class="badge-row">
            <div class="pill">Whisper</div>
            <div class="pill">Edge TTS</div>
            <div class="pill">FFmpeg</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1.05, 1], gap="large")

# --------------------------------------------------------------------------
# LEFT: Upload + settings
# --------------------------------------------------------------------------

with left_col:
    st.markdown(
        '<div class="card"><div class="card-title"><span class="num">1</span> Upload Video</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Drag and drop a video file",
        type=[ext.lstrip(".") for ext in config.ALLOWED_VIDEO_EXTENSIONS],
        label_visibility="collapsed",
    )

    if uploaded is not None:
        ext = Path(uploaded.name).suffix.lower()
        if ext not in config.ALLOWED_VIDEO_EXTENSIONS:
            st.markdown(
                f'<div class="status-error"><div class="title">Unsupported file type</div>'
                f'<div class="detail">Allowed: {", ".join(config.ALLOWED_VIDEO_EXTENSIONS)}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            save_path = TEMP_UPLOAD_DIR / uploaded.name
            if st.session_state.uploaded_video_name != uploaded.name:
                with open(save_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                st.session_state.uploaded_video_path = str(save_path)
                st.session_state.uploaded_video_name = uploaded.name
                st.session_state.uploaded_video_size = uploaded.size
                st.session_state.video_meta = probe_video(str(save_path))
                st.session_state.result_path = None
                st.session_state.error = None

            meta = st.session_state.video_meta
            duration_ok = True
            if meta and meta["duration"] > config.MAX_VIDEO_DURATION:
                duration_ok = False

            st.markdown(
                f"""
                <div class="uploaded-file-card">
                    <div class="check-badge">{'✓' if duration_ok else '!'}</div>
                    <div style="flex:1;">
                        <div class="fname">{st.session_state.uploaded_video_name}</div>
                        <div class="fmeta">{format_bytes(st.session_state.uploaded_video_size)}
                        {'· ' + format_seconds(meta['duration']) if meta else ''}
                        {'· ' + str(meta['width']) + '×' + str(meta['height']) if meta and meta.get('width') else ''}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if not duration_ok:
                st.markdown(
                    f'<div class="status-error" style="margin-top:0.7rem;"><div class="title">Video too long</div>'
                    f'<div class="detail">Limit is {format_seconds(config.MAX_VIDEO_DURATION)}.</div></div>',
                    unsafe_allow_html=True,
                )

    st.markdown("</div>", unsafe_allow_html=True)  # close upload card

    # ---- Settings card ----
    st.markdown(
        '<div class="card"><div class="card-title"><span class="num">2</span> Dubbing Settings</div>',
        unsafe_allow_html=True,
    )

    lang_choices = list(config.SUPPORTED_LANGUAGES.keys())
    default_index = lang_choices.index(config.DEFAULT_LANGUAGE) if config.DEFAULT_LANGUAGE in lang_choices else 0
    target_language = st.selectbox("Target Language", lang_choices, index=default_index)

    voice_name = config.SUPPORTED_LANGUAGES[target_language]["voice"]
    st.markdown(
        f"""
        <div class="voice-box">
            <div class="icon">🎙</div>
            <div>
                <div class="name">{voice_name}</div>
                <div class="sub">Voice is fixed per language by the backend</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:0.9rem"></div>', unsafe_allow_html=True)

    can_start = (
        st.session_state.uploaded_video_path is not None
        and (st.session_state.video_meta is None or st.session_state.video_meta["duration"] <= config.MAX_VIDEO_DURATION)
        and not st.session_state.processing
    )
    start_clicked = st.button("🚀 Start Dubbing", disabled=not can_start)

    st.markdown("</div>", unsafe_allow_html=True)  # close settings card

# --------------------------------------------------------------------------
# RIGHT: Preview
# --------------------------------------------------------------------------

with right_col:
    st.markdown('<div class="card"><div class="card-title">🖼 Preview</div>', unsafe_allow_html=True)
    if st.session_state.uploaded_video_path:
        st.video(st.session_state.uploaded_video_path)
    else:
        st.markdown(
            '<p style="color:var(--text-muted);font-size:0.85rem;">Upload a video to preview it here.</p>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    result_area = st.empty()

# --------------------------------------------------------------------------
# Processing
# --------------------------------------------------------------------------

if start_clicked and st.session_state.uploaded_video_path:
    st.session_state.processing = True
    st.session_state.result_path = None
    st.session_state.error = None

    progress_card = st.empty()
    with progress_card.container():
        st.markdown(
            '<div class="card"><div class="card-title">📟 Processing</div>'
            '<div class="processing-msg"><span class="dot-pulse"></span> '
            'Dubbing your video — this can take a few minutes depending on length...</div>',
            unsafe_allow_html=True,
        )
        bar = st.progress(0)
        st.markdown("</div>", unsafe_allow_html=True)

    start_time = time.time()
    future = run_pipeline_sync(st.session_state.uploaded_video_path, target_language)

    # Animate the bar while we wait — this reflects elapsed wait time only,
    # not real backend stage progress, since run_pipeline() reports none.
    pct = 0
    while not future.done():
        pct = min(pct + 2, 92)
        bar.progress(pct)
        time.sleep(0.3)

    progress_card.empty()
    elapsed = time.time() - start_time

    try:
        output_path = future.result()
        st.session_state.result_path = output_path
        st.session_state.result_language = target_language
        st.session_state.result_time = elapsed
    except Exception as e:
        st.session_state.error = f"{e}\n\n{traceback.format_exc(limit=2)}"

    st.session_state.processing = False

# --------------------------------------------------------------------------
# Result / error
# --------------------------------------------------------------------------

with result_area.container():
    if st.session_state.error:
        st.markdown(
            f"""
            <div class="card">
                <div class="status-error">
                    <div class="title">❌ Dubbing failed</div>
                    <div class="detail">{st.session_state.error}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif st.session_state.result_path and Path(st.session_state.result_path).exists():
        st.markdown(
            '<div class="status-success">🎉 Dubbing completed successfully!</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="card"><div class="card-title">✅ Result</div>', unsafe_allow_html=True)
        st.video(st.session_state.result_path)

        rows = [
            ("Target Language", st.session_state.result_language),
            ("Voice Used", config.SUPPORTED_LANGUAGES[st.session_state.result_language]["voice"]),
            ("Processing Time", format_seconds(st.session_state.result_time)),
        ]
        rows_html = "".join(
            f'<div class="info-row"><span>{label}</span><span class="val">{value}</span></div>'
            for label, value in rows
        )
        st.markdown(f'<div style="margin:0.9rem 0;">{rows_html}</div>', unsafe_allow_html=True)

        with open(st.session_state.result_path, "rb") as f:
            st.download_button(
                "⬇️ Download Dubbed Video",
                data=f.read(),
                file_name=Path(st.session_state.result_path).name,
                mime="video/mp4",
            )
        st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------

st.markdown(
    """
    <div style="text-align:center; color:#5B5470; padding: 1.5rem 0 0.5rem 0; font-size:0.78rem;">
        Built with Python · Streamlit · Faster Whisper · Edge TTS · FFmpeg
    </div>
    """,
    unsafe_allow_html=True,
)