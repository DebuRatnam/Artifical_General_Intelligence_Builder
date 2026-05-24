"""
main_gui.py
Streamlit dashboard for the embodi-align grounded perceptual agent.

Panels:
  1. Egocentric camera feed + tactile / audio line charts.
  2. Dynamic tactile banner (color from label hash, no hard-coded states).
  3. 2D world map (VLM-extracted objects, audio peaks bound by the VLM).
  4. Memory inspector (every learned ObjectCard with its modalities).
  5. Chat panel — ask the agent questions; replies are grounded in the
     current Scene + ObjectMemory via an Ollama chat model.

Launch:
    streamlit run main_gui.py
"""

import hashlib
import time
from collections import deque

import cv2
import numpy as np
import ollama
import streamlit as st

from world_model import WorldModel
from world_map import render_scene


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Embodi-Align — Grounded World Model",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.title("Embodi-Align")
st.sidebar.markdown("**Grounded Perceptual Agent** — audio + vision + tactile memory")
use_mock = st.sidebar.checkbox("Mock mode (no hardware)", value=True)
serial_port = st.sidebar.text_input("Serial port", value="/dev/ttyUSB0")
baud_rate = st.sidebar.number_input("Baud rate", value=460800, step=1)
window_size = st.sidebar.slider("Plot window (samples)", 50, 500, 200)
auto_observe = st.sidebar.checkbox("Auto-observe every N sec", value=False)
auto_period = st.sidebar.slider("Auto period (s)", 2, 30, 6)
vlm_model = st.sidebar.text_input("VLM model (Ollama)", value="moondream")
chat_model = st.sidebar.text_input("Chat model (Ollama)", value="qwen2.5:3b")
memory_path = st.sidebar.text_input("Memory DB path", value="object_memory.db")


# Stable color from a label string. Used by the dynamic tactile banner
# so each learned object gets its own consistent banner color without
# any hard-coded color table.
def label_color(label: str) -> str:
    if not label:
        return "#7f8c8d"
    h = hashlib.md5(label.encode()).hexdigest()
    return f"#{h[:6]}"


# ── One-time session bootstrap ────────────────────────────────────────────────
if 'started' not in st.session_state:
    from data_harvester import token_queue, start, start_mock
    import agent_simulator as agent

    st.session_state.world_model = WorldModel(
        model_name=vlm_model,
        memory_path=memory_path,
    )
    st.session_state.chat_history = []
    st.session_state.agent_thought = "Awaiting first sensory observation…"
    st.session_state.last_auto_obs = 0.0

    if use_mock:
        start_mock(hz=100)
    else:
        start(port=serial_port, baud=baud_rate)
    # Pass memory + world_model into the agent loop so contact events
    # can bootstrap tactile signatures into long-term memory.
    agent.start(token_queue,
                memory=st.session_state.world_model.memory,
                world_model=st.session_state.world_model)
    st.session_state.started = True

import agent_simulator as agent
from data_harvester import token_queue

# ── Rolling buffers ───────────────────────────────────────────────────────────
if 'accel_buf' not in st.session_state:
    st.session_state.accel_buf = deque(maxlen=window_size)
    st.session_state.fft_buf   = deque(maxlen=window_size)
    st.session_state.ts_buf    = deque(maxlen=window_size)

accel_buf = st.session_state.accel_buf
fft_buf   = st.session_state.fft_buf
ts_buf    = st.session_state.ts_buf

# Drain queue
drained = 0
while not token_queue.empty() and drained < 50:
    t = token_queue.get_nowait()
    ts_buf.append(t[0]); accel_buf.append(t[1]); fft_buf.append(t[2])
    drained += 1

# ── Dynamic tactile banner ────────────────────────────────────────────────────
label = agent.current_label
directive = agent.current_directive
color = label_color(label or "")

banner_label = label if label else "Awaiting tactile signal"
st.markdown(f"""
<div style="background:{color};padding:12px 20px;border-radius:8px;margin-bottom:12px;">
  <h2 style="margin:0;color:white;">⬤ Tactile: {banner_label}</h2>
  <p style="margin:4px 0 0 0;color:white;font-family:monospace;">{directive}</p>
</div>
""", unsafe_allow_html=True)

# ── Row 1: Camera + tactile plots ─────────────────────────────────────────────
col_cam, col_plots = st.columns([1, 1])

with col_cam:
    st.subheader("Egocentric Camera")
    cam_placeholder = st.empty()

    # Cache camera in session_state to avoid open/close flicker on every rerun
    if 'cap' not in st.session_state:
        st.session_state.cap = cv2.VideoCapture(0)
    cap = st.session_state.cap

    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            st.session_state.latest_raw_frame = frame.copy()
            cam_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_column_width=True)
        else:
            cam_placeholder.info("Camera opened but frame read failed.")
    else:
        blank = np.full((480, 640, 3), 50, dtype=np.uint8)
        cv2.putText(blank, "Camera unavailable", (160, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)
        cam_placeholder.image(blank, use_column_width=True)

with col_plots:
    st.subheader("Acceleration (g)")
    if accel_buf:
        st.line_chart(list(accel_buf))
    else:
        st.info("Waiting for sensor data…")
    st.subheader("FFT Peak Frequency (Hz)")
    if fft_buf:
        st.line_chart(list(fft_buf))
    else:
        st.info("Waiting for sensor data…")

# ── Row 2: Grounded 2D World Map ──────────────────────────────────────────────
st.markdown("---")
st.header("🧠 Grounded 2D World Map")
st.caption(
    "Fast path: CLIP fingerprints the frame and reuses cached labels from "
    "ObjectMemory. Slow path: VLM extracts objects + hand pose, then the "
    "FFT peak is bound to a visible emitter (also via the VLM, no hard-coded "
    "frequency table)."
)

current_accel = accel_buf[-1] if accel_buf else 0.0
current_fft   = fft_buf[-1]   if fft_buf   else 0

# Auto-observe trigger
should_observe = False
force_vlm = False
if auto_observe and (time.time() - st.session_state.last_auto_obs) > auto_period:
    should_observe = True
    st.session_state.last_auto_obs = time.time()

col_ctrl, col_map = st.columns([1, 3])
with col_ctrl:
    if st.button("⚡ Observe scene (force VLM)", type="primary"):
        should_observe = True
        force_vlm = True
    if st.button("⚡ Quick observe (fast path)"):
        should_observe = True
    if st.button("🧹 Reset world model (keep memory)"):
        st.session_state.world_model.reset()
        st.session_state.agent_thought = "World model reset (memory retained)."
    st.metric("Objects in scene", len(st.session_state.world_model.scene.objects))
    st.metric("Audio sources",    len(st.session_state.world_model.scene.audio_sources))
    st.metric("Last FFT peak",    f"{current_fft} Hz")
    st.metric("Path",             "FAST (CLIP)" if st.session_state.world_model.scene.last_used_fast_path else "SLOW (VLM)")

if should_observe:
    spinner_msg = "Querying VLM and updating world model…" if force_vlm else "Updating world model…"
    with st.spinner(spinner_msg):
        frame = st.session_state.get('latest_raw_frame')
        scene = st.session_state.world_model.observe(
            frame=frame,
            accel_g=current_accel,
            fft_hz=current_fft,
            force_vlm=force_vlm,
        )
        st.session_state.agent_thought = scene.last_summary or "(VLM returned empty)"

with col_map:
    fig = render_scene(st.session_state.world_model.scene)
    st.plotly_chart(fig, use_container_width=True)

# ── Row 3: Raw agent interpretation ───────────────────────────────────────────
st.subheader("Agent's Raw Perceptual Output")
st.code(st.session_state.agent_thought, language="text")

# ── Row 4: Memory inspector ───────────────────────────────────────────────────
st.markdown("---")
st.header("🧠 Persistent Memory (ObjectMemory)")
st.caption(
    "Everything the agent has ever seen, touched, or heard. Tactile and "
    "audio columns fill in as the agent encounters and grounds each object."
)

cards = st.session_state.world_model.memory.all()
if cards:
    import pandas as pd
    rows = []
    for c in cards:
        rows.append({
            "label": c.label,
            "n_visual": c.n_visual,
            "n_tactile": c.n_tactile,
            "n_audio": c.n_audio,
            "accel_mean (g)": round(c.tactile_accel_mean, 3),
            "fft_mean (Hz)":  int(c.tactile_fft_mean),
            "audio (Hz)":     c.audio_freq_hz,
            "tactile_trained": c.tactile_trained,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("Memory is empty. Click '⚡ Observe scene' to start populating it.")

# ── Row 5: Chat panel ─────────────────────────────────────────────────────────
st.markdown("---")
st.header("💬 Talk to the agent")
st.caption(
    "Replies are grounded in the current Scene and the persistent memory DB. "
    "Uses an Ollama chat model — change it in the sidebar."
)


# Build the system prompt for the chat LLM from current Scene + memory.
# This is the RAG context that grounds the agent's free-form responses
# in what it has actually perceived rather than letting it hallucinate.
def build_chat_context(world_model, accel: float, fft: int) -> str:
    scene = world_model.scene
    visible = list(scene.objects.keys()) or ["(nothing identified yet)"]
    sounds = [(s.label, s.freq_hz) for s in scene.audio_sources.values()] or [("(none)", 0)]
    mem_lines = []
    for c in world_model.memory.all()[:25]:
        mem_lines.append(
            f"  • {c.label}: seen×{c.n_visual}, touched×{c.n_tactile} "
            f"(accel≈{c.tactile_accel_mean:.2f}g, fft≈{int(c.tactile_fft_mean)}Hz), "
            f"audio≈{c.audio_freq_hz}Hz"
        )
    mem_block = "\n".join(mem_lines) if mem_lines else "  (empty)"
    return (
        "You are an embodied perceptual agent. You have a camera, a glove-mounted "
        "IMU, and a microphone (FFT peak). Ground every answer in the data below; "
        "do not invent objects or sensor readings.\n\n"
        f"Currently visible objects: {visible}\n"
        f"Audio sources (label, freq Hz): {sounds}\n"
        f"Latest tactile sample: accel={accel:.3f}g, fft_peak={fft}Hz\n"
        f"Most recent tactile classification: {scene.last_tactile_label or '(none)'}\n\n"
        "Long-term memory (every object the agent has grounded):\n"
        f"{mem_block}\n"
    )


# Render history first so the input box stays at the bottom.
for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).write(msg["content"])

prompt = st.chat_input("Ask about the scene, request a summary, or query the memory…")
if prompt:
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    ctx = build_chat_context(st.session_state.world_model, current_accel, current_fft)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking…"):
                resp = ollama.chat(
                    model=chat_model,
                    messages=[
                        {"role": "system", "content": ctx},
                        *st.session_state.chat_history,
                    ],
                )
                reply = resp["message"]["content"]
        except Exception as e:
            reply = f"(chat model error: {e} — is `ollama pull {chat_model}` done?)"
        st.write(reply)
    st.session_state.chat_history.append({"role": "assistant", "content": reply})

# ── Metrics row ───────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Last Accel",       f"{accel_buf[-1]:.3f} g" if accel_buf else "—")
m2.metric("Last FFT Peak",    f"{fft_buf[-1]} Hz"      if fft_buf   else "—")
m3.metric("Tokens received",  len(ts_buf))
m4.metric("Memory size",      len(st.session_state.world_model.memory.all()))

# ── Auto-refresh ──────────────────────────────────────────────────────────────
time.sleep(0.2)
st.rerun()
