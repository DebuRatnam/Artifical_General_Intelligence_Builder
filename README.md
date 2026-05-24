# Embodi-Align: Grounded Perceptual Agent

**Cross-embodiment grounded world model.** Audio + vision + tactile perception system that builds a persistent 2D map of the environment. Inspired by Yann LeCun's argument that real intelligence requires persistent world representation, not just next-token prediction.

---

## What It Does

The agent:
1. **Observes scenes** via camera (CLIP fast-path + llava VLM)
2. **Binds audio frequencies** to visible sound sources (fan ≈ 120 Hz, water ≈ 200 Hz, etc.)
3. **Learns tactile signatures** from experience (accel + FFT mean/std per object)
4. **Maintains persistent memory** across sessions (SQLite ObjectMemory)
5. **Renders a live 2D map** with emoji markers + audio annotations
6. **Answers questions** grounded in current scene + learned memory (Ollama chat model)

No hard-coded material states. No fixed frequency tables. Everything learned from data.

---

## Quick Start (No Hardware Required)

### Prerequisites

- **Python 3.8+** (tested with 3.14)
- **Ollama** (https://ollama.ai) — for local VLM inference
- **Camera** (built-in or USB webcam)

### 1. Clone & Install

```bash
git clone <repo>
cd files
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

**Common issue:** If `pip: command not found`, you're in the wrong Python. Verify:
```bash
which python3          # should be path to system Python
python3 --version     # should be 3.8+
```

### 2. Pull VLM Models (Ollama)

```bash
# One-time download
ollama pull llava          # vision model (required)
ollama pull qwen2.5:3b     # chat model (optional, defaults used in GUI)
```

If Ollama isn't installed:
```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh

# Windows
Download from https://ollama.ai
```

### 3. Launch the Dashboard

```bash
streamlit run main_gui.py
```

**Output:**
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

Open that URL in a browser. You'll see:
- Egocentric camera feed (top-left)
- Tactile acceleration + FFT frequency plots (top-right)
- Dynamic colored banner showing current tactile classification
- **Grounded 2D World Map** with "⚡ Observe scene" button
- Memory inspector (all learned objects)
- Chat panel to query the agent

### 4. Test It

**Without hardware (mock mode, default):**
- Camera feed should show live camera
- Click **⚡ Observe scene (force VLM)** → llava analyzes frame
- Check the **Agent's Raw Perceptual Output** section to see what llava detected
- Detected objects appear on the 2D map with emoji icons

**To disable mock mode and connect Tuya board:**
- Sidebar → uncheck "Mock mode (no hardware)"
- Set serial port (default `/dev/ttyUSB0`)
- Verify baud rate: `460800`

---

## Project Structure

| File | Purpose |
|------|---------|
| `main_gui.py` | Streamlit dashboard — camera, plots, map, memory, chat |
| `world_model.py` | Persistent scene representation + VLM integration |
| `world_map.py` | Plotly 2D map renderer |
| `agent_simulator.py` | Fast tactile classifier + contact-event detector |
| `object_memory.py` | SQLite-backed persistent object store (visual embeddings, tactile signatures, audio frequencies) |
| `clip_encoder.py` | CLIP frame fingerprinting (optional fast-path) |
| `data_harvester.py` | Non-blocking serial reader (Tuya board data) |
| `main.c` | Firmware for Tuya T5 board (IMU + audio sampling) |
| `dsp_filter.c` | On-board FFT + Hann window |

See [FILES.md](FILES.md) for detailed API reference.

---

## Hardware Setup (Tuya T5 Board)

**If you have a Tuya T5AI-Board:**

### Pre-Flight

```bash
# 1. Install Arduino IDE 2.0+
#    https://www.arduino.cc/en/software

# 2. IDE → Preferences → Additional Board Manager URLs:
#    https://github.com/tuya/arduino-tuyaopen/releases/download/global/package_tuya_open_index.json

# 3. Tools → Board Manager → search "TuyaOpen" → Install

# 4. Tools → Board → TuyaOpen → T5
#    Verify: arduino-cli board listall | grep -i tuya
```

### Build & Flash

```bash
# Compile
arduino-cli compile --fqbn tuyaopen:arm:T5 .

# Find your uploader tool path, then flash:
~/.arduino15/packages/tuyaopen/tools/tyutool/<version>/tyutool \
  --port /dev/ttyUSB0 --chip t5 firmware.bin

# Verify serial stream
python -m serial.tools.miniterm /dev/ttyUSB0 460800
```

### Connect on Host

Disable mock mode in Streamlit sidebar:
- **Mock mode** → uncheck
- **Serial port** → `/dev/ttyUSB0` (or your port)
- Baud rate should auto-detect: `460800`

The agent will now consume tactile + audio telemetry from the board.

---

## Troubleshooting

### Camera won't open
- Check permissions: `ls -la /dev/video0` (Linux) or system settings (macOS/Windows)
- Try a different USB port
- If still blocked, the camera is likely open in another app — close it first

### "ModuleNotFoundError: No module named 'ollama'"
- Verify venv is activated: `which python` should show `.../venv/...`
- Reinstall: `pip install ollama`

### VLM not detecting objects
- **Check raw output:** Click "⚡ Observe scene" → look at **Agent's Raw Perceptual Output**
- Moondream has limits; try: better lighting, different angle, or larger objects
- To swap VLM: edit `main_gui.py` line 46, change `llava` to another Ollama model
  ```python
  vlm_model = st.sidebar.text_input("VLM model (Ollama)", value="llava-phi")  # or "minicpm-v"
  ```

### Database error on first run
```
ValueError: not enough values to unpack (expected 13, got 0)
```
Delete stale DB: `rm object_memory.db` → Streamlit will auto-recreate it.

### Serial data not flowing (with hardware)
```bash
# Test board is sending data
python -m serial.tools.miniterm /dev/ttyUSB0 460800

# Should see CSV lines:
# 104721,0.83,3412,0017
# 104722,0.81,3415,0018
```

If no output → board firmware issue. Reflash `main.c`.

---

## Architecture: Data-Driven Perception

**Before (hard-coded):**
- Fixed material states (Dry Leaves, Dense Sticks)
- Hard-coded frequency bands (Fan: 40–180 Hz, Water: 180–400 Hz)
- Every observation calls VLM → 1–3 s latency

**After (this repo):**
- **ObjectMemory:** Persistent SQLite store
  - Visual embedding (512-d CLIP vector)
  - Tactile signature (accel + FFT mean/std)
  - Audio frequency (learned via VLM, cached)
- **Dual-path perception:**
  - **Fast path (~50 ms):** CLIP-encode frame → memory lookup. If match ≥0.82 similarity, reuse cached scene.
  - **Slow path (1–3 s):** VLM analyzes frame + asks "which object emits ~N Hz?" Upserts new objects into memory.
- **Contact-event bootstrap:** On accel spike, bind to closest visible object → learn tactile signature from experience.
- **Result:** Real-time ~100 Hz perception. Open vocabulary. No hard-coded thresholds.

---

## Modes & Configuration

### Sidebar Controls

- **Mock mode** — toggle hardware on/off
- **Serial port** — USB serial device (default `/dev/ttyUSB0`)
- **Baud rate** — board TX rate (fixed: `460800`)
- **Plot window** — tactile sample history (50–500)
- **Auto-observe** — trigger VLM every N seconds
- **VLM model** — Ollama model name (default `llava`)
- **Chat model** — Ollama chat model (default `qwen2.5:3b`)
- **Memory DB path** — ObjectMemory SQLite file

### Chat Grounding

Ask the agent about the scene:
- *"What objects do you see?"* — answered from current Scene
- *"What did the blue thing feel like?"* — grounded in ObjectMemory tactile signatures
- *"What frequency was that sound?"* — bound to audio sources + cached frequencies

Replies are constrained by `build_chat_context()` to ground answers in observed data, not hallucination.

---

## Development

### Run Tests (Standalone)

```bash
# Tactile classifier
python agent_simulator.py --mock --db object_memory.db

# Serial diagnostics
python data_harvester.py --mock --dump
```

### Rebuild Graph Index (for Claude Code)

```bash
graphify hook install
# Graph auto-updates before each git commit
```

---

## Demos

### Quick demo (no objects):
1. Start Streamlit in mock mode
2. Click **⚡ Observe scene (force VLM)**
3. Watch llava output in **Agent's Raw Perceptual Output**
4. 2D map updates with detected objects

### With hardware (Tuya board):
1. Strap board to glove
2. Flash firmware + connect serial
3. Disable mock mode in sidebar
4. Touch objects around the room
5. Watch tactile banner detect contacts
6. Click **Observe** → map updates with learned object positions + audio bindings

---

## Known Limitations

- **Llava vision:** Limited object detection vs. larger models (GPT-4V, Gemini). Consider alternatives if accuracy is critical.
- **FFT size = 512 exactly:** Hard constraint on M33 microcontroller. Don't change.
- **Session state resets:** World model scene clears on page reload (use 🧹 button). ObjectMemory persists.
- **No network:** All compute is local (camera, VLM via Ollama, chat via Ollama).

---

## References

- **CLAUDE.md** — project architecture & invariants
- **FILES.md** — detailed API reference per file
- **World Model Details** — see `world_model.py` docstring
- **Ollama Models** — https://ollama.ai/library

---

**Ready to run?**

```bash
source venv/bin/activate
streamlit run main_gui.py
```

Then open `http://localhost:8501` in your browser. 🚀
