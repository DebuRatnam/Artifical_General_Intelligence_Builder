# CLAUDE.md — embodi-align

> **Cross-Embodiment Grounded Perceptual Agent.**
> Audio + vision world model that builds a 2D top-down map of the room
> the agent is currently in. Inspired by Yann LeCun's argument that real
> intelligence requires a persistent world representation, not just
> next-token prediction.
>
> Hardware target: **Tuya T5AI-Board** strapped to a glove. Onboard
> mic + IMU stream tactile/audio telemetry over USB-serial; host laptop
> runs the camera, the VLM (moondream via Ollama), and the world model.
>
> Demo flow: agent looks around a room → identifies objects + their
> rough 2D positions → binds dominant audio frequencies to the visible
> noise sources (fan ≈ 120 Hz, running water ≈ 200 Hz, etc.) → renders
> an iconographic top-down map that updates as the scene changes.

---

## Repo Layout

```text
embodi-align/
├── main.c                  # T5 firmware: IMU + audio sampling, 460800 baud TX
├── dsp_filter.c / .h       # Hann window + CMSIS-DSP rFFT (N=512)
├── data_harvester.py       # Non-blocking serial reader → thread-safe Queue
├── agent_simulator.py      # Heuristic tactile classifier (low-level state)
├── multimodal_agent.py     # (legacy) one-shot VLM summary path
├── world_model.py          # LeCun-style persistent scene representation
├── world_map.py            # Plotly emoji 2D map renderer
├── main_gui.py             # Streamlit dashboard (camera + plots + map)
├── graphify-out/graph.json # Zero-token structural index for Claude Code
├── requirements.txt
└── CLAUDE.md
```

---

## Two Pillars of the Project

### 1. Grounded perceptual agent (world model, not token predictor)

`world_model.py` maintains a persistent `Scene` across observations:

- **Object map:** `dict[label → SceneObject(x, y, icon, confidence)]`,
  positions in `[0, 1]` top-down coordinates.
- **Audio sources:** `dict[label → AudioSource(icon, freq_hz)]`, with
  the live FFT peak bound to the most plausible visible emitter.
- **Confidence decay:** objects not re-observed in subsequent frames
  fade out (half-life ≈ 6 s) — the scene is *remembered*, not just
  classified frame-by-frame.

Each `observe(frame, accel_g, fft_hz)` call:
1. Sends the frame to moondream (Ollama) with a strict line-format prompt.
2. Regex-parses each line → `SceneObject` / `AudioSource`.
3. Merges new observations into the persistent `Scene` (EMA on positions).
4. Binds the current FFT peak to whichever sound-emitter best matches
   its frequency band (`world_model.FREQ_BANDS`).
5. Decays stale entries.

### 2. 2D iconographic map UI

`world_map.py` renders the current `Scene` as a Plotly figure:

- Each `SceneObject` → emoji marker + bold label at its `(x, y)`.
- Each `AudioSource` → annotation in the top strip with its FFT peak
  in Hz (e.g. `💨 Fan — 120 Hz`).
- A faint confidence wash behind each icon scales with `confidence`.

`main_gui.py` embeds the map below the camera + tactile plots and
re-renders every Streamlit tick. The **⚡ Observe scene** button (or
auto-observe toggle) triggers a new `WorldModel.observe(...)` call.

---

## Hardware

**Board:** Tuya T5AI-Board / T5-E1 module (ARMv8-M Cortex-M33 @ 480 MHz)
**Sensors:** QMI8658 6-axis IMU (SPI/I2C), onboard analog mic (CH343 USB-serial)
**Serial:** Onboard CH343 USB-to-serial chip → host at **460800 baud**

> **Framework:** `arduino-TuyaOpen` core (Arduino IDE 2), not native TuyaOS SDK.
> Rationale: standard compile/upload cycle, 10× faster iteration under
> hackathon constraints. Upload uses the bundled **Tyutool** uploader
> (not standard `arduino-cli upload`).

---

## Pre-Hackathon Board Setup

```bash
# 1. Install Arduino IDE 2: https://www.arduino.cc/en/software

# 2. IDE → File → Preferences → Additional Board Manager URLs:
#    https://github.com/tuya/arduino-tuyaopen/releases/download/global/package_tuya_open_index.json

# 3. IDE → Tools → Board → Boards Manager → search "TuyaOpen" → Install

# 4. Confirm board: Tools → Board → TuyaOpen → T5
#    FQBN: tuyaopen:arm:T5  (verify with: arduino-cli board listall | grep -i tuya)

# 5. Flash a blank sketch to confirm the toolchain works.
```

> **OS caveat:** Some chips are unsupported on certain operating systems —
> verify at setup time, not during the hackathon. **CH343 driver** may
> require manual install on macOS/Windows (fetch from WCH ahead of time).

---

## Build & Flash (Firmware)

```bash
arduino-cli compile --fqbn tuyaopen:arm:T5 .

~/.arduino15/packages/tuyaopen/tools/tyutool/<version>/tyutool \
  --port /dev/ttyUSB0 --chip t5 firmware.bin

# Sanity-check the stream
python -m serial.tools.miniterm /dev/ttyUSB0 460800
```

---

## Host Setup & Launch

```bash
# Deps
pip install -r requirements.txt

# Pull the VLM (once)
ollama pull moondream

# Launch
streamlit run main_gui.py

# Standalone serial diagnostics
python data_harvester.py --port /dev/ttyUSB0 --baud 460800 --dump
python data_harvester.py --mock --dump   # no hardware
```

The Streamlit sidebar exposes mock mode (synthetic tokens), serial port,
auto-observe toggle, and VLM model name (default `moondream`).

---

## Serial Protocol

**Format:** `<timestamp_ms>,<accel_g>,<audio_fft_peak_hz>,<frame_id>\n`
**Example:** `104721,0.83,3412,0017`

| Field          | Type    | Unit | Notes                    |
|----------------|---------|------|--------------------------|
| timestamp_ms   | uint32  | ms   | Board uptime             |
| accel_g        | float32 | g    | QMI8658 Z-axis magnitude |
| audio_fft_peak | uint16  | Hz   | Dominant FFT bin (N=512) |
| frame_id       | uint16  | —    | Wraps at 65535           |

---

## Firmware Invariants (`main.c`, `dsp_filter.c`)

- IMU sample rate: 1 kHz; audio sample rate: 16 kHz.
- Serial TX: `printf("%lu,%.4f,%u,%u\n", ts, az, fft_peak, frame_id);`
- No blocking calls in main loop; DMA transfers only.
- **FFT size = 512 samples exactly.** Any other value risks stack
  overflow on the M33. Hann window (`arm_hanning_f32`) before
  `arm_rfft_fast_f32`. Peak Hz = `(bin * 16000) / 512`.

---

## World Model Conventions

### Spatial coordinate system
- `x ∈ [0, 1]`, 0 = left edge, 1 = right edge.
- `y ∈ [0, 1]`, 0 = bottom edge, 1 = top edge.
- Position keywords from the VLM map to these via
  `world_model.POS_X` and `world_model.POS_Y`.

### Audio frequency → source band

| Band         | Range (Hz)   | Likely source                |
|--------------|--------------|------------------------------|
| fan          | 40 – 180     | HVAC, table fan, motor       |
| water        | 180 – 400    | faucet, sink, running water  |
| voice        | 400 – 1200   | speech, phone, TV            |
| electronic   | 1200 – 3500  | speaker, monitor whine       |
| high         | 3500 – 8000  | whistle, alarm, beep         |

Edit `world_model.FREQ_BANDS` to retune.

### VLM output template (strict)

```
- LABEL | POSITION | EMOJI
SOUND: LABEL | EMOJI
```

`POSITION` is one of nine keywords (`top-left`, `top-center`, ...,
`bottom-right`). Parsed by `world_model._OBJECT_RE` /
`world_model._SOUND_RE`. If you change the template, update both
regexes together.

---

## Heuristic Tactile Agent (`agent_simulator.py`)

The tactile classifier runs in parallel with the world model as a
fast low-level state machine. It does **not** drive the world map —
it powers the colored banner at the top of the dashboard.

| Tactile state | Signature                            | Directive                                  |
|---------------|--------------------------------------|--------------------------------------------|
| Dry Leaves    | accel < 0.5 g  AND  fft_peak > 1200  | velocity −10%, pitch +1°, torque 0.5×      |
| Dense Sticks  | accel ≥ 1.0 g  AND  fft_peak < 600   | velocity −30%, pitch +4°, torque 2.2×      |
| Unknown       | else                                  | HOLD — maintain last known state           |

---

## Thread Safety

```python
# data_harvester.py — producer (daemon thread)
from queue import Queue
token_queue: Queue = Queue(maxsize=512)  # bounded → never blocks GUI

# main_gui.py — consumer (Streamlit main thread)
# token_queue.get_nowait() in a tight loop; catches queue.Empty.
```

`data_harvester.py` and `agent_simulator.py` both run as
`threading.Thread(daemon=True)`. **Never call `serial.read()` from the
Streamlit main thread.** Camera frames are captured synchronously per
Streamlit tick (cheap enough for the demo).

---

## Operational Constraints

- **No network calls** for telemetry. The VLM runs locally via Ollama.
- **FFT buffer = 512 exactly.** Hard constraint on M33.
- **Baud = 460800.** Mismatched host baud silently drops tokens —
  verify with `miniterm` first.
- Camera frames captured per Streamlit tick; no separate camera
  thread needed at current frame rates.
- World model state is **per-session in `st.session_state`** —
  it resets when the page reloads (or via the **🧹 Reset world model**
  button).

---

## Zero-Token Graph Indexing

`graphify-out/graph.json` is a local, offline structural map used by
Claude Code to navigate the repo without re-reading large files. Keep
it fresh:

```bash
graphify hook install   # auto-update before every git commit
```
