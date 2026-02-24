"""Galactic Unicorn equalizer — Pico entry point.

Reads binary packets from USB serial or WiFi UDP and renders
equalizer bars on the LED matrix.  Shows a 'LEFT' or 'RIGHT' label
on startup for 2 seconds so the user can verify board position.

Transport selection (automatic at startup):
  - If pico/secrets.py exists and WiFi connects → UDP receiver
  - Otherwise → USB serial (stdin)
"""

import time
import sys
import select

from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN

from config import BOARD_ID, FLIPPED
from protocol import PacketDecoder, validate_packet
from visualizer import Visualizer

BAUD = 115200
LABEL = "LEFT" if BOARD_ID == 0x00 else "RIGHT"

# Timeout before blanking display when no packets arrive (ms)
NO_DATA_TIMEOUT_MS = 3000

# How often to check WiFi connection health (ms)
WIFI_CHECK_INTERVAL_MS = 5000

# Lux button brightness step (0.0–1.0 range)
LUX_STEP = 0.05
# Minimum time between repeated button presses (ms)
LUX_REPEAT_MS = 150


def _try_wifi():
    """Attempt WiFi setup. Returns a WiFiReceiver or None."""
    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        return None

    try:
        from wifi_receiver import WiFiReceiver
        wifi = WiFiReceiver(WIFI_SSID, WIFI_PASSWORD)
        wifi.connect()
        return wifi
    except OSError as e:
        print(f"[main] WiFi failed: {e}, falling back to serial")
        return None


def _poll_lux(gu, local_brightness, last_lux_ms):
    """Check Lux +/- buttons and adjust local brightness.

    Returns (new_brightness, new_last_lux_ms).  When no button is
    pressed, returns values unchanged.
    """
    now = time.ticks_ms()
    if time.ticks_diff(now, last_lux_ms) < LUX_REPEAT_MS:
        return local_brightness, last_lux_ms

    if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP):
        local_brightness = min(1.0, local_brightness + LUX_STEP)
        return local_brightness, now
    if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN):
        local_brightness = max(0.0, local_brightness - LUX_STEP)
        return local_brightness, now

    return local_brightness, last_lux_ms


def _run_serial(vis, gu):
    """Main loop: receive packets over USB serial (original path)."""
    decoder = PacketDecoder()
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)

    last_frame_ms = time.ticks_ms()
    blank = bytes(53)
    local_brightness = gu.get_brightness()
    last_lux_ms = 0

    while True:
        local_brightness, last_lux_ms = _poll_lux(gu, local_brightness, last_lux_ms)

        events = poller.poll(0)
        if events:
            data = sys.stdin.buffer.read()
            if data:
                packets = decoder.feed(data)
                for pkt in packets:
                    if pkt["board_id"] == BOARD_ID:
                        vis.render(pkt["columns"], local_brightness)
                        last_frame_ms = time.ticks_ms()

        elapsed = time.ticks_diff(time.ticks_ms(), last_frame_ms)
        if elapsed > NO_DATA_TIMEOUT_MS:
            vis.render(blank, 0)
            last_frame_ms = time.ticks_ms()

        time.sleep_ms(1)


def _run_wifi(wifi, vis, gu):
    """Main loop: receive packets over WiFi UDP."""
    last_frame_ms = time.ticks_ms()
    last_wifi_check_ms = time.ticks_ms()
    blank = bytes(53)
    local_brightness = gu.get_brightness()
    last_lux_ms = 0

    while True:
        local_brightness, last_lux_ms = _poll_lux(gu, local_brightness, last_lux_ms)

        data = wifi.recv()
        if data:
            pkt = validate_packet(data)
            if pkt and pkt["board_id"] == BOARD_ID:
                vis.render(pkt["columns"], local_brightness)
                last_frame_ms = time.ticks_ms()

        # Blank display if no data for a while
        elapsed = time.ticks_diff(time.ticks_ms(), last_frame_ms)
        if elapsed > NO_DATA_TIMEOUT_MS:
            vis.render(blank, 0)
            last_frame_ms = time.ticks_ms()

        # Periodic WiFi health check
        now = time.ticks_ms()
        if time.ticks_diff(now, last_wifi_check_ms) > WIFI_CHECK_INTERVAL_MS:
            wifi.check_reconnect()
            last_wifi_check_ms = now

        time.sleep_ms(1)


def main():
    gu = GalacticUnicorn()
    gfx = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)
    gu.set_brightness(0.5)

    vis = Visualizer(gu, gfx, flipped=FLIPPED)

    # Show board identity label
    vis.show_label(LABEL)
    time.sleep(2)

    wifi = _try_wifi()
    if wifi:
        print("[main] Using WiFi transport")
        vis.show_label(LABEL)  # refresh label after WiFi connect delay
        _run_wifi(wifi, vis, gu)
    else:
        print("[main] Using serial transport")
        _run_serial(vis, gu)


main()
