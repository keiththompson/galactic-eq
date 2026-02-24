"""Galactic Equalizer -- macOS host entry point.

Captures system audio via BlackHole, performs FFT analysis, and
sends equalizer data to a Galactic Unicorn board at ~30 FPS.

Transport selection:
  --wifi          Force UDP broadcast (no serial)
  --port PORT     Force serial on explicit port
  (default)       Auto-detect serial; fall back to UDP if no port found

Usage:
    python host/main.py [--port PORT] [--brightness 0-255]
    python host/main.py --wifi [--udp-port 4210]
"""

import argparse
import signal
import sys
import threading
import time

import numpy as np

from audio_capture import AudioCapture
from fft_processor import FFTProcessor
from serial_manager import SerialManager, find_pico_ports
from udp_sender import UDPSender
from protocol import encode_packet, BOARD_ID, NUM_COLS

TARGET_FPS = 30
FRAME_INTERVAL = 1.0 / TARGET_FPS
DEFAULT_BRIGHTNESS = 180


def main():
    parser = argparse.ArgumentParser(description="Galactic Equalizer host")
    parser.add_argument("--port", help="Serial port for the board")
    parser.add_argument("--brightness", type=int, default=DEFAULT_BRIGHTNESS,
                        help="LED brightness 0-255 (default: 180)")
    parser.add_argument("--console", action="store_true",
                        help="Print bars to console instead of serial")
    parser.add_argument("--wifi", action="store_true",
                        help="Use UDP broadcast instead of serial")
    parser.add_argument("--udp-port", type=int, default=4210,
                        help="UDP broadcast port (default: 4210)")
    args = parser.parse_args()

    brightness = max(0, min(255, args.brightness))

    # Shared state: latest FFT result
    lock = threading.Lock()
    latest_bars = np.zeros(NUM_COLS, dtype=int)
    fft_proc = None

    def audio_callback(mono_chunk):
        nonlocal latest_bars, fft_proc
        if fft_proc is None:
            return
        bars = fft_proc.process(mono_chunk)
        with lock:
            latest_bars = bars

    # Set up audio
    print("[host] Starting audio capture from BlackHole...")
    audio = AudioCapture(callback=audio_callback)
    fft_proc = FFTProcessor(audio.sample_rate, audio.block_size)

    # Determine transport
    ser = None
    udp = None
    if not args.console:
        if args.port:
            # Explicit serial port
            print("[host] Opening serial connection...")
            ser = SerialManager(port=args.port)
            ser.open()
        elif args.wifi:
            # Explicit WiFi flag -- use UDP
            print("[host] Opening UDP broadcast...")
            udp = UDPSender(port=args.udp_port)
            udp.open()
        else:
            # Auto-detect: try serial first, fall back to UDP
            ports = find_pico_ports()
            if ports:
                print("[host] Opening serial connection...")
                ser = SerialManager()
                ser.open()
            else:
                print("[host] No serial port found, using UDP broadcast...")
                udp = UDPSender(port=args.udp_port)
                udp.open()

    audio.start()
    print(f"[host] Running at {TARGET_FPS} FPS, brightness={brightness}")
    if args.console:
        print("[host] Console mode -- press Ctrl+C to quit")
    elif udp:
        print("[host] Broadcasting via UDP -- press Ctrl+C to quit")
    else:
        print("[host] Sending via serial -- press Ctrl+C to quit")

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

            cols = bars[:NUM_COLS]

            if args.console:
                _print_console(cols)
            else:
                pkt = encode_packet(BOARD_ID, frame_num, brightness, cols)
                if ser:
                    ser.send(pkt)
                elif udp:
                    udp.send(pkt)

            frame_num = (frame_num + 1) & 0xFF

            # Sleep remainder of frame
            elapsed = time.monotonic() - t0
            if elapsed < FRAME_INTERVAL:
                time.sleep(FRAME_INTERVAL - elapsed)

    finally:
        print("\n[host] Shutting down...")
        audio.stop()
        if ser:
            ser.close()
        if udp:
            udp.close()


def _print_console(cols: np.ndarray):
    """Render a simple ASCII bar chart to the terminal."""
    bar_chars = "".join("▁▂▃▄▅▆▇█"[min(v, 8)] if v > 0 else " "
                        for v in cols)
    print(f"\r|{bar_chars}|", end="", flush=True)


if __name__ == "__main__":
    main()
