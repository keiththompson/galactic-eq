"""Galactic Equalizer — macOS host entry point.

Captures system audio via BlackHole, performs FFT analysis, and
sends equalizer data to two Galactic Unicorn boards at ~30 FPS.

Transport selection:
  --wifi          Force UDP broadcast (no serial)
  --left/--right  Force serial on explicit ports
  (default)       Auto-detect serial; fall back to UDP if no ports found

Usage:
    python host/main.py [--left PORT] [--right PORT] [--brightness 0-255]
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
from protocol import encode_packet, BOARD_LEFT, BOARD_RIGHT, NUM_COLS

TARGET_FPS = 30
FRAME_INTERVAL = 1.0 / TARGET_FPS
DEFAULT_BRIGHTNESS = 180


def main():
    parser = argparse.ArgumentParser(description="Galactic Equalizer host")
    parser.add_argument("--left", help="Serial port for left board")
    parser.add_argument("--right", help="Serial port for right board")
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
    latest_bars = np.zeros(106, dtype=int)
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
        if args.left or args.right:
            # Explicit serial ports — use serial
            print("[host] Opening serial connections...")
            ser = SerialManager(left_port=args.left, right_port=args.right)
            ser.open()
        elif args.wifi:
            # Explicit WiFi flag — use UDP
            print("[host] Opening UDP broadcast...")
            udp = UDPSender(port=args.udp_port)
            udp.open()
        else:
            # Auto-detect: try serial first, fall back to UDP
            ports = find_pico_ports()
            if len(ports) >= 2:
                print("[host] Opening serial connections...")
                ser = SerialManager()
                ser.open()
            else:
                print(f"[host] No serial ports found, using UDP broadcast...")
                udp = UDPSender(port=args.udp_port)
                udp.open()

    audio.start()
    print(f"[host] Running at {TARGET_FPS} FPS, brightness={brightness}")
    if args.console:
        print("[host] Console mode — press Ctrl+C to quit")
    elif udp:
        print("[host] Broadcasting via UDP — press Ctrl+C to quit")
    else:
        print("[host] Sending via serial — press Ctrl+C to quit")

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

            left_cols = bars[:NUM_COLS]
            right_cols = bars[NUM_COLS:]

            if args.console:
                _print_console(left_cols, right_cols)
            else:
                left_pkt = encode_packet(BOARD_LEFT, frame_num, brightness,
                                         left_cols)
                right_pkt = encode_packet(BOARD_RIGHT, frame_num, brightness,
                                          right_cols)
                if ser:
                    ser.send_left(left_pkt)
                    ser.send_right(right_pkt)
                elif udp:
                    udp.send(left_pkt)
                    udp.send(right_pkt)

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


def _print_console(left: np.ndarray, right: np.ndarray):
    """Render a simple ASCII bar chart to the terminal."""
    all_cols = np.concatenate([left, right])
    # Compress 106 cols down to terminal width (~53 chars)
    compressed = all_cols[::2]
    bar_chars = "".join("▁▂▃▄▅▆▇█"[min(v, 8)] if v > 0 else " "
                        for v in compressed)
    print(f"\r|{bar_chars}|", end="", flush=True)


if __name__ == "__main__":
    main()
