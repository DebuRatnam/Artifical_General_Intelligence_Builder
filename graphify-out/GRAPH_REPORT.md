# Graph Report - .  (2026-05-24)

## Corpus Check
- 23 files · ~18,456 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 431 nodes · 627 edges · 37 communities (25 shown, 12 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 85 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]

## God Nodes (most connected - your core abstractions)
1. `run()` - 17 edges
2. `WorldModel — VLM + CLIP dual-path perception` - 13 edges
3. `classify()` - 10 edges
4. `_parse_vlm_output()` - 10 edges
5. `main_gui (Streamlit app)` - 10 edges
6. `Scene` - 10 edges
7. `UnifiedEmbodiedAgent._warmup` - 9 edges
8. `WorldModel.observe` - 9 edges
9. `run()` - 9 edges
10. `Scene` - 9 edges

## Surprising Connections (you probably didn't know these)
- `run()` --implements--> `Thread Safety Pattern (daemon threads + Queue)`  [INFERRED]
  agent_simulator.py → CLAUDE.md
- `Serial Protocol (CSV format)` --conceptually_related_to--> `classify()`  [INFERRED]
  CLAUDE.md → agent_simulator.py
- `classify()` --semantically_similar_to--> `generate_grounded_summary()`  [INFERRED] [semantically similar]
  agent_simulator.py → multimodal_agent.py
- `classify()` --semantically_similar_to--> `WorldModel._bind_audio`  [INFERRED] [semantically similar]
  agent_simulator.py → world_model.py
- `Perceive-Reason-Act Loop Pattern` --semantically_similar_to--> `generate_grounded_summary()`  [INFERRED] [semantically similar]
  agent_simulator.py → multimodal_agent.py

## Hyperedges (group relationships)
- **Sensor Ingestion Pipeline** — firmware_main_loop, sensors_data_harvester_reader_loop, sensors_data_harvester_parse_line [EXTRACTED 1.00]
- **Audio DSP Processing Chain** — firmware_main_read_audio_sample, firmware_dsp_compute_hann_window, firmware_dsp_get_peak_hz, firmware_main_loop [EXTRACTED 1.00]
- **Tactile Memory and Inference** — agents_agent_simulator_classify, perception_object_memory_nearest_tactile, perception_object_memory_update_tactile [EXTRACTED 1.00]
- **Multimodal Object Memory System** — perception_object_memory_object_card, perception_object_memory_upsert_visual, perception_object_memory_update_tactile, perception_object_memory_update_audio, perception_clip_encoder_encode_image [INFERRED 0.85]
- **Camera capture workflow** — frontend_camerafeed_component, frontend_camerafeed_getusermediacall, backend_server_camera_capture, perception_world_model_observe_method [INFERRED 0.85]
- **Complete perception pipeline** — perception_world_model_observe_method, perception_world_model_clip_fast_path, perception_world_model_vlm_binding, perception_world_model_scene_dataclass, perception_world_model_object_memory [EXTRACTED 1.00]
- **2D world map rendering pipeline** — perception_world_map_render, perception_world_map_objects_layer, perception_world_map_audio_strip, frontend_worldmap_component, frontend_worldmap_rendering [EXTRACTED 1.00]
- **Backend REST + WebSocket API surface** — backend_server_api, backend_server_observe_endpoint, backend_server_chat_endpoint, backend_server_memory_endpoint, backend_server_ws_telemetry [EXTRACTED 1.00]
- **Legacy Streamlit dashboard panels** — backend_main_gui_streamlit, backend_main_gui_camera_panel, backend_main_gui_world_map_panel, backend_main_gui_chat_panel, backend_main_gui_memory_inspector [EXTRACTED 1.00]
- **Persistent scene representation** — perception_world_model_scene_dataclass, perception_world_model_sceneobject, perception_world_model_audiosource, perception_world_model_handpose [EXTRACTED 1.00]

## Communities (37 total, 12 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (31): Open-Vocabulary Perception, Persistent Grounded World Model, Scene — Persistent in-memory world state, AudioSource, clip_encoder.py Thin wrapper around open_clip that gives the agent a way to fing, HandPose, Scene, SceneObject (+23 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (41): classify(), Dense Sticks Policy, Dry Leaves Policy, emit_directive(), last_policy (shared global), Perceive-Reason-Act Loop Pattern, POLICIES Dict, Policy Dataclass (+33 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (7): ObjectCard, object_memory.py Persistent SQLite-backed multi-modal grounding store.  Each row, nearest_tactile() — Mahalanobis σ-gating, ObjectCard, object_memory.py Persistent SQLite-backed multi-modal grounding store.  Each row, update_audio() — EMA-update freq_hz, _vlm_bind_audio() — VLM picks emitter for FFT peak

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (29): current_label, current_directive, current_distance, last_contact_ts, _build_chat_context(), chat(), ChatRequest, _drain_queue_to_latest(), observe(), ObserveRequest, server.py Headless FastAPI backend for PIA (Physics-Informed Agents).  Ports the (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (31): build_chat_context(), Egocentric camera feed panel, Grounded chat interface, ObjectMemory DataFrame inspector, main_gui.py Streamlit dashboard for the PIA (Physics-Informed Agents) grounded p, Streamlit dashboard — Camera + plots + map + memory + chat, 2D world map rendering panel, FastAPI backend application (+23 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (15): CameraFeed(), PHASES, hueFromLabel(), StatusBar(), TelemetryStream(), WaveformCanvas(), place(), EMA-based position and confidence interpolation (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (23): current_directive (shared global), current_state (shared global), generate_grounded_summary() — Fused vision+audio+tactile prompt, host_app/multimodal_agent.py Unified Perceptual Agent: Integrates CV matrices an, Checks if ollama is running and has the model pulled., Thread Safety Pattern (daemon threads + Queue), token_queue (thread-safe Queue), host_app/multimodal_agent.py Unified Perceptual Agent: Integrates CV matrices an (+15 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (23): FastAPI backend server, dependencies, lucide-react, react, react-dom, react-markdown, remark-gfm, devDependencies (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (21): CLAUDE.md (project rules), arduino-TuyaOpen framework choice, FFT size = 512 invariant, LeCun-style persistent world model, CSV Serial Telemetry Protocol (460800 baud), _parse_line(), Parse a CSV serial line into a token. Returns None on bad packet., compute_hann_window() (+13 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (21): Cross-Modal Audio Binding, Dual-Path Perception (Fast + Slow), Visual Embedding (CLIP), CLIPEncoder.encode_image, Audio frequency → visible emitter binding, Scene confidence decay (half-life), Legacy one-shot VLM summary path (multimodal_agent), Strict line-format VLM prompt template (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (21): cv2.VideoCapture camera integration, lifespan(), Token — [ts_ms, accel_g, fft_hz, frame_id] telemetry unit, dsp_get_peak_hz() — Hann + rFFT + argmax → Hz, loop() — Audio fill → FFT → serial TX, qmi8658_read_az() — I2C read Z-axis accel, read_audio_sample() — 12-bit ADC sample, CameraFeed React Component (+13 more)

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (17): Spatial coordinate system [0,1], Dual-path perception — Fast CLIP + slow VLM, Audio source annotation strip, Scene object rendering with EMA smoothing, encode_image() — BGR frame → 512-d unit vector, nearest_visual() — Cosine search (CLIP), upsert_visual() — EMA-merge visual embedding, Scene objects emoji marker layer (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.26
Nodes (9): classify(), ContactDetector, emit_directive(), agent_simulator.py Memory-backed tactile classifier and contact-event detector., run(), start(), Tactile bootstrap — Contact spike → hand proximity → learn signature, update_tactile() — EMA-accumulate accel/fft mean/std (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.67
Nodes (3): Arduino TuyaOpen vs TuyaOS SDK Rationale, Embodi-Align Project (CLAUDE.md), FFT Buffer = 512 Constraint

## Knowledge Gaps
- **69 isolated node(s):** `Policy`, `Policy Dataclass`, `last_policy (shared global)`, `Dry Leaves Policy`, `Dense Sticks Policy` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `render_scene()` connect `Community 0` to `Community 1`, `Community 5`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **Why does `lifespan()` connect `Community 10` to `Community 0`, `Community 3`, `Community 12`, `Community 4`?**
  _High betweenness centrality (0.149) - this node is a cross-community bridge._
- **Why does `classify()` connect `Community 1` to `Community 9`, `Community 6`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `run()` (e.g. with `Thread Safety Pattern (daemon threads + Queue)` and `Tactile Learning via Contact Events`) actually correct?**
  _`run()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `classify()` (e.g. with `Serial Protocol (CSV format)` and `generate_grounded_summary()`) actually correct?**
  _`classify()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Policy`, `agent_simulator.py Heuristic physical agent: Perceive → Reason → Act. Classifies`, `Map sensor signatures to material state.      Signatures (from CLAUDE.md):` to the rest of the system?**
  _130 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.051203277009728626 - nodes in this community are weakly interconnected._