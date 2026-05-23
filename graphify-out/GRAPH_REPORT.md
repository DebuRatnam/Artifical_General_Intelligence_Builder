# Graph Report - .  (2026-05-23)

## Corpus Check
- 5 files · ~3,070 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 66 nodes · 83 edges · 7 communities
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 7 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Heuristic PRA Policy Engine|Heuristic PRA Policy Engine]]
- [[_COMMUNITY_Serial Data Harvester|Serial Data Harvester]]
- [[_COMMUNITY_Multimodal VLM Agent|Multimodal VLM Agent]]
- [[_COMMUNITY_Thread-Safe State & Queue|Thread-Safe State & Queue]]
- [[_COMMUNITY_DSP  FFT Firmware|DSP / FFT Firmware]]
- [[_COMMUNITY_Material Policy Configs|Material Policy Configs]]
- [[_COMMUNITY_Project Architecture Rationale|Project Architecture Rationale]]

## God Nodes (most connected - your core abstractions)
1. `run()` - 9 edges
2. `classify()` - 8 edges
3. `generate_grounded_summary()` - 8 edges
4. `Streamlit Dashboard (main_gui.py)` - 6 edges
5. `_warmup()` - 5 edges
6. `loop()` - 4 edges
7. `_reader_loop()` - 4 edges
8. `UnifiedEmbodiedAgent` - 4 edges
9. `emit_directive()` - 4 edges
10. `start()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `run()` --implements--> `Thread Safety Pattern (daemon threads + Queue)`  [INFERRED]
  agent_simulator.py → CLAUDE.md
- `Serial Protocol (CSV format)` --conceptually_related_to--> `classify()`  [INFERRED]
  CLAUDE.md → agent_simulator.py
- `classify()` --semantically_similar_to--> `generate_grounded_summary()`  [INFERRED] [semantically similar]
  agent_simulator.py → multimodal_agent.py
- `Perceive-Reason-Act Loop Pattern` --semantically_similar_to--> `generate_grounded_summary()`  [INFERRED] [semantically similar]
  agent_simulator.py → multimodal_agent.py
- `Camera Feed (OpenCV capture)` --shares_data_with--> `generate_grounded_summary()`  [INFERRED]
  main_gui.py → multimodal_agent.py

## Hyperedges (group relationships)
- **Multi-Modal Sensor Fusion Pipeline** — main_gui_trigger_sensory_alignment, multimodal_agent_generate_grounded_summary, agent_simulator_classify [EXTRACTED 0.95]
- **Thread-Safe Producer-Consumer Pattern** — claude_md_token_queue, agent_simulator_run, main_gui_token_queue_consumer [EXTRACTED 0.95]
- **Perceive-Reason-Act Architecture** — agent_simulator_classify, agent_simulator_emit_directive, agent_simulator_run [EXTRACTED 1.00]

## Communities (7 total, 0 thin omitted)

### Community 0 - "Heuristic PRA Policy Engine"
Cohesion: 0.17
Nodes (14): classify(), emit_directive(), last_policy (shared global), Perceive-Reason-Act Loop Pattern, Policy Dataclass, run(), start(), Serial Protocol (CSV format) (+6 more)

### Community 1 - "Serial Data Harvester"
Cohesion: 0.18
Nodes (12): _parse_line(), _push(), data_harvester.py Non-blocking serial reader. Runs in a daemon thread and pushes, Parse a CSV serial line into a token. Returns None on bad packet., Push token to queue; drop oldest if full., Background thread: read serial, parse, push to queue., Start the serial reader as a daemon thread. Returns the thread., Inject synthetic tokens at a fixed rate for testing without hardware. (+4 more)

### Community 2 - "Multimodal VLM Agent"
Cohesion: 0.20
Nodes (10): host_app/multimodal_agent.py Unified Perceptual Agent: Integrates CV matrices an, Checks if ollama is running and has the model pulled., Ingests vision frame, audio bins, and tactile forces simultaneously          to, UnifiedEmbodiedAgent, vlm_agent Session State, generate_grounded_summary(), Late-Fusion Multi-Modal Context Pattern, Moondream VLM (Ollama) (+2 more)

### Community 3 - "Thread-Safe State & Queue"
Cohesion: 0.20
Nodes (10): current_directive (shared global), current_state (shared global), Thread Safety Pattern (daemon threads + Queue), token_queue (thread-safe Queue), Camera Feed (OpenCV capture), Rolling Deque Buffers (accel/fft/ts), STATE_COLORS Map, Streamlit Dashboard (main_gui.py) (+2 more)

### Community 4 - "DSP / FFT Firmware"
Cohesion: 0.36
Nodes (7): compute_hann_window(), dsp_filter_init(), dsp_get_peak_hz(), loop(), qmi8658_read_az(), read_audio_sample(), setup()

### Community 5 - "Material Policy Configs"
Cohesion: 0.67
Nodes (3): Dense Sticks Policy, Dry Leaves Policy, POLICIES Dict

### Community 6 - "Project Architecture Rationale"
Cohesion: 0.67
Nodes (3): Arduino TuyaOpen vs TuyaOS SDK Rationale, Embodi-Align Project (CLAUDE.md), FFT Buffer = 512 Constraint

## Knowledge Gaps
- **9 isolated node(s):** `Policy`, `Policy Dataclass`, `last_policy (shared global)`, `Dry Leaves Policy`, `Dense Sticks Policy` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `classify()` connect `Heuristic PRA Policy Engine` to `Multimodal VLM Agent`, `Material Policy Configs`?**
  _High betweenness centrality (0.291) - this node is a cross-community bridge._
- **Why does `generate_grounded_summary()` connect `Multimodal VLM Agent` to `Heuristic PRA Policy Engine`, `Thread-Safe State & Queue`?**
  _High betweenness centrality (0.254) - this node is a cross-community bridge._
- **Why does `run()` connect `Heuristic PRA Policy Engine` to `Thread-Safe State & Queue`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `classify()` (e.g. with `Serial Protocol (CSV format)` and `generate_grounded_summary()`) actually correct?**
  _`classify()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `generate_grounded_summary()` (e.g. with `classify()` and `Perceive-Reason-Act Loop Pattern`) actually correct?**
  _`generate_grounded_summary()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Policy`, `agent_simulator.py Heuristic physical agent: Perceive → Reason → Act. Classifies`, `Map sensor signatures to material state.      Signatures (from CLAUDE.md):` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._