"""
data_harvester.py
Non-blocking serial reader. Runs in a daemon thread and pushes
parsed tokens into a thread-safe Queue for the GUI and agent.

Supports two stream types from the T5 board over the same UART:
- Telemetry CSV: line prefixed with `T,` then `<ts>,<accel>,<fft>,<frame_id>\n`
- JPEG frames:   line prefixed with `J,<len>,<id>\n` then `<len>` raw bytes

Usage (standalone diagnostics):
    python3 data_harvester.py --port /dev/ttyUSB0 --baud 460800 --dump
    python3 data_harvester.py --mock --dump
"""

import argparse
import threading
import time
from queue import Full, Queue

import serial

# ── Shared queues ─────────────────────────────────────────────────────────────
token_queue: Queue = Queue(maxsize=512)   # parsed telemetry tokens
frame_queue: Queue = Queue(maxsize=8)     # latest JPEG bytes (small bounded)


def _parse_telemetry(payload: bytes) -> list | None:
    """`<ts>,<accel>,<fft>,<frame_id>` → token list. None on parse error."""
    try:
        parts = payload.decode('ascii', errors='ignore').strip().split(',')
        if len(parts) != 4:
            return None
        return [int(parts[0]), float(parts[1]), int(parts[2]), int(parts[3])]
    except (ValueError, IndexError):
        return None


def _push(q: Queue, item) -> None:
    """Non-blocking enqueue; drop oldest if full so producer never stalls."""
    try:
        q.put_nowait(item)
    except Full:
        try:
            q.get_nowait()
        except Exception:
            pass
        try:
            q.put_nowait(item)
        except Full:
            pass


def _read_exact(ser: serial.Serial, n: int, stop_event: threading.Event) -> bytes:
    """Read exactly n bytes from serial. Returns partial on stop/timeout."""
    buf = bytearray()
    while len(buf) < n and not stop_event.is_set():
        chunk = ser.read(n - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def _reader_loop(port: str, baud: int, stop_event: threading.Event) -> None:
    """Background thread: read framed stream (T,... lines + J,<len>,<id> + bytes)."""
    while not stop_event.is_set():
        try:
            with serial.Serial(port, baud, timeout=1.0) as ser:
                print(f"[harvester] connected: {port} @ {baud}")
                pending = bytearray()
                while not stop_event.is_set():
                    chunk = ser.read(4096)
                    if chunk:
                        pending.extend(chunk)

                    while b'\n' in pending:
                        nl = pending.index(b'\n')
                        line = bytes(pending[:nl]).rstrip(b'\r')
                        del pending[:nl + 1]

                        if line.startswith(b'T,'):
                            tok = _parse_telemetry(line[2:])
                            if tok:
                                _push(token_queue, tok)
                        elif line.startswith(b'J,'):
                            parts = line.split(b',')
                            if len(parts) != 3:
                                continue
                            try:
                                jlen = int(parts[1])
                                jid  = int(parts[2])
                            except ValueError:
                                continue
                            if jlen <= 0 or jlen > 200_000:
                                continue
                            while len(pending) < jlen and not stop_event.is_set():
                                more = ser.read(jlen - len(pending))
                                if not more:
                                    break
                                pending.extend(more)
                            if len(pending) >= jlen:
                                jpeg = bytes(pending[:jlen])
                                del pending[:jlen]
                                _push(frame_queue, {'id': jid, 'jpeg': jpeg, 'ts': time.time()})
                        # unknown prefix → drop silently
        except serial.SerialException as e:
            print(f"[harvester] serial error: {e} — retrying in 2s")
            time.sleep(2.0)


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
def start_mock(hz: int = 100) -> threading.Thread:
    """Inject synthetic tokens + a single placeholder JPEG for end-to-end testing."""
    import random

    def _mock_loop():
        frame_id = 0
        cam_id = 0
        last_cam = 0.0
        # Minimal valid 1x1 JPEG placeholder
        placeholder = bytes.fromhex(
            'ffd8ffe000104a46494600010100000100010000ffdb0043000806060706050806070707'
            '090908080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c28'
            '372a2c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d18321f'
            '1c1f3232323232323232323232323232323232323232323232323232323232323232323232'
            '32323232323232323232323232323232ffc0001108000100010301220002110103110100'
            'ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400'
            'b5100002010303020403050504040000017d01020300041105122131410613516107227114'
            '328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738'
            '393a434445464748494a535455565758595a636465666768696a737475767778797a8384'
            '85868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4'
            'c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faff'
            'da0008010100003f00fbffd9'
        )
        while True:
            ts = int(time.time() * 1000)
            accel = round(random.uniform(0.1, 2.5), 4)
            fft_peak = random.randint(100, 4000)
            _push(token_queue, [ts, accel, fft_peak, frame_id])
            frame_id = (frame_id + 1) % 65535

            now = time.time()
            if now - last_cam > 0.5:
                _push(frame_queue, {'id': cam_id, 'jpeg': placeholder, 'ts': now})
                cam_id += 1
                last_cam = now

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

    last_t = time.time()
    t_count = 0; j_count = 0
    while True:
        try:
            token = token_queue.get(timeout=0.1)
            t_count += 1
            if args.dump:
                ts, accel, fft, frame = token
                print(f"T ts={ts}  accel={accel:.4f}g  fft={fft}Hz  frame={frame}")
        except Exception:
            pass
        try:
            f = frame_queue.get_nowait()
            j_count += 1
            if args.dump:
                print(f"J id={f['id']} len={len(f['jpeg'])} bytes")
        except Exception:
            pass
        if time.time() - last_t > 5:
            print(f"[stats] T={t_count} J={j_count}")
            last_t = time.time()
