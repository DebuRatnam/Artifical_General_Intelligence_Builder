"""
main_gui.py
Streamlit dashboard: egocentric camera feed, live tactile line charts,
and colored agent state overlay.

Launch:
    streamlit run host_app/main_gui.py

Flags (set in sidebar):
    --mock    Use synthetic data (no hardware required)
    --port    Serial port (default /dev/ttyUSB0)
"""

import threading
import time
from collections import deque

import cv2
import numpy as np
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Embodi-Align",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.title("Embodi-Align")
st.sidebar.markdown("Cross-Embodiment Data Harvester")
use_mock = st.sidebar.checkbox("Mock mode (no hardware)", value=True)
serial_port = st.sidebar.text_input("Serial port", value="/dev/ttyUSB0")
baud_rate = st.sidebar.number_input("Baud rate", value=460800, step=1)
window_size = st.sidebar.slider("Plot window (samples)", 50, 500, 200)

# ── Start harvester + agent (once per session via st.session_state) ───────────
if 'started' not in st.session_state:
    from data_harvester import token_queue, start, start_mock
    import agent_simulator as agent

    if use_mock:
        start_mock(hz=100)
    else:
        start(port=serial_port, baud=baud_rate)

    agent.start(token_queue)
    st.session_state.started = True

import agent_simulator as agent
from data_harvester import token_queue

# ── Rolling buffers ───────────────────────────────────────────────────────────
if 'accel_buf' not in st.session_state:
    st.session_state.accel_buf   = deque(maxlen=window_size)
    st.session_state.fft_buf     = deque(maxlen=window_size)
    st.session_state.ts_buf      = deque(maxlen=window_size)

accel_buf = st.session_state.accel_buf
fft_buf   = st.session_state.fft_buf
ts_buf    = st.session_state.ts_buf

# ── Drain queue into buffers ──────────────────────────────────────────────────
drained = 0
while not token_queue.empty() and drained < 50:
    token = token_queue.get_nowait()
    ts_buf.append(token[0])
    accel_buf.append(token[1])
    fft_buf.append(token[2])
    drained += 1

# ── State colour map ──────────────────────────────────────────────────────────
STATE_COLORS = {
    "Smooth Plastic":  "#2ecc71",   # green
    "Rough Sandpaper": "#f39c12",   # amber
    "Stuck Sticker":   "#e74c3c",   # red
    "Unknown":         "#95a5a6",   # grey
}
state     = agent.current_state
directive = agent.current_directive
color     = STATE_COLORS.get(state, "#95a5a6")

# ── Layout ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:{color};padding:12px 20px;border-radius:8px;margin-bottom:12px;">
  <h2 style="margin:0;color:white;">⬤ {state}</h2>
  <p style="margin:4px 0 0 0;color:white;font-family:monospace;">{directive}</p>
</div>
""", unsafe_allow_html=True)

col_cam, col_plots = st.columns([1, 1])

# ── Camera feed ───────────────────────────────────────────────────────────────
with col_cam:
    st.subheader("Egocentric Camera")
    cam_placeholder = st.empty()

    # Try to grab a real camera frame; fall back to a blank placeholder
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cam_placeholder.image(frame_rgb, use_column_width=True)
        else:
            cam_placeholder.info("Camera opened but frame read failed.")
    else:
        # Show a blank grey placeholder with label
        blank = np.full((480, 640, 3), 50, dtype=np.uint8)
        cv2.putText(blank, "Camera unavailable", (160, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 200), 2)
        cam_placeholder.image(blank, use_column_width=True)

# ── Tactile plots ─────────────────────────────────────────────────────────────
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

# ── Metrics row ───────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
m1.metric("Last Accel",    f"{accel_buf[-1]:.3f} g"  if accel_buf else "—")
m2.metric("Last FFT Peak", f"{fft_buf[-1]} Hz"       if fft_buf   else "—")
m3.metric("Tokens received", len(ts_buf))

# ── Auto-refresh every 100 ms ─────────────────────────────────────────────────
time.sleep(0.1)
st.rerun()
