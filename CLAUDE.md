# CLAUDE.md — embodi-align

> Cross-Embodiment Data Harvester: multi-modal tactile/audio physical AI data collection tool.
> Target demo: sticker-scraping contact task across surface types (plastic / sandpaper / stuck sticker).

---

## Repo Layout

```text
embodi-align/
├── firmware/
│   ├── src/main.c          # IMU + audio sampling, serial TX @ 460800 baud
│   └── src/dsp_filter.c    # Hann window + FFT (CMSIS-DSP, N=512)
├── host_app/
│   ├── data_harvester.py   # Non-blocking serial reader → thread-safe Queue
│   ├── agent_simulator.py  # Perceive→Reason→Act heuristic policy loop
│   └── main_gui.py         # Streamlit dashboard: camera + tactile + state overlay
├── graphify-out/
│   └── graph.json          # Zero-token local structural index map used by Claude Code
├── requirements.txt
└── CLAUDE.md
```

---

## Hardware

**Board:** Tuya T5AI-Board / T5-E1 module (ARMv8-M Cortex-M33 @ 480MHz)
**Sensors:** QMI8658 6-axis IMU (SPI/I2C), onboard analog mic (CH343 USB-serial), optional ADC force pin
**Serial:** Onboard CH343 USB-to-serial chip → host at 460800 baud

> **Framework:** `arduino-TuyaOpen` core (Arduino IDE 2) instead of native TuyaOS SDK.
> Rationale: standard compile/upload cycle; 10× faster iteration under hackathon constraints.
> Upload uses the bundled **Tyutool** uploader (not standard `arduino-cli upload`).

---

## Zero-Token Graph Indexing (Claude Optimization)

To prevent Claude from burning through context tokens by reading large files repeatedly, this project uses a local, offline structural graph layout file (`graphify-out/graph.json`).

### Automated Graph Syncing (Prevents Stale Graph)
To ensure the graph stays synchronized with your VS Code edits automatically without manual intervention, configure one of the background runners before hacking:

#### Option A: The Git Commit Trigger (Highly Recommended)
Install a background pre-commit hook that silent-updates your structural map before every version stamp:
```bash
graphify hook install
```

---

## Pre-Hackathon Board Setup (do once before clock starts)

```bash
# 1. Install Arduino IDE 2 from https://www.arduino.cc/en/software

# 2. Add board manager URL in IDE → File → Preferences → Additional Board Manager URLs:
#    https://github.com/tuya/arduino-tuyaopen/releases/download/global/package_tuya_open_index.json

# 3. Install core: IDE → Tools → Board → Boards Manager → search "TuyaOpen" → Install

# 4. Confirm your board appears: Tools → Board → TuyaOpen → T5
#    (Board entry in boards.txt is "T5"; FQBN format: tuyaopen:arm:T5)
#    ⚠ Verify exact FQBN with: arduino-cli board listall | grep -i tuya

# 5. Flash a blank sketch to confirm toolchain works before day-of
```

> **OS caveat:** The arduino-TuyaOpen README explicitly states some chips are unsupported on
> certain operating systems. Verify your OS works at setup time, not during the hackathon.

---

## Build & Flash (Firmware)

```bash
# Compile (Arduino IDE 2 GUI, or via CLI after confirming FQBN above)
arduino-cli compile --fqbn tuyaopen:arm:T5 firmware/

# Flash — Tyutool is bundled by the core; IDE handles it via Tools → Upload
# For CLI upload, Tyutool path (verify after core install):
~/.arduino15/packages/tuyaopen/tools/tyutool/<version>/tyutool \
  --port /dev/ttyUSB0 --chip t5 firmware/firmware.bin

# Verify serial stream
python -m serial.tools.miniterm /dev/ttyUSB0 460800
```

---

## Host Setup & Launch

```bash
# Install dependencies
pip install pyserial numpy scipy streamlit opencv-python

# Launch GUI (spawns harvester + agent as background threads internally)
streamlit run host_app/main_gui.py

# Standalone serial diagnostics
python host_app/data_harvester.py --port /dev/ttyUSB0 --baud 460800 --dump
```

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

## Firmware Invariants (`firmware/src/`)

**main.c**
- IMU sample rate: 1 kHz; audio sample rate: 16 kHz (matches T5AI-Core default)
- Serial TX: `printf("%lu,%.4f,%u,%u\n", ts, az, fft_peak, frame_id)`
- No blocking calls in main loop; DMA transfers only

**dsp_filter.c**
- FFT size: **512 samples only** (power-of-two; stack overflow prevention on M33)
- Window: Hann (`arm_hanning_f32`) applied before `arm_rfft_fast_f32`
- Output: single dominant bin → Hz = `(bin * 16000) / 512`

---

## Agent State Machine (`host_app/agent_simulator.py`)

| Material State    | Signature                             | Policy Directive                                               |
|-------------------|---------------------------------------|----------------------------------------------------------------|
| Smooth Plastic    | accel < 0.3g AND fft_peak > 2000 Hz  | `MAINTAIN: velocity=nominal, pitch=0°, torque=1.0x`           |
| Rough Sandpaper   | accel 0.3–1.0g AND fft_peak < 800 Hz | `ADJUST: velocity=-10%, pitch=+2°, torque=0.85x`              |
| Stuck Sticker     | accel > 1.5g AND fft_peak < 300 Hz   | `ACTION: velocity=-40%, pitch=+5°, torque=2.5x↓, dwell=+200ms`|
| Unknown/Transient | else                                  | `HOLD: maintain last known state`                              |

---

## Thread Safety (`host_app/`)

```python
# data_harvester.py — producer
from queue import Queue
token_queue: Queue = Queue(maxsize=512)  # never block GUI thread

# main_gui.py — consumer
# token_queue.get_nowait() inside st.empty() loop; catch queue.Empty
```

`data_harvester.py` runs in `threading.Thread(daemon=True)`. Never call `serial.read()` from the Streamlit main thread.

---

## Operational Constraints

- **No network calls.** No cloud DB, no external API. Fully air-gapped.
- **FFT buffer = 512 exactly.** Any other value risks stack overflow on M33.
- **Baud = 460800.** Mismatched host baud drops tokens silently; verify with `miniterm` first.
- **Camera feed** runs in a second daemon thread; frames in `queue.Queue(maxsize=2)` to cap memory.
- **CH343 driver** may require manual install on macOS/Windows — fetch from WCH before the hackathon.
