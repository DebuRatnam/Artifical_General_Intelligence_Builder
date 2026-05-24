"""
agent_simulator.py
Memory-backed tactile classifier and contact-event detector.

What changed vs the original heuristic version:
  • The hard-coded POLICIES dict (Dry Leaves / Dense Sticks / Unknown)
    is gone. There is no fixed material vocabulary.
  • classify() now consults the persistent ObjectMemory: if a tactile
    signature has been bootstrapped for any known label, nearest-
    neighbour returns that label. Otherwise None.
  • A simple contact-event detector watches for accel spikes and asks
    the world model to bind the spike to the visible object closest
    to the hand. That is the bootstrap path that grows the memory.

Can be imported by main_gui.py or run standalone for testing:
    python3 agent_simulator.py --mock
"""

import argparse
import threading
import time
from typing import Optional

# ── Shared state — read by main_gui.py ────────────────────────────────────────
# current_label is whatever the most recent (accel, fft) sample classified
# to according to memory. None until at least one tactile signature has
# been bootstrapped. directive is a short human-readable status line.
current_label: Optional[str] = None
current_directive: str = "Listening — no tactile signature learned yet."
current_distance: float = 0.0   # σ-distance from nearest learned sig
last_contact_ts: float = 0.0


# Memory-backed classifier. Returns the label of the closest learned
# tactile signature, or None if memory is empty / nothing is within
# the σ-gate. No hard-coded thresholds; everything is data-driven.
def classify(memory, accel_g: float, fft_peak_hz: int) -> Optional[tuple[str, float]]:
    return memory.nearest_tactile(accel_g, fft_peak_hz)


# Format a classification result as a short human-readable directive.
# Used as the subtitle of the dynamic banner in main_gui.py.
def emit_directive(label: Optional[str], dist: float) -> str:
    if label is None:
        return "Listening — no tactile signature matched. Pick something up to teach me."
    return f"Touching: {label}  (σ={dist:.2f} from learned signature)"


# Cheap contact-event detector. Returns True if the latest sample looks
# like the start of a touch: a meaningful jump in accel away from a
# rolling baseline. Uses a tiny EMA baseline rather than a fixed
# threshold so it adapts to ambient vibration.
class ContactDetector:
    # baseline_alpha controls how fast the rest-state vibration baseline
    # adapts. spike_g is the absolute jump above baseline that counts as
    # a contact. refractory_s suppresses repeat fires after a true touch.
    def __init__(self, baseline_alpha: float = 0.05,
                 spike_g: float = 0.35, refractory_s: float = 0.6):
        self.baseline = 0.0
        self.alpha = baseline_alpha
        self.spike_g = spike_g
        self.refractory_s = refractory_s
        self._last_fire = 0.0
        self._primed = False

    # Feed one accel sample; returns True exactly on the rising edge of
    # a contact event. Mutates the internal baseline so the detector
    # stays calibrated to the current ambient noise floor.
    def step(self, accel_g: float) -> bool:
        if not self._primed:
            self.baseline = accel_g
            self._primed = True
            return False
        delta = accel_g - self.baseline
        self.baseline = (1 - self.alpha) * self.baseline + self.alpha * accel_g
        now = time.time()
        if delta > self.spike_g and (now - self._last_fire) > self.refractory_s:
            self._last_fire = now
            return True
        return False


# Main consumer loop. Pulls tokens from token_queue, classifies each
# sample against memory, and triggers a contact-binding call on the
# world model when a spike is detected. world_model is optional — if
# None, the loop still classifies but cannot bootstrap new objects.
def run(token_queue, memory, world_model=None,
        stop_event: Optional[threading.Event] = None) -> None:
    global current_label, current_directive, current_distance, last_contact_ts
    detector = ContactDetector()

    while stop_event is None or not stop_event.is_set():
        try:
            token = token_queue.get(timeout=1.0)
            _, accel_g, fft_peak_hz, _ = token

            # 1. Classify against learned signatures (no thresholds).
            hit = classify(memory, accel_g, fft_peak_hz)
            if hit is not None:
                current_label, current_distance = hit
            else:
                current_distance = 0.0
                # Leave current_label sticky so the banner doesn't flicker
                # between transient/idle samples; it'll update on next hit.

            current_directive = emit_directive(current_label, current_distance)

            # 2. Contact event → ask world model to bind the spike to
            #    whichever visible object the hand is closest to. This is
            #    how new tactile signatures get learned (bootstrap path).
            if detector.step(accel_g) and world_model is not None:
                bound = world_model.handle_contact(accel_g, fft_peak_hz)
                if bound:
                    last_contact_ts = time.time()
                    current_label = bound
                    current_directive = (
                        f"Learned touch: {bound}  "
                        f"(accel={accel_g:.2f}g, fft={fft_peak_hz}Hz)"
                    )
        except Exception:
            continue


# Spawn the classifier loop as a daemon thread. Daemon so it dies with
# the host process; returns the Thread handle.
def start(token_queue, memory, world_model=None) -> threading.Thread:
    t = threading.Thread(
        target=run,
        args=(token_queue, memory, world_model),
        daemon=True,
        name='agent-simulator',
    )
    t.start()
    return t


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mock', action='store_true', help='Run with mock serial data')
    parser.add_argument('--db', default='object_memory.db', help='ObjectMemory SQLite path')
    args = parser.parse_args()

    from object_memory import ObjectMemory
    mem = ObjectMemory(db_path=args.db)

    if args.mock:
        from data_harvester import token_queue, start_mock
        start_mock()
    else:
        from data_harvester import token_queue, start as start_serial
        start_serial()

    start(token_queue, mem)
    print("Agent running. Press Ctrl+C to stop.\n")
    prev = None
    while True:
        if current_label != prev:
            print(f"  Label     : {current_label}")
            print(f"  Directive : {current_directive}\n")
            prev = current_label
        time.sleep(0.05)
