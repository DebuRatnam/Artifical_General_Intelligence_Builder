"""
world_model.py
LeCun-style grounded world model with persistent multi-modal memory.

What changed vs the original heuristic version:
  • FREQ_BANDS (hard-coded fan/water/voice Hz table) is gone.
  • The keyword-table audio binder (`preferred` dict) is gone.
  • Audio binding now asks the VLM, which already knows the typical Hz
    of common emitters from its training. The chosen label is then
    persisted to ObjectMemory so future bindings don't need the VLM.
  • Tactile classification + visual recognition both flow through
    ObjectMemory (SQLite), which gives the agent open-vocab persistent
    learning across sessions.
  • The VLM prompt now also asks for HAND position so the host can
    figure out which visible object a tactile contact event refers to.

The pipeline per observe():
  1. (fast)  CLIP-fingerprint frame, ask memory if we've seen this scene.
             If yes → reuse cached labels and skip the VLM call.
  2. (slow)  Otherwise → VLM lists visible objects + hand position.
  3. Each labeled object is inserted/updated in ObjectMemory (visual
     embedding EMA, description).
  4. The current FFT peak is bound to one of the visible sound-emitters
     by asking the VLM ("which of these objects produces ~N Hz?"); the
     binding is then memoised in memory.audio_freq_hz.
  5. Scene state is decayed and returned for rendering.

The T5 hardware role is unchanged: it still streams IMU + FFT over
serial. The host owns memory, CLIP, and the VLM.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from ollama import Client as OllamaClient

from perception.object_memory import ObjectMemory
from perception.clip_encoder import CLIPEncoder

# Hard wall-clock cap on any one Ollama call. Without this, a stuck
# llava runner can hang /api/observe indefinitely and the UI freezes.
# Override with PIA_VLM_TIMEOUT (seconds).
VLM_TIMEOUT_S = float(os.getenv("PIA_VLM_TIMEOUT", "25.0"))


# ── Spatial coordinate convention ─────────────────────────────────────────────
# Top-down map uses (x, y) in [0, 1]; x: 0=left → 1=right, y: 0=bottom → 1=top.

POS_X = {"left": 0.15, "center": 0.5, "right": 0.85}
POS_Y = {"bottom": 0.15, "middle": 0.5, "top": 0.85}


@dataclass
class SceneObject:
    label: str
    x: float
    y: float
    icon: str = "❓"
    confidence: float = 1.0        # displayed value = base_confidence × decay
    base_confidence: float = 1.0   # P(label is correct) at observation time
    last_seen: float = field(default_factory=time.time)


@dataclass
class AudioSource:
    label: str
    icon: str = "🔊"
    freq_hz: int = 0
    last_seen: float = field(default_factory=time.time)


# Optional hand pose pulled from the VLM. None if no hand is visible.
# Used by handle_contact() to decide which object the user is touching.
@dataclass
class HandPose:
    x: float
    y: float
    last_seen: float = field(default_factory=time.time)


@dataclass
class Scene:
    objects: dict[str, SceneObject] = field(default_factory=dict)
    audio_sources: dict[str, AudioSource] = field(default_factory=dict)
    hand: Optional[HandPose] = None
    last_summary: str = ""
    last_tactile_label: Optional[str] = None   # set by handle_contact()
    last_used_fast_path: bool = False          # CLIP hit instead of VLM

    # Age out the scene. Confidence on each SceneObject decays
    # exponentially with the given half-life; entries older than 2x
    # the half-life are dropped entirely. Called once per observe().
    def decay(self, half_life_s: float = 6.0) -> None:
        now = time.time()
        for d in (self.objects, self.audio_sources):
            stale = [k for k, v in d.items() if (now - v.last_seen) > half_life_s * 2]
            for k in stale:
                del d[k]
        for o in self.objects.values():
            age = now - o.last_seen
            decay_factor = 0.5 ** (age / half_life_s)
            o.confidence = max(0.05, o.base_confidence * decay_factor)
        if self.hand and (now - self.hand.last_seen) > half_life_s * 2:
            self.hand = None


# ── VLM prompt template ──────────────────────────────────────────────────────
# Format adds a CONFIDENCE column. Confidence is your honest P(label correct),
# NOT P(object exists). A truthful spread of values is required — see calibration
# rubric below. The host then re-weights this with an independent CLIP image-text
# similarity score so a lazy "0.99 for everything" output still gets corrected.
_PROMPT_TEMPLATE = """You are a grounded perceptual agent mapping a room.
TASK: Identify items visible in the image. Output ONLY object lines, nothing else.

EXACT FORMAT — one line per object:
- LABEL | POSITION | CONFIDENCE | EMOJI

LABEL       lowercase common noun (couch, lamp, laptop, ...). What the item IS.
POSITION    one of: top-left, top-center, top-right,
                    middle-left, middle-center, middle-right,
                    bottom-left, bottom-center, bottom-right
CONFIDENCE  float 0.00–1.00 — your honest probability that LABEL is correct
            for that item, NOT the probability an object exists there.
EMOJI       single emoji icon for the item.

CONFIDENCE CALIBRATION (HARD RULE — most outputs MUST NOT be 0.99):
  0.95–1.00 → unmistakable: full clear view, distinctive shape, no ambiguity
  0.75–0.94 → clear but partial occlusion / sub-optimal angle / muted lighting
  0.50–0.74 → recognisable shape, ambiguous between 2+ similar items
  0.30–0.49 → only a hint; suspect but not sure
  < 0.30    → DO NOT include this object at all

GOOD EXAMPLES (note varied confidences — same object, different views):
- couch         | bottom-right  | 0.91 | 🛋️
- lamp          | top-left      | 0.78 | 💡
- person        | middle-center | 0.96 | 👤
- laptop        | middle-center | 0.88 | 💻
- monitor       | top-center    | 0.93 | 🖥️
- keyboard      | bottom-center | 0.82 | ⌨️
- mouse         | bottom-right  | 0.71 | 🖱️
- phone         | middle-right  | 0.85 | 📱
- mug           | middle-left   | 0.66 | ☕
- water bottle  | bottom-left   | 0.74 | 🍶
- plate         | middle-center | 0.62 | 🍽️
- book          | bottom-left   | 0.80 | 📕
- chair         | bottom-center | 0.89 | 🪑
- desk          | middle-center | 0.87 | 🗄️
- plant         | top-right     | 0.81 | 🪴
- window        | top-left      | 0.94 | 🪟
- door          | middle-left   | 0.86 | 🚪
- fan           | top-center    | 0.83 | 💨
- speaker       | middle-right  | 0.69 | 🔈
- tv            | top-center    | 0.93 | 📺
- remote        | middle-center | 0.58 | 🎮
- backpack      | bottom-left   | 0.77 | 🎒
- shoe          | bottom-right  | 0.72 | 👟
- pen           | middle-center | 0.55 | 🖊️
- notebook      | middle-left   | 0.79 | 📓
- clock         | top-right     | 0.84 | 🕐
- mirror        | middle-right  | 0.75 | 🪞
- fridge        | bottom-left   | 0.91 | 🧊
- towel         | middle-right  | 0.61 | 🧻
- guitar        | bottom-right  | 0.86 | 🎸
- headphones    | middle-center | 0.81 | 🎧
- cable         | middle-center | 0.45 | 🔌
- bottle cap    | middle-left   | 0.42 | 🧢

BAD EXAMPLES (DO NOT emit these):
- Object        | center        | 0.99 | ❓     ← lazy default; everything ≠ 0.99
- weird thing   | top-left      | 1.00 | 📦     ← invented; no visual evidence
- "I see a small dark blob that could be ..."  ← prose, not allowed
- something     | middle-center | 0.70 | ❓     ← unsure → omit, never emit ❓
- couch         | bottom-right  | 0.91 | 🛋️
  couch         | bottom-center | 0.91 | 🛋️    ← duplicate label, not allowed

HALLUCINATION GUARDS — read before answering:
- Dark / blurry / empty image → output NOTHING. Silent is correct.
- Unsure between two labels → pick the MORE GENERAL one (bottle, not "Aquafina bottle")
  AND lower the confidence.
- Reflections, posters, screen images, paintings, and photographs of items
  are NOT the items themselves — do not list them.
- Hard cap: 5 objects. Quality over quantity. If you only see 2 clearly, output 2.
- Confidences MUST vary across your output. If every line ends in the same
  confidence you are not calibrating — re-score.
- No duplicate labels. One line per distinct visible item.
- Use only labels for items you can name. If you cannot name it confidently,
  do not include it.

For SOUND-EMITTING visible objects (OPTIONAL — only AFTER the object lines):
SOUND: LABEL | EMOJI

Telemetry hint (use ONLY to corroborate what you actually see, never to invent):
  Current audio peak: {fft_hz} Hz, vibration: {accel_g:.2f} g

BEGIN OUTPUT (object lines only, no header, no commentary):
"""

# Asked separately after object extraction so the VLM can think about
# audio binding with the candidate list already in front of it.
_AUDIO_BIND_PROMPT = """Of these visible sound-emitting objects: {names}
which ONE is most likely producing an audio peak around {fft_hz} Hz?
Reply with ONLY the exact label from the list above. No other text.
"""


# ── Parsing ───────────────────────────────────────────────────────────────────
# Strict: `- LABEL | POSITION | CONFIDENCE | EMOJI`
# Lenient fallback (legacy 4-field format without confidence) keeps older VLM
# outputs parseable; missing confidence defaults to 0.5 so CLIP calibration
# does the heavy lifting.
_OBJECT_RE = re.compile(
    r"^\s*[-*]\s*([^|]+?)\s*\|\s*(top|middle|bottom)[\s-]+(left|center|right)\s*\|\s*"
    r"([01](?:\.\d+)?|0?\.\d+)\s*\|\s*(.+?)$",
    re.IGNORECASE,
)
_OBJECT_RE_LEGACY = re.compile(
    r"^\s*[-*]\s*([^|]+?)\s*\|\s*(top|middle|bottom)[\s-]+(left|center|right)\s+(.+?)$",
    re.IGNORECASE,
)
_SOUND_RE = re.compile(
    r"^\s*SOUND\s*:\s*([^|]+?)\s*\|\s*(.+?)$",
    re.IGNORECASE,
)
_HAND_RE = re.compile(
    r"^\s*HAND\s*:\s*(top|middle|bottom)[\s-]+(left|center|right)",
    re.IGNORECASE,
)


# Line-by-line regex parse of the strict VLM output. Returns visible
# objects, sound emitters, and an optional hand pose. Unmatched lines
# are silently ignored (VLM commentary, blank lines, etc.).
def _parse_vlm_output(text: str) -> tuple[list[SceneObject], list[AudioSource], Optional[HandPose]]:
    objs: list[SceneObject] = []
    seen_labels: set[str] = set()
    sounds: list[AudioSource] = []
    hand: Optional[HandPose] = None
    for line in text.splitlines():
        m = _OBJECT_RE.match(line)
        if m:
            label = m.group(1).strip()
            v_kw  = m.group(2).lower()
            h_kw  = m.group(3).lower()
            try:
                conf = max(0.0, min(1.0, float(m.group(4))))
            except ValueError:
                conf = 0.5
            icon = m.group(5).strip()
            key = label.lower()
            if key in seen_labels:
                continue
            seen_labels.add(key)
            objs.append(SceneObject(
                label=label,
                x=POS_X.get(h_kw, 0.5),
                y=POS_Y.get(v_kw, 0.5),
                icon=icon,
                confidence=conf,
                base_confidence=conf,
            ))
            continue
        m = _OBJECT_RE_LEGACY.match(line)
        if m:
            label, v_kw, h_kw, icon = m.group(1).strip(), m.group(2).lower(), m.group(3).lower(), m.group(4).strip()
            key = label.lower()
            if key in seen_labels:
                continue
            seen_labels.add(key)
            objs.append(SceneObject(
                label=label,
                x=POS_X.get(h_kw, 0.5),
                y=POS_Y.get(v_kw, 0.5),
                icon=icon,
                confidence=0.5,
                base_confidence=0.5,
            ))
            continue
        m = _SOUND_RE.match(line)
        if m:
            sounds.append(AudioSource(label=m.group(1).strip(), icon=m.group(2).strip()))
            continue
        m = _HAND_RE.match(line)
        if m:
            v_kw, h_kw = m.group(1).lower(), m.group(2).lower()
            hand = HandPose(x=POS_X.get(h_kw, 0.5), y=POS_Y.get(v_kw, 0.5))
    return objs, sounds, hand


# Euclidean distance between two points on the [0,1] x [0,1] top-down
# map. Used to pick which visible object a hand is closest to during a
# contact event so we can bind the tactile burst to the right label.
def _xy_dist(ax: float, ay: float, bx: float, by: float) -> float:
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


# ── World Model ───────────────────────────────────────────────────────────────
class WorldModel:
    """
    Persistent grounded scene representation backed by ObjectMemory + CLIP.

    Each `observe(frame, accel_g, fft_hz)` call updates the internal Scene:
      • fast path: CLIP-fingerprint frame; if it matches a remembered scene
        well, reuse cached labels and skip the VLM call entirely.
      • slow path: VLM extracts open-vocab objects + hand pose; new labels
        are persisted to memory along with their CLIP embedding.
      • audio binding: VLM picks which visible emitter the FFT peak belongs
        to; result memoised.
      • on contact (handle_contact): the closest object to the hand gets
        its tactile signature updated. This is the bootstrap path that
        teaches the agent what each object "feels like".
    """

    # Wire up the VLM model name, the memory DB path, and a CLIP encoder.
    # vlm_force_every controls how often the slow VLM path runs even when
    # the fast CLIP path matches a remembered scene — set >0 to refresh.
    def __init__(self, model_name: str = "llava",
                 memory_path: str = "object_memory.db",
                 clip_device: str = "cpu",
                 vlm_force_every: float = 15.0):
        self.model_name = model_name
        self.scene = Scene()
        self.memory = ObjectMemory(db_path=memory_path)
        self.clip = CLIPEncoder(device=clip_device)
        self.vlm_force_every = vlm_force_every
        self._last_vlm_call = 0.0
        # Dedicated client with a hard timeout so VLM calls cannot hang
        # the request thread when llava stalls or its runner crashes.
        self._ollama = OllamaClient(timeout=VLM_TIMEOUT_S)
        self._warmup()

    # Best-effort check that the configured Ollama model is available.
    # Never raises — the first generate() call will surface a real error.
    def _warmup(self) -> None:
        try:
            self._ollama.show(self.model_name)
        except Exception:
            print(f"[WorldModel] '{self.model_name}' not pulled — run: ollama pull {self.model_name}")

    # Send the current BGR frame + telemetry to the Ollama VLM and
    # return its raw text response. Writes the frame to a temp jpeg
    # because the Ollama image API takes file paths, then deletes it.
    def _query_vlm(self, frame, accel_g: float, fft_hz: int) -> str:
        tmp = "temp_worldmodel_view.jpg"
        cv2.imwrite(tmp, frame)
        try:
            resp = self._ollama.generate(
                model=self.model_name,
                prompt=_PROMPT_TEMPLATE.format(fft_hz=fft_hz, accel_g=accel_g),
                images=[tmp],
                keep_alive="30m",
                options={
                    "num_predict": 256,   # cap output so model can't ramble
                    "temperature": 0.2,   # tighter, less hallucination
                },
            )
            self._last_vlm_call = time.time()
            return resp["response"]
        except Exception as e:
            return f"VLM_TIMEOUT_OR_ERROR ({VLM_TIMEOUT_S:.0f}s cap): {e}"
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # Ask the VLM which of the currently visible sound-emitters is most
    # likely the source of the current FFT peak. Replaces the hard-coded
    # FREQ_BANDS table. Returns the chosen label as a string (lower-cased)
    # or None if the VLM call fails / no candidates exist.
    def _vlm_bind_audio(self, fft_hz: int, candidates: list[str]) -> Optional[str]:
        if not candidates or fft_hz <= 0:
            return None
        try:
            resp = self._ollama.generate(
                model=self.model_name,
                prompt=_AUDIO_BIND_PROMPT.format(names=candidates, fft_hz=fft_hz),
                keep_alive="30m",
                options={"num_predict": 64, "temperature": 0.0},
            )
            chosen = resp["response"].strip().lower()
            for c in candidates:
                if c.lower() in chosen:
                    return c.lower()
        except Exception as e:
            print(f"[WorldModel] audio bind VLM failed: {e}")
        return None

    # Combine VLM self-confidence with an INDEPENDENT CLIP image-text
    # similarity score so we don't trust the VLM alone (it tends to anchor
    # at 0.99). Returns calibrated P(label is correct in this frame).
    #
    # Method:
    #   clip_sim   = cos(frame_emb, text_emb("a photo of a {label}"))
    #                ∈ ~[0.10, 0.40] for true matches with ViT-B/32.
    #   clip_score = clip_sim / 0.32, clamped to [0, 1]
    #                (0.32 ≈ strong match on ViT-B/32 OpenAI weights)
    #   final      = 0.5 * vlm_conf + 0.5 * clip_score
    #
    # If CLIP is disabled (no torch / open_clip), we down-weight the raw
    # VLM number by 0.85 so a sea of 0.99s still shrinks toward ~0.84 and
    # the displayed confidence reflects uncalibrated input.
    def _calibrate_confidence(self, frame_emb,
                              label: str, vlm_conf: float) -> float:
        if frame_emb is None or not self.clip.enabled:
            return round(min(1.0, vlm_conf * 0.85), 3)
        text_emb = self.clip.encode_text(f"a photo of a {label}")
        if text_emb is None:
            return round(min(1.0, vlm_conf * 0.85), 3)
        try:
            sim = float(np.dot(frame_emb, text_emb))
        except Exception:
            return round(min(1.0, vlm_conf * 0.85), 3)
        clip_score = max(0.0, min(1.0, sim / 0.32))
        blended = 0.5 * vlm_conf + 0.5 * clip_score
        return round(max(0.05, min(1.0, blended)), 3)

    # Bind a tactile spike to whichever visible object the hand is
    # nearest. Called by main_gui (or by an upstream contact-event
    # detector) when accel exceeds a threshold. Persists the (accel,
    # fft) sample to memory under that object's label so the next
    # touch can classify instantly. Returns the chosen label or None
    # if no plausible target exists.
    def handle_contact(self, accel_g: float, fft_hz: int,
                       max_dist: float = 0.25) -> Optional[str]:
        if not self.scene.objects or self.scene.hand is None:
            return None
        hx, hy = self.scene.hand.x, self.scene.hand.y
        best_label: Optional[str] = None
        best_d = float("inf")
        for key, obj in self.scene.objects.items():
            d = _xy_dist(hx, hy, obj.x, obj.y)
            if d < best_d:
                best_d, best_label = d, obj.label
        if best_label is None or best_d > max_dist:
            return None
        self.memory.update_tactile(best_label, accel_g, fft_hz)
        self.scene.last_tactile_label = best_label
        return best_label

    # Cross-modal audio binding step. Uses the VLM (not a hard-coded
    # table) to pick the best emitter, then persists the (label →
    # freq_hz) mapping to memory and to the Scene's audio_sources.
    def _bind_audio(self, fft_hz: int, observed_sounds: list[AudioSource]) -> None:
        if not observed_sounds or fft_hz <= 0:
            return
        names = [s.label for s in observed_sounds]
        chosen_lbl = self._vlm_bind_audio(fft_hz, names)
        chosen: Optional[AudioSource] = None
        if chosen_lbl:
            for s in observed_sounds:
                if s.label.lower() == chosen_lbl:
                    chosen = s
                    break
        if chosen is None:
            chosen = observed_sounds[0]

        chosen.freq_hz = fft_hz
        chosen.last_seen = time.time()
        self.scene.audio_sources[chosen.label.lower()] = chosen
        self.memory.update_audio(chosen.label, fft_hz)

        for s in observed_sounds:
            key = s.label.lower()
            if key not in self.scene.audio_sources:
                self.scene.audio_sources[key] = s

    # Reconstruct Scene.objects from a list of memory cards (used by the
    # CLIP fast path). Positions are not stored in memory, so we drop the
    # cached objects at unknown positions but flag them via confidence;
    # the next VLM call (slow path) will refresh real coordinates.
    def _scene_from_cards(self, cards: list) -> None:
        now = time.time()
        for card in cards:
            key = card.label
            if key in self.scene.objects:
                obj = self.scene.objects[key]
                obj.base_confidence = max(obj.base_confidence, 0.7)
                obj.confidence = obj.base_confidence
                obj.last_seen = now
            else:
                self.scene.objects[key] = SceneObject(
                    label=card.label, x=0.5, y=0.5, icon="❓",
                    confidence=0.6, base_confidence=0.6, last_seen=now,
                )

    # Fast-path attempt. CLIP-encode the frame, query memory for the
    # nearest known scenes/objects, and if any sit above the similarity
    # threshold, populate Scene from those cached labels and return True.
    # Returns False if CLIP is disabled, no embedding, or no match —
    # caller should then fall through to the slow VLM path.
    def _try_fast_path(self, frame) -> bool:
        if not self.clip.enabled:
            return False
        if (time.time() - self._last_vlm_call) > self.vlm_force_every:
            # Periodically force a slow path even on a fast-path hit so
            # newly-introduced objects in the scene can still be picked up.
            return False
        emb = self.clip.encode_image(frame)
        if emb is None:
            return False
        hits = self.memory.nearest_visual(emb, top_k=5, threshold=0.82)
        if not hits:
            return False
        self._scene_from_cards([c for (_, _, c) in hits])
        self.scene.last_used_fast_path = True
        self.scene.last_summary = (
            "(fast path) recognised from memory: "
            + ", ".join(lbl for (lbl, _, _) in hits)
        )
        self.scene.decay()
        return True

    # Full perception cycle. force_vlm=True skips the fast path entirely
    # (bound to the "⚡ Observe scene" button in main_gui.py so the user
    # can demand a fresh VLM look on demand).
    def observe(self, frame, accel_g: float, fft_hz: int,
                force_vlm: bool = False) -> Scene:
        if frame is None:
            self.scene.last_summary = "Vision buffer empty."
            return self.scene

        # 1. Fast path: have we seen this scene before?
        if not force_vlm and self._try_fast_path(frame):
            return self.scene

        # 2. Slow path: full VLM call.
        self.scene.last_used_fast_path = False
        raw = self._query_vlm(frame, accel_g, fft_hz)
        self.scene.last_summary = raw.strip()

        new_objs, new_sounds, hand = _parse_vlm_output(raw)
        now = time.time()

        # 3. CLIP fingerprint for memory upsert. One embedding per frame
        #    is shared across every object the VLM named in that frame —
        #    crude but workable until per-object crop/bbox extraction is
        #    added (out of scope for this hackathon iteration).
        frame_emb = self.clip.encode_image(frame) if self.clip.enabled else None

        for o in new_objs:
            key = o.label.lower()
            cal_conf = self._calibrate_confidence(frame_emb, o.label, o.base_confidence)
            existing = self.scene.objects.get(key)
            if existing:
                existing.x = 0.6 * existing.x + 0.4 * o.x
                existing.y = 0.6 * existing.y + 0.4 * o.y
                existing.icon = o.icon or existing.icon
                existing.base_confidence = cal_conf
                existing.confidence = cal_conf
                existing.last_seen = now
            else:
                o.base_confidence = cal_conf
                o.confidence = cal_conf
                self.scene.objects[key] = o
            # Persist visual + description fragment to long-term memory.
            self.memory.upsert_visual(
                label=o.label,
                embedding=frame_emb,
                description=f"icon={o.icon}",
            )

        if hand is not None:
            self.scene.hand = hand

        self._bind_audio(fft_hz, new_sounds)
        self.scene.decay()
        return self.scene

    # Drop all in-memory scene state but keep the persistent memory DB
    # intact. Bound to the "🧹 Reset world model" button in main_gui.py.
    # Use memory.forget(label) to actually erase a learned object.
    def reset(self) -> None:
        self.scene = Scene()
