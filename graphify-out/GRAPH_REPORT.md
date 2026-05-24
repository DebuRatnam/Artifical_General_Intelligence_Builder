# Graph Report - /Users/deburatnam/Desktop/HackStorm_Hackathon/files  (2026-05-24)

## Corpus Check
- 10 files · ~12,098 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 175 nodes · 269 edges · 14 communities (12 shown, 2 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 50 edges (avg confidence: 0.81)
- Token cost: 61,746 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Vision Encoding & World Model|Vision Encoding & World Model]]
- [[_COMMUNITY_Tactile Classification & Policy|Tactile Classification & Policy]]
- [[_COMMUNITY_Thread Safety & Data Flow|Thread Safety & Data Flow]]
- [[_COMMUNITY_Persistent Object Memory|Persistent Object Memory]]
- [[_COMMUNITY_Dual-Path Perception (FastSlow)|Dual-Path Perception (Fast/Slow)]]
- [[_COMMUNITY_Serial Data Harvesting|Serial Data Harvesting]]
- [[_COMMUNITY_Firmware & Constraints|Firmware & Constraints]]
- [[_COMMUNITY_Tactile Signature Policies|Tactile Signature Policies]]
- [[_COMMUNITY_Design Rationales|Design Rationales]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]

## God Nodes (most connected - your core abstractions)
1. `run()` - 17 edges
2. `classify()` - 10 edges
3. `_parse_vlm_output()` - 10 edges
4. `main_gui (Streamlit app)` - 10 edges
5. `Scene` - 10 edges
6. `WorldModel.observe` - 9 edges
7. `generate_grounded_summary()` - 8 edges
8. `SceneObject` - 7 edges
9. `Streamlit Dashboard (main_gui.py)` - 6 edges
10. `WorldModel._bind_audio` - 6 edges

## Surprising Connections (you probably didn't know these)
- `run()` --implements--> `Thread Safety Pattern (daemon threads + Queue)`  [INFERRED]
  agent_simulator.py → CLAUDE.md
- `Serial Protocol (CSV format)` --conceptually_related_to--> `classify()`  [INFERRED]
  CLAUDE.md → agent_simulator.py
- `classify()` --semantically_similar_to--> `generate_grounded_summary()`  [INFERRED] [semantically similar]
  agent_simulator.py → multimodal_agent.py
- `Perceive-Reason-Act Loop Pattern` --semantically_similar_to--> `generate_grounded_summary()`  [INFERRED] [semantically similar]
  agent_simulator.py → multimodal_agent.py
- `UnifiedEmbodiedAgent.generate_grounded_summary` --semantically_similar_to--> `WorldModel.observe`  [INFERRED] [semantically similar]
  multimodal_agent.py → world_model.py

## Hyperedges (group relationships)
- **Perception Pipeline** — files_world_model_try_fast_path, files_world_model_query_vlm, files_world_model_observe, files_clip_encoder_encode_image [INFERRED 0.90]
- **Object Memory Learning Cycle** — files_object_memory_update_tactile, files_object_memory_update_audio, files_object_memory_upsert_visual, files_object_memory_nearest_visual [INFERRED 0.85]
- **Tactile Contact Detection & Bootstrap** — files_agent_simulator_run, files_contact_detector_step, files_world_model_handle_contact, files_object_memory_update_tactile [EXTRACTED 1.00]

## Communities (14 total, 2 thin omitted)

### Community 0 - "Vision Encoding & World Model"
Cohesion: 0.08
Nodes (23): Persistent Grounded World Model, AudioSource, clip_encoder.py Thin wrapper around open_clip that gives the agent a way to fing, HandPose, Scene, SceneObject, world_map.py Render a 2D top-down iconographic map of the agent's current Scene., render_scene() (+15 more)

### Community 1 - "Tactile Classification & Policy"
Cohesion: 0.12
Nodes (20): emit_directive(), last_policy (shared global), Perceive-Reason-Act Loop Pattern, Policy Dataclass, run(), start(), Tactile Learning via Contact Events, current_directive (+12 more)

### Community 2 - "Thread Safety & Data Flow"
Cohesion: 0.10
Nodes (20): current_directive (shared global), current_state (shared global), Thread Safety Pattern (daemon threads + Queue), token_queue (thread-safe Queue), host_app/multimodal_agent.py Unified Perceptual Agent: Integrates CV matrices an, Checks if ollama is running and has the model pulled., Ingests vision frame, audio bins, and tactile forces simultaneously          to, UnifiedEmbodiedAgent._warmup (+12 more)

### Community 3 - "Persistent Object Memory"
Cohesion: 0.18
Nodes (4): Open-Vocabulary Perception, ObjectCard, object_memory.py Persistent SQLite-backed multi-modal grounding store.  Each row, Data-Driven Over Hard-Coded States

### Community 4 - "Dual-Path Perception (Fast/Slow)"
Cohesion: 0.12
Nodes (17): Dual-Path Perception (Fast + Slow), Visual Embedding (CLIP), CLIPEncoder.encode_image, Scene confidence decay (half-life), Legacy one-shot VLM summary path (multimodal_agent), Strict line-format VLM prompt template, UnifiedEmbodiedAgent.generate_grounded_summary, ObjectMemory.nearest_visual (+9 more)

### Community 5 - "Serial Data Harvesting"
Cohesion: 0.16
Nodes (13): _push(), data_harvester.py Non-blocking serial reader. Runs in a daemon thread and pushes, Push token to queue; drop oldest if full., Background thread: read serial, parse, push to queue., Start the serial reader as a daemon thread. Returns the thread., Inject synthetic tokens at a fixed rate for testing without hardware., _reader_loop(), start() (+5 more)

### Community 6 - "Firmware & Constraints"
Cohesion: 0.18
Nodes (14): CLAUDE.md (project rules), arduino-TuyaOpen framework choice, FFT size = 512 invariant, LeCun-style persistent world model, CSV Serial Telemetry Protocol (460800 baud), _parse_line(), Parse a CSV serial line into a token. Returns None on bad packet., compute_hann_window() (+6 more)

### Community 7 - "Tactile Signature Policies"
Cohesion: 0.17
Nodes (12): classify(), Dense Sticks Policy, Dry Leaves Policy, POLICIES Dict, Serial Protocol (CSV format), Cross-Modal Audio Binding, Classifies organic materials based on vibrational friction (g-force)     and aco, Map sensor signatures to material state.      Signatures (from CLAUDE.md): (+4 more)

### Community 8 - "Design Rationales"
Cohesion: 0.67
Nodes (3): Arduino TuyaOpen vs TuyaOS SDK Rationale, Embodi-Align Project (CLAUDE.md), FFT Buffer = 512 Constraint

## Knowledge Gaps
- **24 isolated node(s):** `Policy`, `Policy Dataclass`, `last_policy (shared global)`, `Dry Leaves Policy`, `Dense Sticks Policy` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `classify()` connect `Tactile Signature Policies` to `Tactile Classification & Policy`, `Thread Safety & Data Flow`?**
  _High betweenness centrality (0.211) - this node is a cross-community bridge._
- **Why does `run()` connect `Tactile Classification & Policy` to `Thread Safety & Data Flow`, `Tactile Signature Policies`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Why does `WorldModel.observe` connect `Dual-Path Perception (Fast/Slow)` to `Vision Encoding & World Model`, `Tactile Classification & Policy`, `Tactile Signature Policies`?**
  _High betweenness centrality (0.132) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `run()` (e.g. with `Thread Safety Pattern (daemon threads + Queue)` and `Tactile Learning via Contact Events`) actually correct?**
  _`run()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `classify()` (e.g. with `Serial Protocol (CSV format)` and `generate_grounded_summary()`) actually correct?**
  _`classify()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Scene` (e.g. with `object_memory.py` and `clip_encoder.py`) actually correct?**
  _`Scene` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Policy`, `agent_simulator.py Heuristic physical agent: Perceive → Reason → Act. Classifies`, `Map sensor signatures to material state.      Signatures (from CLAUDE.md):` to the rest of the system?**
  _54 weakly-connected nodes found - possible documentation gaps or missing edges._