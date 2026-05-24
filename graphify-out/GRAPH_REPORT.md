# Graph Report - .  (2026-05-24)

## Corpus Check
- 21 files · ~18,315 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 401 nodes · 565 edges · 41 communities (26 shown, 15 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 78 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_World Model & Scene Representation|World Model & Scene Representation]]
- [[_COMMUNITY_Serial Hardware IO|Serial Hardware I/O]]
- [[_COMMUNITY_Persistent Object Memory|Persistent Object Memory]]
- [[_COMMUNITY_World Model & Scene Representation|World Model & Scene Representation]]
- [[_COMMUNITY_World Model & Scene Representation|World Model & Scene Representation]]
- [[_COMMUNITY_Backend HTTP API|Backend HTTP API]]
- [[_COMMUNITY_Telemetry WebSocket Stream|Telemetry WebSocket Stream]]
- [[_COMMUNITY_Backend HTTP API|Backend HTTP API]]
- [[_COMMUNITY_Firmware & Hardware Interface|Firmware & Hardware Interface]]
- [[_COMMUNITY_Backend HTTP API|Backend HTTP API]]
- [[_COMMUNITY_Backend HTTP API|Backend HTTP API]]
- [[_COMMUNITY_World Model & Scene Representation|World Model & Scene Representation]]
- [[_COMMUNITY_Vision Encoding (CLIP)|Vision Encoding (CLIP)]]
- [[_COMMUNITY_Tactile Classification & Policy|Tactile Classification & Policy]]
- [[_COMMUNITY_Audio Frequency Analysis|Audio Frequency Analysis]]
- [[_COMMUNITY_Utility Module 15|Utility Module 15]]
- [[_COMMUNITY_Utility Module 16|Utility Module 16]]
- [[_COMMUNITY_Firmware & Hardware Interface|Firmware & Hardware Interface]]
- [[_COMMUNITY_VLM Perception Agent|VLM Perception Agent]]
- [[_COMMUNITY_Vision Encoding (CLIP)|Vision Encoding (CLIP)]]
- [[_COMMUNITY_Vision Encoding (CLIP)|Vision Encoding (CLIP)]]
- [[_COMMUNITY_Vision Encoding (CLIP)|Vision Encoding (CLIP)]]
- [[_COMMUNITY_Utility Module 33|Utility Module 33]]
- [[_COMMUNITY_Vision Encoding (CLIP)|Vision Encoding (CLIP)]]
- [[_COMMUNITY_Utility Module 35|Utility Module 35]]
- [[_COMMUNITY_Utility Module 36|Utility Module 36]]
- [[_COMMUNITY_Utility Module 37|Utility Module 37]]
- [[_COMMUNITY_Serial Hardware IO|Serial Hardware I/O]]
- [[_COMMUNITY_Firmware & Hardware Interface|Firmware & Hardware Interface]]
- [[_COMMUNITY_Backend HTTP API|Backend HTTP API]]

## God Nodes (most connected - your core abstractions)
1. `run()` - 17 edges
2. `classify()` - 10 edges
3. `_parse_vlm_output()` - 10 edges
4. `main_gui (Streamlit app)` - 10 edges
5. `Scene` - 10 edges
6. `WorldModel.observe` - 9 edges
7. `Scene` - 9 edges
8. `generate_grounded_summary()` - 8 edges
9. `UnifiedEmbodiedAgent._warmup` - 8 edges
10. `SceneObject` - 7 edges

## Surprising Connections (you probably didn't know these)
- `loop()` --implements--> `CSV Serial Telemetry Protocol (460800 baud)`  [INFERRED]
  main.c → CLAUDE.md
- `Serial Protocol (CSV format)` --conceptually_related_to--> `classify()`  [INFERRED]
  CLAUDE.md → agent_simulator.py
- `classify()` --semantically_similar_to--> `generate_grounded_summary()`  [INFERRED] [semantically similar]
  agent_simulator.py → multimodal_agent.py
- `classify()` --semantically_similar_to--> `WorldModel._bind_audio`  [INFERRED] [semantically similar]
  agent_simulator.py → world_model.py
- `run()` --implements--> `Thread Safety Pattern (daemon threads + Queue)`  [INFERRED]
  agent_simulator.py → CLAUDE.md

## Hyperedges (group relationships)
- **Firmware telemetry pipeline** — firmware_main_c_loop, firmware_main_c_qmi8658_read_az, firmware_main_c_read_audio_sample, firmware_dsp_filter_c_dsp_get_peak_hz [EXTRACTED 1.00]
- **Serial ingestion → token queue** — sensors_data_harvester_start, sensors_data_harvester_reader_loop, sensors_data_harvester_token_queue [EXTRACTED 1.00]
- **World model perception** — perception_world_model_observe, perception_world_model_try_fast_path, perception_world_model_query_vlm, perception_object_memory_class, perception_clip_encoder_class [EXTRACTED 1.00]
- **FastAPI server handlers** — backend_server_observe, backend_server_chat, backend_server_ws_telemetry [EXTRACTED 1.00]

## Communities (41 total, 15 thin omitted)

### Community 0 - "World Model & Scene Representation"
Cohesion: 0.08
Nodes (20): AudioSource, HandPose, Scene, SceneObject, render_scene(), _freq_band(), FREQ_BANDS, _OBJECT_RE (+12 more)

### Community 1 - "Serial Hardware I/O"
Cohesion: 0.07
Nodes (35): classify(), current_directive (shared global), current_state (shared global), Dense Sticks Policy, Dry Leaves Policy, emit_directive(), last_policy (shared global), Perceive-Reason-Act Loop Pattern (+27 more)

### Community 2 - "Persistent Object Memory"
Cohesion: 0.09
Nodes (8): Open-Vocabulary Perception, Persistent Grounded World Model, ObjectCard, object_memory.py Persistent SQLite-backed multi-modal grounding store.  Each row, ObjectCard, object_memory.py Persistent SQLite-backed multi-modal grounding store.  Each row, LeCun's World Representation Argument, Data-Driven Over Hard-Coded States

### Community 3 - "World Model & Scene Representation"
Cohesion: 0.09
Nodes (14): build_chat_context(), main_gui.py Streamlit dashboard for the PIA (Physics-Informed Agents) grounded p, Scene — Persistent in-memory world state, clip_encoder.py Thin wrapper around open_clip that gives the agent a way to fing, clip_encoder.py Thin wrapper around open_clip that gives the agent a way to fing, world_map.py Render a 2D top-down iconographic map of the agent's current Scene., render_scene(), AudioSource (+6 more)

### Community 4 - "World Model & Scene Representation"
Cohesion: 0.10
Nodes (15): CameraFeed(), PHASES, hueFromLabel(), StatusBar(), TelemetryStream(), WaveformCanvas(), place(), EMA-based position and confidence interpolation (+7 more)

### Community 5 - "Backend HTTP API"
Cohesion: 0.08
Nodes (23): FastAPI backend server, dependencies, lucide-react, react, react-dom, react-markdown, remark-gfm, devDependencies (+15 more)

### Community 6 - "Telemetry WebSocket Stream"
Cohesion: 0.10
Nodes (22): current_directive, current_state, CSV Serial Telemetry Protocol (460800 baud), Producer/consumer Queue thread-safety pattern, _parse_line(), _push(), data_harvester.py Non-blocking serial reader. Runs in a daemon thread and pushes, Parse a CSV serial line into a token. Returns None on bad packet. (+14 more)

### Community 7 - "Backend HTTP API"
Cohesion: 0.12
Nodes (19): current_label, current_directive, current_distance, last_contact_ts, _build_chat_context(), chat(), _drain_queue_to_latest(), observe(), server.py Headless FastAPI backend for PIA (Physics-Informed Agents).  Ports the, Drain pending serial tokens; keep newest accel/fft/ts under lock., Same RAG context the Streamlit chat used — ports main_gui.build_chat_context. (+11 more)

### Community 8 - "Firmware & Hardware Interface"
Cohesion: 0.14
Nodes (18): CLAUDE.md (project rules), arduino-TuyaOpen framework choice, FFT size = 512 invariant, LeCun-style persistent world model, compute_hann_window(), dsp_get_peak_hz, dsp_filter_init, loop() (+10 more)

### Community 9 - "Backend HTTP API"
Cohesion: 0.13
Nodes (19): start(), Streamlit dashboard — Camera + plots + map + memory + chat, FastAPI app — REST + WebSocket backend, lifespan(), ObjectMemory — Multi-modal persistence (visual/tactile/audio per label), CLIPEncoder — ViT-B/32 frame fingerprinting, ObjectMemory — SQLite persistent store, WorldModel — VLM + CLIP dual-path perception (+11 more)

### Community 10 - "Backend HTTP API"
Cohesion: 0.13
Nodes (17): ChatRequest, ObserveRequest, BaseModel, _build_chat_context(), chat(), ChatRequest, _drain_queue_to_latest(), lifespan() (+9 more)

### Community 11 - "World Model & Scene Representation"
Cohesion: 0.12
Nodes (18): Cross-Modal Audio Binding, Dual-Path Perception (Fast + Slow), Visual Embedding (CLIP), CLIPEncoder.encode_image, Audio frequency → visible emitter binding, Scene confidence decay (half-life), Legacy one-shot VLM summary path (multimodal_agent), Strict line-format VLM prompt template (+10 more)

### Community 12 - "Vision Encoding (CLIP)"
Cohesion: 0.14
Nodes (12): host_app/multimodal_agent.py Unified Perceptual Agent: Integrates CV matrices an, Checks if ollama is running and has the model pulled., host_app/multimodal_agent.py Unified Perceptual Agent: Integrates CV matrices an, Checks if ollama is running and has the model pulled., Ingests vision frame, audio bins, and tactile forces simultaneously          to, UnifiedEmbodiedAgent._warmup, vlm_agent Session State, generate_grounded_summary() (+4 more)

### Community 13 - "Tactile Classification & Policy"
Cohesion: 0.14
Nodes (15): classify(), ContactDetector, emit_directive(), agent_simulator.py Memory-backed tactile classifier and contact-event detector., run(), Tactile bootstrap — Contact spike → hand proximity → learn signature, Token — [ts_ms, accel_g, fft_hz, frame_id] telemetry unit, dsp_get_peak_hz() — Hann + rFFT + argmax → Hz (+7 more)

### Community 14 - "Audio Frequency Analysis"
Cohesion: 0.67
Nodes (3): Arduino TuyaOpen vs TuyaOS SDK Rationale, Embodi-Align Project (CLAUDE.md), FFT Buffer = 512 Constraint

## Knowledge Gaps
- **68 isolated node(s):** `Policy`, `Policy Dataclass`, `last_policy (shared global)`, `Dry Leaves Policy`, `Dense Sticks Policy` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `render_scene()` connect `World Model & Scene Representation` to `World Model & Scene Representation`, `Telemetry WebSocket Stream`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `main_gui (Streamlit app)` connect `Telemetry WebSocket Stream` to `World Model & Scene Representation`, `Serial Hardware I/O`, `World Model & Scene Representation`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Why does `classify()` connect `Serial Hardware I/O` to `World Model & Scene Representation`, `Vision Encoding (CLIP)`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `run()` (e.g. with `Thread Safety Pattern (daemon threads + Queue)` and `Tactile Learning via Contact Events`) actually correct?**
  _`run()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `classify()` (e.g. with `Serial Protocol (CSV format)` and `generate_grounded_summary()`) actually correct?**
  _`classify()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Scene` (e.g. with `object_memory.py` and `clip_encoder.py`) actually correct?**
  _`Scene` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Policy`, `agent_simulator.py Heuristic physical agent: Perceive → Reason → Act. Classifies`, `Map sensor signatures to material state.      Signatures (from CLAUDE.md):` to the rest of the system?**
  _125 weakly-connected nodes found - possible documentation gaps or missing edges._