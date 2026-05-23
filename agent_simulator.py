"""
agent_simulator.py
Heuristic physical agent: Perceive → Reason → Act.
Classifies material state from sensor tokens and emits kinematic directives.

Can be imported by main_gui.py or run standalone for testing:
    python3 agent_simulator.py --mock
"""

import argparse
import threading
import time
from dataclasses import dataclass

# ── Material state definitions ────────────────────────────────────────────────

@dataclass
class Policy:
    state: str
    velocity_pct: float    # % change from nominal (0 = no change)
    pitch_deg: float       # blade pitch offset in degrees
    torque_scale: float    # multiplier on nominal joint torque
    dwell_ms: int = 0      # extra dwell time at contact point


# This is where we will add items for our demo.
POLICIES: dict[str, Policy] = {
    "Dry Leaves": Policy(
        state="Dry Leaves",
        velocity_pct=-10.0,  # Slow down slightly to handle brittle material
        pitch_deg=1.0,
        torque_scale=0.5,   # Low torque required for delicate surfaces
    ),
    "Dense Sticks": Policy(
        state="Dense Sticks",
        velocity_pct=-30.0,  # Slow down heavily for solid obstacles
        pitch_deg=4.0,       # Increase tool pitch clearance
        torque_scale=2.2,    # High torque scaling to move against resistance
    ),
    "Unknown": Policy(
        state="Unknown",
        velocity_pct=0.0,
        pitch_deg=0.0,
        torque_scale=1.0,
    )
}


# ── Perceive: classify material from raw token ─────────────────────────────────

def classify(accel_g: float, fft_peak_hz: int) -> str:
    """
    Classifies organic materials based on vibrational friction (g-force)
    and acoustic resonance peaks (Hz).
    """
    # Dry leaves generate high-frequency cracking noises but minimal heavy vibration
    if accel_g < 0.5 and fft_peak_hz > 1200:
        return "Dry Leaves"
        
    # Dense sticks generate low-frequency heavy impacts/thuds when scraped
    elif accel_g >= 1.0 and fft_peak_hz < 600:
        return "Dense Sticks"
        
    return "Unknown"


# ── Reason + Act: map state to directive string ────────────────────────────────

def emit_directive(policy: Policy) -> str:
    if policy.state == "Unknown":
        return "ACTION: HOLD — maintain last known state"
    dwell = f", dwell=+{policy.dwell_ms}ms" if policy.dwell_ms else ""
    sign = "+" if policy.velocity_pct >= 0 else ""
    return (
        f"ACTION: velocity={sign}{policy.velocity_pct:.0f}%, "
        f"pitch=+{policy.pitch_deg}°, "
        f"torque={policy.torque_scale}x"
        f"{dwell}"
    )


# ── Main agent loop (runs in its own thread) ──────────────────────────────────

# Shared state — read by main_gui.py
current_state: str = "Unknown"
current_directive: str = "ACTION: HOLD — waiting for data"
last_policy: Policy = POLICIES["Unknown"]


def run(token_queue, stop_event: threading.Event | None = None) -> None:
    """
    Pull tokens from token_queue and update shared agent state.
    Call this in a daemon thread from main_gui.py.
    """
    global current_state, current_directive, last_policy

    while stop_event is None or not stop_event.is_set():
        try:
            token = token_queue.get(timeout=1.0)
            _, accel_g, fft_peak_hz, _ = token

            state = classify(accel_g, fft_peak_hz)

            # Hold last known state on Unknown
            if state == "Unknown":
                state = last_policy.state

            policy = POLICIES[state]
            directive = emit_directive(policy)

            # Update shared globals (reads are atomic in CPython)
            current_state = state
            current_directive = directive
            last_policy = policy

        except Exception:
            continue


def start(token_queue) -> threading.Thread:
    """Start agent loop as daemon thread. Returns thread."""
    t = threading.Thread(
        target=run,
        args=(token_queue,),
        daemon=True,
        name='agent-simulator'
    )
    t.start()
    return t


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mock', action='store_true', help='Run with mock serial data')
    args = parser.parse_args()

    if args.mock:
        from data_harvester import token_queue, start_mock
        start_mock()
    else:
        from data_harvester import token_queue, start
        start()

    print("Agent running. Press Ctrl+C to stop.\n")
    prev_state = None
    while True:
        if current_state != prev_state:
            print(f"  State     : {current_state}")
            print(f"  Directive : {current_directive}\n")
            prev_state = current_state
        time.sleep(0.05)
