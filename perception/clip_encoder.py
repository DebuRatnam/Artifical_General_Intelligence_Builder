"""
clip_encoder.py
Thin wrapper around open_clip that gives the agent a way to fingerprint
a camera frame (or a piece of text) as a 512-d unit vector.

The vectors are what ObjectMemory.upsert_visual stores and what
ObjectMemory.nearest_visual searches. Encoding is ~50ms on CPU for
ViT-B/32 — fast enough to run every observe cycle without blocking
the GUI, in contrast to the 1-3s VLM call.

If open_clip / torch aren't installed, the wrapper degrades to a
no-op encoder that returns None. The rest of the stack handles None
visual_embedding gracefully (memory still stores tactile + audio, the
VLM still labels new scenes — you just lose the fast vision shortcut).
"""

from __future__ import annotations

from typing import Optional

import numpy as np


# Loads open_clip lazily so that importing this module is cheap and so
# the rest of the system still runs if the optional dependency is
# missing. enabled=False after a failed init makes encode_* return None.
class CLIPEncoder:
    # Pick model + pretrained checkpoint and device. Defaults to the
    # ViT-B/32 OpenAI weights — 150MB, ~50ms/CPU encode, 512-d output.
    # device="cpu" works everywhere; switch to "cuda"/"mps" if available.
    def __init__(self, model_name: str = "ViT-B-32",
                 pretrained: str = "openai", device: str = "cpu"):
        self.model_name = model_name
        self.pretrained = pretrained
        self.device = device
        self.enabled = False
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._torch = None
        self._load()

    # Best-effort import + model load. Sets enabled=True on success.
    # Failures (missing dep, missing weights, no internet) are swallowed
    # so the agent still boots; a one-line hint is printed for the user.
    def _load(self) -> None:
        try:
            import torch  # type: ignore
            import open_clip  # type: ignore
        except ImportError:
            print("[clip] open_clip / torch not installed — fast vision path disabled. "
                  "pip install open-clip-torch torch  to enable.")
            return

        try:
            model, _, preprocess = open_clip.create_model_and_transforms(
                self.model_name, pretrained=self.pretrained, device=self.device,
            )
            model.eval()
            self._model = model
            self._preprocess = preprocess
            self._tokenizer = open_clip.get_tokenizer(self.model_name)
            self._torch = torch
            self.enabled = True
        except Exception as e:
            print(f"[clip] failed to load {self.model_name}/{self.pretrained}: {e}")

    # Encode a BGR OpenCV frame to a normalised 512-d vector. Returns
    # None if CLIP is disabled or the encode raises (e.g. bad frame).
    # The vector is unit-length, so cosine == dot product downstream.
    def encode_image(self, frame_bgr) -> Optional[np.ndarray]:
        if not self.enabled or frame_bgr is None:
            return None
        try:
            import cv2
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            from PIL import Image  # PIL is a transitive dep of open_clip.
            pil = Image.fromarray(rgb)
            tensor = self._preprocess(pil).unsqueeze(0).to(self.device)
            with self._torch.no_grad():
                feat = self._model.encode_image(tensor)
                feat = feat / feat.norm(dim=-1, keepdim=True)
            return feat.cpu().numpy().astype(np.float32).flatten()
        except Exception as e:
            print(f"[clip] encode_image failed: {e}")
            return None

    # Encode a text string to the same 512-d shared space. Useful for
    # "find me the orange" text-to-image retrieval over the memory DB
    # without ever calling the VLM.
    def encode_text(self, text: str) -> Optional[np.ndarray]:
        if not self.enabled or not text:
            return None
        try:
            tokens = self._tokenizer([text]).to(self.device)
            with self._torch.no_grad():
                feat = self._model.encode_text(tokens)
                feat = feat / feat.norm(dim=-1, keepdim=True)
            return feat.cpu().numpy().astype(np.float32).flatten()
        except Exception as e:
            print(f"[clip] encode_text failed: {e}")
            return None
