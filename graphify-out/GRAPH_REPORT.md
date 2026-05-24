# Graph Report - .  (2026-05-23)

## Corpus Check
- 11 files · ~6,594 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 117 nodes · 164 edges · 10 communities (9 shown, 1 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 19 edges (avg confidence: 0.88)
- Token cost: 12,000 input · 8,000 output

## Community Hubs (Navigation)
- [[_COMMUNITY_World Model & Map Rendering|World Model & Map Rendering]]
- [[_COMMUNITY_Tactile State & Thread Plumbing|Tactile State & Thread Plumbing]]
- [[_COMMUNITY_Serial Telemetry Ingest|Serial Telemetry Ingest]]
- [[_COMMUNITY_Heuristic Tactile Classifier|Heuristic Tactile Classifier]]
- [[_COMMUNITY_Firmware DSP & Constraints|Firmware DSP & Constraints]]
- [[_COMMUNITY_VLM Parsing & Audio Binding|VLM Parsing & Audio Binding]]
- [[_COMMUNITY_Legacy Multimodal Agent|Legacy Multimodal Agent]]
- [[_COMMUNITY_Project Rationale|Project Rationale]]
- [[_COMMUNITY_Grounded Perception Concept|Grounded Perception Concept]]

## God Nodes (most connected - your core abstractions)
1. `run()` - 13 edges
2. `main_gui (Streamlit app)` - 10 edges
3. `classify()` - 9 edges
4. `_parse_vlm_output()` - 9 edges
5. `generate_grounded_summary()` - 8 edges
6. `Scene` - 7 edges
7. `Streamlit Dashboard (main_gui.py)` - 6 edges
8. `WorldModel.observe` - 6 edges
9. `CLAUDE.md (project rules)` - 6 edges
10. `loop()` - 5 edges

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
- **End-to-end CSV telemetry pipeline (firmware → host queue → consumers)** — files_main_loop, files_data_harvester_reader_loop, files_data_harvester_token_queue, files_agent_simulator_run, files_main_gui_module [INFERRED 0.95]
- **WorldModel observe cycle: query → parse → bind audio → decay** — files_world_model_observe, files_world_model_query_vlm, files_world_model_parse_vlm_output, files_world_model_bind_audio, files_world_model_decay [EXTRACTED 1.00]
- **Scene rendering chain: WorldModel.scene → render_scene → Streamlit map** — files_world_model_scene, files_world_map_render_scene, files_main_gui_module [EXTRACTED 1.00]

## Communities (10 total, 1 thin omitted)

### Community 0 - "World Model & Map Rendering"
Cohesion: 0.13
Nodes (15): world_map.py Render a 2D top-down iconographic map of the agent's current Scene., render_scene(), AudioSource, _OBJECT_RE, _parse_vlm_output(), POS_X, POS_Y, world_model.py LeCun-style grounded world model: builds and maintains a persiste (+7 more)

### Community 1 - "Tactile State & Thread Plumbing"
Cohesion: 0.12
Nodes (22): current_directive (shared global), current_state (shared global), last_policy (shared global), run(), start(), Thread Safety Pattern (daemon threads + Queue), token_queue (thread-safe Queue), current_directive (+14 more)

### Community 2 - "Serial Telemetry Ingest"
Cohesion: 0.18
Nodes (13): CSV Serial Telemetry Protocol (460800 baud), _parse_line(), _push(), data_harvester.py Non-blocking serial reader. Runs in a daemon thread and pushes, Parse a CSV serial line into a token. Returns None on bad packet., Push token to queue; drop oldest if full., Background thread: read serial, parse, push to queue., Start the serial reader as a daemon thread. Returns the thread. (+5 more)

### Community 3 - "Heuristic Tactile Classifier"
Cohesion: 0.17
Nodes (12): classify(), Dense Sticks Policy, Dry Leaves Policy, emit_directive(), Perceive-Reason-Act Loop Pattern, POLICIES Dict, Policy Dataclass, Serial Protocol (CSV format) (+4 more)

### Community 4 - "Firmware DSP & Constraints"
Cohesion: 0.23
Nodes (11): CLAUDE.md (project rules), arduino-TuyaOpen framework choice, FFT size = 512 invariant, LeCun-style persistent world model, compute_hann_window(), dsp_get_peak_hz, dsp_filter_init, loop() (+3 more)

### Community 5 - "VLM Parsing & Audio Binding"
Cohesion: 0.15
Nodes (12): Audio frequency → visible emitter binding, Scene confidence decay (half-life), Legacy one-shot VLM summary path (multimodal_agent), Strict line-format VLM prompt template, UnifiedEmbodiedAgent.generate_grounded_summary, WorldModel._bind_audio, Scene.decay, _freq_band() (+4 more)

### Community 6 - "Legacy Multimodal Agent"
Cohesion: 0.20
Nodes (10): host_app/multimodal_agent.py Unified Perceptual Agent: Integrates CV matrices an, Checks if ollama is running and has the model pulled., Ingests vision frame, audio bins, and tactile forces simultaneously          to, UnifiedEmbodiedAgent._warmup, vlm_agent Session State, generate_grounded_summary(), Late-Fusion Multi-Modal Context Pattern, Moondream VLM (Ollama) (+2 more)

### Community 7 - "Project Rationale"
Cohesion: 0.67
Nodes (3): Arduino TuyaOpen vs TuyaOS SDK Rationale, Embodi-Align Project (CLAUDE.md), FFT Buffer = 512 Constraint

## Knowledge Gaps
- **19 isolated node(s):** `Policy`, `Policy Dataclass`, `last_policy (shared global)`, `Dry Leaves Policy`, `Dense Sticks Policy` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `classify()` connect `Heuristic Tactile Classifier` to `Tactile State & Thread Plumbing`, `VLM Parsing & Audio Binding`, `Legacy Multimodal Agent`?**
  _High betweenness centrality (0.279) - this node is a cross-community bridge._
- **Why does `main_gui (Streamlit app)` connect `Tactile State & Thread Plumbing` to `World Model & Map Rendering`, `Serial Telemetry Ingest`, `VLM Parsing & Audio Binding`?**
  _High betweenness centrality (0.256) - this node is a cross-community bridge._
- **Why does `run()` connect `Tactile State & Thread Plumbing` to `Heuristic Tactile Classifier`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `classify()` (e.g. with `Serial Protocol (CSV format)` and `generate_grounded_summary()`) actually correct?**
  _`classify()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `generate_grounded_summary()` (e.g. with `classify()` and `Perceive-Reason-Act Loop Pattern`) actually correct?**
  _`generate_grounded_summary()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Policy`, `agent_simulator.py Heuristic physical agent: Perceive → Reason → Act. Classifies`, `Map sensor signatures to material state.      Signatures (from CLAUDE.md):` to the rest of the system?**
  _43 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `World Model & Map Rendering` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._