"""
object_memory.py
Persistent SQLite-backed multi-modal grounding store.

Each row = one ObjectCard binding a label to its learned modalities:
  • visual_embedding  (CLIP/SigLIP vector, EMA-updated)
  • tactile signature (accel + fft running mean/std)
  • audio signature   (FFT peak Hz)
  • description text  (free-form VLM caption captured on first sighting)

This is the agent's long-term memory. The VLM is a slow oracle; this DB
is the fast index that turns every "have I touched/seen this before?"
question into a numpy dot product instead of a 1-3s VLM call.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


_EMBED_DIM = 512  # ViT-B/32 from open_clip outputs 512-d.


# Per-object record. One row in SQLite. Mutable in-Python; persisted by
# ObjectMemory.upsert_* methods. None visual_embedding means we know the
# label (via VLM) but haven't captured a vision embedding yet.
@dataclass
class ObjectCard:
    label: str
    visual_embedding: Optional[np.ndarray] = None
    tactile_accel_mean: float = 0.0
    tactile_accel_std: float = 0.0
    tactile_fft_mean: float = 0.0
    tactile_fft_std: float = 0.0
    audio_freq_hz: int = 0
    description: str = ""
    n_visual: int = 0
    n_tactile: int = 0
    n_audio: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    # Cheap maturity gate. Below this, the tactile signature is too
    # noisy to use for classification — only good for accumulation.
    @property
    def tactile_trained(self) -> bool:
        return self.n_tactile >= 5


# SQLite-backed object memory. One file (default object_memory.db) holds
# every object the agent has ever seen/touched/heard. Vector search is
# brute-force cosine in numpy — fine up to ~10k entries on a laptop and
# avoids a FAISS/sqlite-vec dependency for the demo.
class ObjectMemory:
    # Open or create the DB at db_path. Creates the schema if absent.
    # alpha is the EMA mixing weight for tactile/visual updates: higher
    # → faster adaptation, lower → smoother but slower to learn.
    def __init__(self, db_path: str = "object_memory.db", alpha: float = 0.2):
        self.db_path = db_path
        self.alpha = alpha
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    # Idempotent schema creation. Called from __init__; safe to re-run.
    def _create_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                label              TEXT PRIMARY KEY,
                visual_embedding   BLOB,
                tactile_accel_mean REAL DEFAULT 0,
                tactile_accel_std  REAL DEFAULT 0,
                tactile_fft_mean   REAL DEFAULT 0,
                tactile_fft_std    REAL DEFAULT 0,
                audio_freq_hz      INTEGER DEFAULT 0,
                description        TEXT DEFAULT '',
                n_visual           INTEGER DEFAULT 0,
                n_tactile          INTEGER DEFAULT 0,
                n_audio            INTEGER DEFAULT 0,
                first_seen         REAL,
                last_seen          REAL
            )
        """)
        self._conn.commit()

    # Row → ObjectCard adapter. Handles the BLOB → numpy decode.
    def _row_to_card(self, row: tuple) -> ObjectCard:
        (label, emb_blob, ta_m, ta_s, tf_m, tf_s, af, desc,
         nv, nt, na, fs, ls) = row
        embedding = None
        if emb_blob is not None:
            embedding = np.frombuffer(emb_blob, dtype=np.float32).copy()
        return ObjectCard(
            label=label,
            visual_embedding=embedding,
            tactile_accel_mean=ta_m, tactile_accel_std=ta_s,
            tactile_fft_mean=tf_m, tactile_fft_std=tf_s,
            audio_freq_hz=af, description=desc,
            n_visual=nv, n_tactile=nt, n_audio=na,
            first_seen=fs, last_seen=ls,
        )

    # Fetch one card by exact label match, or None if absent.
    def get(self, label: str) -> Optional[ObjectCard]:
        key = label.strip().lower()
        cur = self._conn.execute("SELECT * FROM objects WHERE label=?", (key,))
        row = cur.fetchone()
        return self._row_to_card(row) if row else None

    # Return every card in the DB. Used for brute-force visual search and
    # for serialising scene context into the chat LLM prompt.
    def all(self) -> list[ObjectCard]:
        cur = self._conn.execute("SELECT * FROM objects")
        return [self._row_to_card(r) for r in cur.fetchall()]

    # Insert a new row with a fresh label. Sets first_seen=last_seen=now.
    # description is optional; embedding is optional (text-only seed OK).
    def _insert(self, label: str, embedding: Optional[np.ndarray],
                description: str) -> ObjectCard:
        now = time.time()
        emb_blob = embedding.astype(np.float32).tobytes() if embedding is not None else None
        self._conn.execute("""
            INSERT INTO objects (label, visual_embedding, description,
                                 n_visual, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (label, emb_blob, description, 1 if embedding is not None else 0, now, now))
        self._conn.commit()
        return ObjectCard(
            label=label, visual_embedding=embedding, description=description,
            n_visual=1 if embedding is not None else 0,
            first_seen=now, last_seen=now,
        )

    # Insert if new; otherwise EMA-update the visual embedding and merge
    # description. Returns the up-to-date card. Use this every time the
    # VLM names an object and we have a CLIP vector for the frame.
    def upsert_visual(self, label: str, embedding: Optional[np.ndarray] = None,
                      description: str = "") -> ObjectCard:
        key = label.strip().lower()
        card = self.get(key)
        if card is None:
            return self._insert(key, embedding, description)

        # Update existing
        if embedding is not None:
            if card.visual_embedding is None:
                merged = embedding.astype(np.float32)
            else:
                merged = (1 - self.alpha) * card.visual_embedding + self.alpha * embedding
                # Renormalise so cosine stays comparable.
                norm = np.linalg.norm(merged) or 1.0
                merged = (merged / norm).astype(np.float32)
            card.visual_embedding = merged
            card.n_visual += 1

        if description and not card.description:
            card.description = description

        card.last_seen = time.time()
        self._conn.execute("""
            UPDATE objects SET
                visual_embedding=?, description=?, n_visual=?, last_seen=?
            WHERE label=?
        """, (
            card.visual_embedding.tobytes() if card.visual_embedding is not None else None,
            card.description, card.n_visual, card.last_seen, key,
        ))
        self._conn.commit()
        return card

    # Push one (accel, fft) sample into the tactile signature for label.
    # Uses EMA for the mean and an EMA-on-absdev approximation for the
    # std (good enough for a 2.5σ nearest-neighbour gate).
    def update_tactile(self, label: str, accel: float, fft: float) -> ObjectCard:
        key = label.strip().lower()
        card = self.get(key) or self._insert(key, None, "")

        if card.n_tactile == 0:
            card.tactile_accel_mean = accel
            card.tactile_fft_mean = fft
        else:
            a = self.alpha
            card.tactile_accel_mean = (1 - a) * card.tactile_accel_mean + a * accel
            card.tactile_fft_mean   = (1 - a) * card.tactile_fft_mean   + a * fft
            card.tactile_accel_std = (1 - a) * card.tactile_accel_std + a * abs(accel - card.tactile_accel_mean)
            card.tactile_fft_std   = (1 - a) * card.tactile_fft_std   + a * abs(fft   - card.tactile_fft_mean)
        card.n_tactile += 1
        card.last_seen = time.time()

        self._conn.execute("""
            UPDATE objects SET
                tactile_accel_mean=?, tactile_accel_std=?,
                tactile_fft_mean=?,   tactile_fft_std=?,
                n_tactile=?, last_seen=?
            WHERE label=?
        """, (
            card.tactile_accel_mean, card.tactile_accel_std,
            card.tactile_fft_mean,   card.tactile_fft_std,
            card.n_tactile, card.last_seen, key,
        ))
        self._conn.commit()
        return card

    # Record an audio FFT peak Hz for label. Uses a simple EMA over the
    # integer peak — sufficient because the freq band of a given source
    # is much narrower than the full audible spectrum.
    def update_audio(self, label: str, freq_hz: int) -> ObjectCard:
        key = label.strip().lower()
        card = self.get(key) or self._insert(key, None, "")
        if card.n_audio == 0:
            card.audio_freq_hz = freq_hz
        else:
            a = self.alpha
            card.audio_freq_hz = int((1 - a) * card.audio_freq_hz + a * freq_hz)
        card.n_audio += 1
        card.last_seen = time.time()
        self._conn.execute("""
            UPDATE objects SET audio_freq_hz=?, n_audio=?, last_seen=? WHERE label=?
        """, (card.audio_freq_hz, card.n_audio, card.last_seen, key))
        self._conn.commit()
        return card

    # Visual nearest-neighbour search. Returns the top_k closest cards
    # whose cosine similarity is at least threshold. Brute-force is fine
    # for <10k entries; switch to FAISS if/when the cache grows past that.
    def nearest_visual(self, embedding: np.ndarray, top_k: int = 3,
                       threshold: float = 0.75) -> list[tuple[str, float, ObjectCard]]:
        if embedding is None:
            return []
        q = embedding.astype(np.float32)
        q_norm = np.linalg.norm(q) or 1.0
        q = q / q_norm

        hits: list[tuple[str, float, ObjectCard]] = []
        for card in self.all():
            if card.visual_embedding is None:
                continue
            sim = float(np.dot(q, card.visual_embedding))
            if sim >= threshold:
                hits.append((card.label, sim, card))
        hits.sort(key=lambda x: x[1], reverse=True)
        return hits[:top_k]

    # Tactile nearest-neighbour. For each trained card, compute a
    # per-feature standardised distance (Mahalanobis-ish) and pick the
    # closest. Returns (label, distance) or None if no signature is
    # within max_sigma. Caller decides what "close enough" means.
    def nearest_tactile(self, accel: float, fft: float,
                        max_sigma: float = 2.5) -> Optional[tuple[str, float]]:
        best: Optional[tuple[str, float]] = None
        for card in self.all():
            if not card.tactile_trained:
                continue
            da = (accel - card.tactile_accel_mean) / max(card.tactile_accel_std, 0.05)
            df = (fft   - card.tactile_fft_mean)   / max(card.tactile_fft_std,   20.0)
            d = float((da * da + df * df) ** 0.5)
            if d <= max_sigma and (best is None or d < best[1]):
                best = (card.label, d)
        return best

    # Remove a label entirely. Used by the UI "forget this object" path
    # for cleaning up bad VLM hallucinations from polluting the cache.
    def forget(self, label: str) -> None:
        key = label.strip().lower()
        self._conn.execute("DELETE FROM objects WHERE label=?", (key,))
        self._conn.commit()

    # Close the SQLite handle. Safe to call repeatedly. Streamlit doesn't
    # call this explicitly but the WAL journal mode keeps things sane.
    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
