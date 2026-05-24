# PIA (Physics-Informed Agents): Grounded Perceptual Agent

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

### System Dependencies (Install First)

Before running any commands, install these system-level tools:

**1. Git**
- macOS: `brew install git`
- Windows: https://git-scm.com/download/win
- Linux: `sudo apt install git`
- Verify: `git --version`

**2. Python 3.8+**
- Download: https://www.python.org/downloads/
- Choose 3.10+ recommended (tested with 3.14)
- macOS: `brew install python3`
- Windows: Run installer, **check "Add Python to PATH"**
- Verify: `python3 --version`

**3. Node.js + npm** (required for React frontend)
- Download: https://nodejs.org (LTS version recommended)
- Includes npm automatically
- Verify: `node --version` and `npm --version`

**4. Ollama** (VLM inference engine)
- Download: https://ollama.ai
- macOS: `brew install ollama`
- Linux: `curl https://ollama.ai/install.sh | sh`
- Windows: Download from https://ollama.ai
- Verify: `ollama --version`

**5. Camera** (built-in or USB webcam)
- Ensure camera is plugged in and working
- Test in system settings (Camera app on macOS)

### Prerequisites

Once system dependencies are installed, you'll need:

- **Python 3.8+** (from above)
- **Ollama** (from above)
- **Camera** (from above)

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

Two supported UIs:

**A) Streamlit (legacy single-process)**

```bash
streamlit run backend/main_gui.py
```

**B) FastAPI backend + Vite React frontend (recommended)**

One command boots both:

```bash
./scripts/run_dev.sh
```

Output:

```
[run_dev] starting FastAPI server on :8000 …
[run_dev] starting Vite dev server on :5173 …
  API : http://localhost:8000   (docs: /docs, ws: /ws/telemetry)
  WEB : http://localhost:5173
```

Open `http://localhost:5173`. Ctrl-C stops both processes.

The script:
- activates `./venv` if present
- runs `npm install` in `frontend/` the first time
- streams both logs with `[api]` / `[web]` prefixes
- traps SIGINT/SIGTERM so neither process is orphaned

Manual two-terminal equivalent (run from repo root):

```bash
# terminal 1 — backend
source venv/bin/activate
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload

# terminal 2 — frontend
cd frontend
npm install         # first time only
npm run dev         # http://localhost:5173, proxies /api + /ws/telemetry to :8000
```

Environment overrides (either path):

| Var                 | Default            | Notes                                    |
|---------------------|--------------------|------------------------------------------|
| `PIA_USE_MOCK`      | `1`                | `0` = real serial hardware               |
| `PIA_SERIAL_PORT`   | `/dev/ttyUSB0`     | Board serial device                      |
| `PIA_BAUD_RATE`     | `460800`           | Match `firmware/main.c` TX rate          |
| `PIA_VLM_MODEL`     | `llava`            | Ollama vision model                      |
| `PIA_CHAT_MODEL`    | `qwen2.5:3b`       | Ollama chat model                        |
| `PIA_MEMORY_PATH`   | `object_memory.db` | SQLite path                              |
| `PIA_CAMERA_INDEX`  | `0`                | `cv2.VideoCapture(index)`                |
| `PIA_WS_HZ`         | `40`               | `/ws/telemetry` push rate (30–60 sane)   |
| `PORT_API`          | `8000`             | `run_dev.sh` only                        |
| `PORT_WEB`          | `5173`             | `run_dev.sh` only                        |

**Legacy Streamlit (option A) — same flow as before:**

```bash
streamlit run backend/main_gui.py
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
- Camera feed displays live real-time camera stream via browser `getUserMedia` API
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
| `backend/main_gui.py` | Streamlit dashboard — camera, plots, map, memory, chat (legacy) |
| `backend/server.py` | Headless FastAPI backend — REST + WebSocket telemetry |
| `frontend/` | Vite + React + Tailwind dashboard (talks to `backend/server.py`) |
| `scripts/run_dev.sh` | One-shot launcher for `server.py` + Vite dev server |
| `perception/world_model.py` | Persistent scene representation + VLM integration |
| `perception/world_map.py` | Plotly 2D map renderer |
| `perception/object_memory.py` | SQLite-backed persistent object store (visual embeddings, tactile signatures, audio frequencies) |
| `perception/clip_encoder.py` | CLIP frame fingerprinting (optional fast-path) |
| `agents/agent_simulator.py` | Fast tactile classifier + contact-event detector |
| `agents/multimodal_agent.py` | Legacy one-shot VLM summary path |
| `sensors/data_harvester.py` | Non-blocking serial reader (Tuya board data) |
| `firmware/main.c` | Firmware for Tuya T5 board (IMU + audio sampling) |
| `firmware/dsp_filter.c` | On-board FFT + Hann window |

See [docs/FILES.md](docs/FILES.md) for detailed API reference.

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

### Physical Attachment

1. **Board + Glove:** Strap the T5 board to the back of a glove or hand using:
   - Velcro strips (industrial-strength, both sides)
   - Elastic band around wrist/palm
   - Medical tape (comfortable, removable)

2. **Orientation:** IMU Z-axis should point upward (perpendicular to palm). Microphone should face outward to capture ambient sound.

3. **Cable routing:** USB micro-B cable goes from board to host laptop. Keep cable slack to avoid tugging during movement.

### Driver Installation (USB Serial)

Board uses **WCH CH343 USB-to-serial chip** for telemetry stream. Most systems auto-detect, but manual install may be needed:

**macOS:**
```bash
# Download CH343 driver from WCH: https://www.wch.cn/downloads/category/63.html
# Or via homebrew (if available):
brew install wch-ch34x-usb-serial-driver

# Verify connection:
ls -la /dev/tty.* | grep -i ch343  # Should show /dev/tty.usbserial-*
```

**Windows:**
- Download driver from: https://www.wch.cn/downloads/category/63.html
- Run installer, reboot
- Device Manager should show board as COM port (e.g., COM3)

**Linux:**
- Usually auto-detected as `/dev/ttyUSB0`
- If not: `sudo modprobe ch343` and replug USB
- Set permissions: `sudo usermod -a -G dialout $USER` (then logout/login)

### Hardware Diagnostics

If board not recognized after connection:

```bash
# Check connected USB devices
lsusb | grep -i ch343       # Linux
system_profiler SPUSBDataType | grep -i ch343  # macOS

# Check serial port
ls /dev/tty*                # macOS/Linux
# Windows: Device Manager → Ports (COM & LPT)

# Test serial stream (after finding port)
python -m serial.tools.miniterm /dev/ttyUSB0 460800
# Should see CSV lines: 104721,0.83,3412,0017

# If no output:
#   1. Verify baud rate matches firmware (460800)
#   2. Re-flash firmware via Arduino IDE
#   3. Try different USB port
#   4. Check USB cable is data-capable (not charge-only)
```

### Connect on Host

**FastAPI/React frontend (recommended):**
```bash
./scripts/run_dev.sh
# Then in sidebar on http://localhost:5173:
# - Board mode → uncheck "Mock mode (no hardware)"
# - Serial port → `/dev/ttyUSB0` (or your detected port)
# - Baud rate: `460800`
```

**Streamlit (legacy):**
Disable mock mode in sidebar:
- **Mock mode** → uncheck
- **Serial port** → `/dev/ttyUSB0` (or your port)
- Baud rate should auto-detect: `460800`

The agent will now consume tactile + audio telemetry from the board in real-time.

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
- **VLM has strict validation:** llava is filtered to ONLY confident, clearly visible objects (see `perception/world_model.py` prompt template). Dim lighting, blurry frames, or small objects may be skipped by design.
- **If still hallucinating:** Try better lighting, different angle, or larger objects
- **Reduce false positives:** The prompt enforces `CRITICAL: If you are uncertain about an object, do NOT include it` and caps output at 4 objects per frame
- **To swap VLM:** Edit `backend/main_gui.py` (look for `vlm_model = st.sidebar.text_input(...)`) and change `llava` to another Ollama model
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

If no output → board firmware issue. Reflash `firmware/main.c`.

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
# Tactile classifier  (run from repo root)
python -m agents.agent_simulator --mock --db object_memory.db

# Serial diagnostics
python -m sensors.data_harvester --mock --dump
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
- **World Model Details** — see `perception/world_model.py` docstring
- **Ollama Models** — https://ollama.ai/library

---

**Ready to run?**

```bash
source venv/bin/activate
./scripts/run_dev.sh             # FastAPI :8000 + Vite :5173  (recommended)
# or
streamlit run backend/main_gui.py   # legacy single-process UI on :8501
```

Open `http://localhost:5173` (Vite) or `http://localhost:8501` (Streamlit). 🚀
