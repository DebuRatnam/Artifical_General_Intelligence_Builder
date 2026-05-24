"""
data_harvester.py
Non-blocking serial reader. Runs in a daemon thread and pushes
parsed tokens into a thread-safe Queue for the GUI and agent.

Usage (standalone diagnostics):
    python3 data_harvester.py --port /dev/ttyUSB0 --baud 460800 --dump
    python3 data_harvester.py --mock --dump
"""

import argparse
import threading
import time
from queue import Full, Queue

import serial

# ── Shared queue (imported by main_gui.py and agent_simulator.py) ─────────────
token_queue: Queue = Queue(maxsize=512)

# ── Token schema ──────────────────────────────────────────────────────────────
# [timestamp_ms (int), accel_g (float), fft_peak_hz (int), frame_id (int)]


# Parse one raw serial line into a 4-element token list.
# Format: "<ts_ms>,<accel_g>,<fft_peak_hz>,<frame_id>". Returns None on
# any parse error (malformed line, wrong field count, non-numeric).
def _parse_line(line: str) -> list | None:
    """Parse a CSV serial line into a token. Returns None on bad packet."""
    try:
        parts = line.strip().split(',')
        if len(parts) != 4:
            return None
        return [int(parts[0]), float(parts[1]), int(parts[2]), int(parts[3])]
    except (ValueError, IndexError):
        return None


# Non-blocking enqueue. If the queue is full we evict the oldest entry
# so the producer (serial reader) never stalls behind a slow consumer.
def _push(token: list) -> None:
    """Push token to queue; drop oldest if full."""
    try:
        token_queue.put_nowait(token)
    except Full:
        token_queue.get_nowait()
        token_queue.put_nowait(token)


# Background reader thread. Opens the serial port, then loops reading
# one line at a time, parsing it, and pushing the token. On serial
# error it logs and reconnects with a 2s backoff. Exits when stop_event is set.
def _reader_loop(port: str, baud: int, stop_event: threading.Event) -> None:
    """Background thread: read serial, parse, push to queue."""
    while not stop_event.is_set():
        try:
            with serial.Serial(port, baud, timeout=1.0) as ser:
                print(f"[harvester] connected: {port} @ {baud}")
                while not stop_event.is_set():
                    raw = ser.readline().decode('ascii', errors='ignore')
                    token = _parse_line(raw)
                    if token:
                        _push(token)
        except serial.SerialException as e:
            print(f"[harvester] serial error: {e} — retrying in 2s")
            time.sleep(2.0)


# Spawn the serial reader as a daemon thread so it dies with the host
# process. Returns the Thread handle for the caller (rarely needed).
def start(port: str = '/dev/ttyUSB0', baud: int = 460800) -> threading.Thread:
    """Start the serial reader as a daemon thread. Returns the thread."""
    stop_event = threading.Event()
    t = threading.Thread(
        target=_reader_loop,
        args=(port, baud, stop_event),
        daemon=True,
        name='serial-harvester'
    )
    t.start()
    return t


# ── Mock producer (no hardware needed) ───────────────────────────────────────
# Hardware-free producer. Generates random (but plausibly-ranged) tokens
# at a fixed rate so the rest of the host stack can be exercised end-to-end
# without the T5 board attached. Useful for UI dev and CI.
def start_mock(hz: int = 100) -> threading.Thread:
    """Inject synthetic tokens at a fixed rate for testing without hardware."""
    import random

    # Inner thread body. Emits one synthetic token per (1/hz) seconds
    # until the daemon thread is terminated by the process exiting.
    def _mock_loop():
        frame_id = 0
        while True:
            ts = int(time.time() * 1000)
            accel = round(random.uniform(0.1, 2.5), 4)
            fft_peak = random.randint(100, 4000)
            _push([ts, accel, fft_peak, frame_id])
            frame_id = (frame_id + 1) % 65535
            time.sleep(1.0 / hz)

    t = threading.Thread(target=_mock_loop, daemon=True, name='mock-harvester')
    t.start()
    return t


# ── CLI diagnostics ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',  default='/dev/ttyUSB0')
    parser.add_argument('--baud',  default=460800, type=int)
    parser.add_argument('--dump',  action='store_true', help='Print tokens to stdout')
    parser.add_argument('--mock',  action='store_true', help='Use mock data (no hardware)')
    args = parser.parse_args()

    if args.mock:
        start_mock()
        print("[harvester] running in MOCK mode")
    else:
        start(args.port, args.baud)

    while True:
        token = token_queue.get()
        if args.dump:
            ts, accel, fft, frame = token
            print(f"ts={ts}  accel={accel:.4f}g  fft={fft}Hz  frame={frame}")
