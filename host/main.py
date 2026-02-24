"""Galactic Equalizer -- macOS host entry point.

Captures system audio via BlackHole, performs FFT analysis, and
sends equalizer data to a Galactic Unicorn board at ~30 FPS via
UDP broadcast.

Usage:
    python host/main.py [--brightness 0-255] [--udp-port 4210]
    python host/main.py --console
"""

import argparse
import signal
import threading
import time

import numpy as np
from audio_capture import AudioCapture
from fft_processor import FFTProcessor
from level_processor import LevelProcessor
from protocol import BOARD_ID, NUM_COLS, encode_packet
from udp_sender import UDPSender
from waveform_processor import WaveformProcessor

TARGET_FPS = 30
FRAME_INTERVAL = 1.0 / TARGET_FPS
DEFAULT_BRIGHTNESS = 180


def main():
    parser = argparse.ArgumentParser(description="Galactic Equalizer host")
    parser.add_argument(
        "--brightness",
        type=int,
        default=DEFAULT_BRIGHTNESS,
        help="LED brightness 0-255 (default: 180)",
    )
    parser.add_argument(
        "--console", action="store_true", help="Print bars to console instead of sending"
    )
    parser.add_argument(
        "--udp-port", type=int, default=4210, help="UDP broadcast port (default: 4210)"
    )
    args = parser.parse_args()

    brightness = max(0, min(255, args.brightness))

    # Shared state: latest FFT + waveform + VU results
    lock = threading.Lock()
    latest_bars = np.zeros(NUM_COLS, dtype=int)
    latest_scope = np.zeros(NUM_COLS, dtype=int)
    latest_vu = (0, 0, 0, 0)
    fft_proc = None
    wave_proc = None
    level_proc = None

    def audio_callback(mono_chunk, left_chunk, right_chunk):
        nonlocal latest_bars, latest_scope, latest_vu, fft_proc, wave_proc, level_proc
        if fft_proc is None or wave_proc is None or level_proc is None:
            return
        bars = fft_proc.process(mono_chunk)
        scope = wave_proc.process(mono_chunk)
        vu = level_proc.process(left_chunk, right_chunk)
        with lock:
            latest_bars = bars
            latest_scope = scope
            latest_vu = vu

    # Set up audio
    print("[host] Starting audio capture from BlackHole...")
    audio = AudioCapture(callback=audio_callback)
    fft_proc = FFTProcessor(audio.sample_rate, audio.block_size)
    wave_proc = WaveformProcessor(audio.block_size)
    level_proc = LevelProcessor()

    # Set up transport
    udp = None
    if not args.console:
        print("[host] Opening UDP broadcast...")
        udp = UDPSender(port=args.udp_port)
        udp.open()

    audio.start()
    print(f"[host] Running at {TARGET_FPS} FPS, brightness={brightness}")
    if args.console:
        print("[host] Console mode -- press Ctrl+C to quit")
    else:
        print("[host] Broadcasting via UDP -- press Ctrl+C to quit")

    # Graceful shutdown
    running = True

    def shutdown(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    frame_num = 0
    try:
        while running:
            t0 = time.monotonic()

            with lock:
                bars = latest_bars.copy()
                scope = latest_scope.copy()
                vu = latest_vu

            cols = bars[:NUM_COLS]
            scope_cols = scope[:NUM_COLS]

            if args.console:
                _print_console(cols)
            elif udp:
                pkt = encode_packet(
                    BOARD_ID, frame_num, brightness, cols.tolist(), scope_cols.tolist(), vu=vu
                )
                udp.send(pkt)

            frame_num = (frame_num + 1) & 0xFF

            # Sleep remainder of frame
            elapsed = time.monotonic() - t0
            if elapsed < FRAME_INTERVAL:
                time.sleep(FRAME_INTERVAL - elapsed)

    finally:
        print("\n[host] Shutting down...")
        audio.stop()
        if udp:
            udp.close()


def _print_console(cols: np.ndarray):
    """Render a simple ASCII bar chart to the terminal."""
    bar_chars = "".join("▁▂▃▄▅▆▇█"[min(v, 7)] if v > 0 else " " for v in cols)
    print(f"\r|{bar_chars}|", end="", flush=True)


if __name__ == "__main__":
    main()
