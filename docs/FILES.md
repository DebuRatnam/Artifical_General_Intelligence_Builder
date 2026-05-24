# FILES.md — Per-File Reference

Quick map of every source file in the repo, what it does, and what it
exports. Cross-references use the in-repo path so they're clickable in
the IDE.

---

## Firmware (runs on the Tuya T5 board)

### [main.c](main.c)
Arduino-TuyaOpen entry point for the T5 microcontroller. Owns the
hardware sampling loop and the serial TX format. Reads one 12-bit ADC
audio sample per `loop()` iteration; once 512 samples are buffered,
it reads one Z-axis accel value from the QMI8658 IMU over I²C, runs
the FFT (via `dsp_filter.c`), and emits one CSV serial line at
460800 baud.

**Key symbols**
- `setup()` — initializes UART, I²C, ADC, DSP.
- `loop()` — fills audio buffer; on full buffer, samples IMU,
  computes FFT peak, prints one telemetry line.
- `qmi8658_read_az()` — I²C read of one signed 16-bit Z-axis value.
- `read_audio_sample()` — single 12-bit ADC sample centered around 0.

### [dsp_filter.c](dsp_filter.c) / [dsp_filter.h](dsp_filter.h)
On-board signal processing. CMSIS-DSP wrapper that applies a Hann
window to the 512-sample audio buffer, runs a real FFT, computes the
magnitude spectrum, and returns the dominant frequency in Hz. Pure
function — no allocation in the hot path; window coefficients are
pre-computed at init.

**Key symbols**
- `dsp_filter_init(sample_rate, buf_size)` — one-time setup of the
  FFT instance and Hann window.
- `dsp_get_peak_hz(samples, n)` — Hann-window → rFFT → magnitude →
  argmax → Hz. Called once per 512-sample buffer.

---

## Host: Sensor I/O Layer

### [data_harvester.py](data_harvester.py)
Non-blocking serial reader. Runs as a daemon thread; reads CSV lines
off the USB-serial port and pushes parsed tokens into a thread-safe
`Queue` (`token_queue`, size 512). Includes a mock-mode producer so
the host stack can be exercised without the board attached.

**Key symbols**
- `token_queue` — bounded `Queue` shared with `agent_simulator` and
  `main_gui`.
- `_parse_line(line)` — CSV → `[ts_ms, accel_g, fft_peak_hz, frame_id]`.
- `_push(token)` — non-blocking enqueue; drops oldest if the queue
  is full so the producer never stalls.
- `_reader_loop(port, baud, stop_event)` — auto-reconnects on serial
  errors with a 2 s backoff.
- `start(port, baud)` — start the serial daemon thread.
- `start_mock(hz)` — synthetic-token generator for hardware-free
  testing.

---

## Host: Reasoning Layer

### [object_memory.py](object_memory.py)
**Persistent multi-modal object store.** SQLite-backed database that
learns and remembers every object the agent has seen, touched, or heard
across sessions. Enables open-vocabulary perception: agent learns tactile
signatures (accel + FFT mean/std) and audio frequencies per object
through experience, without hard-coded material states.

**Key symbols**
- `ObjectCard` (dataclass) — one learned object: label, visual_embedding
  (512-d CLIP vector or None), tactile_accel_{mean,std}, tactile_fft_{mean,std},
  audio_freq_hz, description, n_visual/n_tactile/n_audio counters,
  last_updated timestamp.
- `ObjectMemory.__init__(db_path)` — SQLite loader/initializer.
- `upsert_visual(label, embedding, description)` — insert or EMA-merge
  a visual embedding (512-d unit vector) for a label.
- `update_tactile(label, accel_g, fft_hz)` — push one tactile sample;
  EMA-updates mean + std (α=0.2).
- `update_audio(label, freq_hz)` — record observed audio peak Hz.
- `nearest_visual(embedding, top_k=3, threshold=0.75)` — cosine search
  for the frame's CLIP vector; returns list of (label, similarity, ObjectCard)
  or empty if no hit ≥threshold.
- `nearest_tactile(accel_g, fft_hz, max_sigma=2.5)` — Mahalanobis-ish
  σ-gating on learned tactile signatures; returns (label, σ-distance)
  or None if no learned signature within gate.
- `get(label)`, `all()`, `forget(label)` — query, list, delete.

### [clip_encoder.py](clip_encoder.py)
**Fast frame fingerprinting.** Lazy wrapper around open_clip for computing
512-d unit-norm visual embeddings of camera frames in ~50ms on CPU.
Enables the fast-path scene re-identification (skip expensive VLM if
CLIP finds a cached match ≥0.82 similarity). Gracefully degrades to
None embeddings if torch/open_clip are not installed.

**Key symbols**
- `CLIPEncoder.__init__(model_name="ViT-B-32", pretrained="openai", device="cpu")`
  — lazy init; prints hint if deps missing.
- `_load()` — best-effort import + model load; sets enabled=False on failure.
- `encode_image(frame_bgr)` — BGR OpenCV frame → 512-d unit-norm numpy array
  (or None if disabled or error).
- `encode_text(text)` — text → same 512-d space (future use: text-to-image
  retrieval without VLM).

### [agent_simulator.py](agent_simulator.py)
**Fast data-driven tactile classifier.** Watches `token_queue` and
classifies each tactile sample (accel + FFT peak) against learned
ObjectMemory signatures. Updates module-level globals (`current_label`,
`current_directive`, `current_distance`) that the GUI reads each tick.
Powers the dynamic colored banner — independent of VLM/world-model.
Bootstraps new tactile signatures via contact-event detection + hand-proximity
binding (see `handle_contact` in `world_model.py`).

**Key symbols**
- `classify(memory, accel_g, fft_peak_hz)` — calls memory.nearest_tactile();
  returns (label, σ-distance) or None. No hard-coded thresholds.
- `ContactDetector` — EMA-based spike detector.
  - `__init__(baseline_alpha=0.05, spike_g=0.35, refractory_s=0.6)`.
  - `step(accel_g)` — returns True on rising edge (accel jump > spike_g
    above baseline). EMA baseline adapts to ambient vibration; refractory
    gate prevents chatter.
- `emit_directive(label, dist)` — formats (label, σ-distance) as
  human-readable status ("Touching: {label} (σ={dist})" or
  "Listening — no tactile signature matched...").
- `run(token_queue, memory, world_model, stop_event)` — main consumer loop.
  Classifies each sample; on contact spike calls world_model.handle_contact()
  to bind + learn.
- `start(token_queue, memory, world_model)` — spawn the daemon thread.
- Module-level globals: `current_label`, `current_directive`, `current_distance`,
  `last_contact_ts` — read by `main_gui`.

### [multimodal_agent.py](multimodal_agent.py)
**Legacy.** One-shot VLM summary path (kept for reference). Sends the
current frame + tactile/audio metrics to Ollama and returns a 2-sentence
narrative. Replaced by the stateful `world_model.py` + `ObjectMemory`
path, which maintains persistent scene representation.

**Key symbols**
- `UnifiedEmbodiedAgent(model_name)` — constructor + warm-up.
- `generate_grounded_summary(frame, accel_g, fft_hz, heuristic_state)` —
  sync VLM call, returns text.

### [world_model.py](world_model.py)
**Primary brain.** LeCun-style persistent perceptual world model with
dual-path perception: fast CLIP-based re-identification + slow VLM for
novel objects. Owns the `Scene` dataclass (objects + audio sources + hand pose),
the VLM prompt template, regex parsing, and the contact-event bootstrap
path for learning new tactile signatures.

**Key symbols**
- `SceneObject`, `AudioSource`, `HandPose`, `Scene` (dataclasses).
- `POS_X` / `POS_Y` — keyword → coordinate maps for the 9-cell grid.
- `Scene.decay(half_life_s)` — confidence falloff + stale eviction.
- `_PROMPT_TEMPLATE` — strict line-format VLM prompt.
- `_OBJECT_RE`, `_SOUND_RE` — regexes for parsing VLM output.
- `_parse_vlm_output(text)` — line-by-line regex parse.
- `WorldModel.__init__(model_name, memory_path, clip_device="cpu", vlm_force_every=15.0)`
  — wire up Ollama VLM client, ObjectMemory instance, CLIPEncoder. vlm_force_every
  forces slow path periodically to catch new objects.
- `_try_fast_path(frame)` — CLIP-encode frame; query memory.nearest_visual();
  if match ≥0.82 similarity, populate Scene from cached ObjectCard and return True.
  Else False.
- `_vlm_bind_audio(fft_hz, candidates)` — ask VLM "which visible object emits ~N Hz?"
  Replaces hard-coded FREQ_BANDS table. Result cached to memory.audio_freq_hz.
- `observe(frame, accel_g, fft_hz, force_vlm=False)` — main entry point.
  Tries fast path first; falls through to slow path if no hit. Parses VLM output
  and upserts all detected objects into ObjectMemory. Returns Scene with
  last_used_fast_path flag.
- `handle_contact(accel_g, fft_hz, max_dist=0.25)` — on tactile spike,
  finds closest visible object. If distance ≤ max_dist, calls
  memory.update_tactile(label, accel, fft) to bootstrap/update signature,
  and returns label. This is how the agent learns new tactile signatures
  from experience.
- `reset()` — wipes the scene (memory is NOT cleared).

---

## Host: UI Layer

### [world_map.py](world_map.py)
Pure rendering. Converts a `Scene` into a Plotly `Figure`. No state,
no I/O — given the same `Scene`, returns the same figure. Used by
`main_gui.py` and reusable for screenshots / exports.

**Key symbols**
- `render_scene(scene)` — emoji markers for objects at (x, y) with
  confidence wash, top-strip annotations for audio sources with their
  bound Hz, hand pose indicator.

### [main_gui.py](main_gui.py)
Streamlit dashboard. Six rows:
1. **Dynamic tactile banner** — colored by object label hash (MD5), not
   hard-coded states. Shows current tactile classification + σ-distance.
2. **Camera + tactile/audio line charts** (left/right columns).
3. **Grounded 2D world map** with **Observe scene (force VLM)** and
   **Quick observe (fast path)** buttons, metrics, and auto-observe toggle.
4. **Raw VLM output** of the latest observation.
5. **Memory inspector** — dataframe of all learned ObjectCards: label,
   n_visual, n_tactile, n_audio, accel_mean, fft_mean, audio_freq_hz,
   tactile_trained flag.
6. **Chat panel** — user text input. Replies are grounded in current Scene
   + ObjectMemory via `build_chat_context()` system prompt. Uses Ollama
   chat model (configurable in sidebar, default `qwen2.5:3b`).

Owns the Streamlit `session_state` keys: `world_model`, `accel_buf`,
`fft_buf`, `ts_buf`, `latest_raw_frame`, `last_auto_obs`, `started`,
`chat_history`, `agent_thought`.

The page calls `st.rerun()` every 200 ms to keep plots and map fresh;
VLM calls are opt-in (button or auto-observe) so the page isn't blocked.

**Key symbols**
- `label_color(label)` — MD5(label) hash → "#rrggbb" for dynamic banner.
- `build_chat_context(world_model, accel, fft)` — serialize Scene +
  ObjectMemory into RAG context for chat grounding.
- Sidebar controls: `use_mock`, `serial_port`, `baud_rate`, `window_size`,
  `auto_observe`, `auto_period`, `vlm_model`, `chat_model`, `memory_path`.

---

## Config / Data

### [requirements.txt](requirements.txt)
Python deps for the host stack. Core: `pyserial`, `numpy`, `scipy`,
`streamlit`, `opencv-python`, `ollama`, `plotly`, `pandas`. Optional
fast-path deps (gracefully degrade if missing): `open-clip-torch>=2.24`,
`torch>=2.1`, `Pillow>=10.0`.

### [CLAUDE.md](CLAUDE.md)
Project rules + architecture overview consumed by Claude Code on every
session start. Read it before making structural changes.

### [graphify-out/](graphify-out/)
Local, offline structural index of the repo. Used by Claude Code to
locate code without re-reading large files. Refreshed by the graphify
git hook.

---

## File-Dependency Graph (host stack only)

```text
main_gui.py
  ├── world_model.py ─── ObjectMemory, CLIPEncoder, ollama, cv2
  │   ├── object_memory.py
  │   └── clip_encoder.py ─── torch, open_clip, PIL (optional)
  ├── world_map.py ────────── plotly
  ├── agent_simulator.py ──── ObjectMemory
  └── data_harvester.py ────── pyserial

multimodal_agent.py (unreferenced, legacy)
```

---

## Architecture: Open-Vocab Perception Pipeline

**Before (hard-coded):**
- Fixed material states (Dry Leaves, Dense Sticks, Unknown) with
  thresholded accel/FFT ranges.
- Hard-coded frequency band table (Fan: 40–180 Hz, Water: 180–400 Hz, etc.).
- Frame classification: every observe() calls VLM (1–3 s latency).

**After (data-driven):**
- **ObjectMemory**: Persistent SQLite store. Each object learns:
  - Visual embedding (512-d CLIP fingerprint).
  - Tactile signature (accel + FFT mean/std from experience).
  - Audio frequency (learned via VLM → cached).
- **Dual-path perception**:
  - **Fast path** (~50 ms): CLIP-encode frame → nearest_visual() in memory
    (cosine search). If hit ≥0.82 similarity, reuse cached scene. Skip VLM.
  - **Slow path** (1–3 s): VLM labels frame + asks "which object emits ~N Hz?"
    Upsert all new objects into memory.
- **Contact event bootstrap**: On accel spike, bind to closest visible object
  (hand-proximity heuristic) → `memory.update_tactile()` → EMA-learn signature.
- **Result**: Real-time perception at ~100 Hz. Open vocabulary. Cross-session
  learning. No hard-coded thresholds.
