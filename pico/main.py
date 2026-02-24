"""Galactic Unicorn visualiser -- Pico entry point.

Reads binary packets over WiFi UDP and renders on the LED matrix.
Button A = spectrum EQ, Button B = scope.
"""

import time

from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN

from config import FLIPPED
from protocol import validate_packet
from visualizer import Visualizer

# Timeout before blanking display when no packets arrive (ms)
NO_DATA_TIMEOUT_MS = 3000

# How often to check WiFi connection health (ms)
WIFI_CHECK_INTERVAL_MS = 5000

# Lux button brightness step (0.0-1.0 range)
LUX_STEP = 0.05
# Minimum time between repeated button presses (ms)
LUX_REPEAT_MS = 150

# File to persist brightness across reboots
LUX_FILE = "lux.cfg"
# Delay before writing to flash after last change (ms) to reduce wear
LUX_SAVE_DELAY_MS = 2000

# Visualisation modes (selected by A/B/C/D buttons)
MODE_EQ = 0     # Button A: spectrum analyser
MODE_SCOPE = 1  # Button B: oscilloscope
MODE_REPEAT_MS = 200  # debounce for mode buttons


def _load_lux():
    """Load saved brightness from flash, or return None."""
    try:
        with open(LUX_FILE, "r") as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return None


def _save_lux(brightness):
    """Write brightness to flash."""
    try:
        with open(LUX_FILE, "w") as f:
            f.write(str(round(brightness, 2)))
    except OSError:
        pass


def _connect_wifi():
    """Connect to WiFi and return a WiFiReceiver."""
    from secrets import WIFI_SSID, WIFI_PASSWORD
    from wifi_receiver import WiFiReceiver
    wifi = WiFiReceiver(WIFI_SSID, WIFI_PASSWORD)
    wifi.connect()
    return wifi


def _poll_lux(gu, local_brightness, last_lux_ms, lux_dirty_ms):
    """Check Lux +/- buttons and adjust local brightness.

    Returns (new_brightness, new_last_lux_ms, new_lux_dirty_ms).
    lux_dirty_ms is 0 when no save is pending, or the tick when the
    value last changed (used to defer the flash write).
    """
    now = time.ticks_ms()

    # Deferred save: write to flash once stable for LUX_SAVE_DELAY_MS
    if lux_dirty_ms and time.ticks_diff(now, lux_dirty_ms) >= LUX_SAVE_DELAY_MS:
        _save_lux(local_brightness)
        lux_dirty_ms = 0

    if time.ticks_diff(now, last_lux_ms) < LUX_REPEAT_MS:
        return local_brightness, last_lux_ms, lux_dirty_ms

    if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_UP):
        local_brightness = min(1.0, local_brightness + LUX_STEP)
        return local_brightness, now, now
    if gu.is_pressed(GalacticUnicorn.SWITCH_BRIGHTNESS_DOWN):
        local_brightness = max(LUX_STEP, local_brightness - LUX_STEP)
        return local_brightness, now, now

    return local_brightness, last_lux_ms, lux_dirty_ms


def _poll_mode(gu, current_mode, last_mode_ms):
    """Check A/B buttons for visualisation mode switch.

    Returns (mode, last_mode_ms).
    """
    now = time.ticks_ms()
    if time.ticks_diff(now, last_mode_ms) < MODE_REPEAT_MS:
        return current_mode, last_mode_ms

    if gu.is_pressed(GalacticUnicorn.SWITCH_A):
        return MODE_EQ, now
    if gu.is_pressed(GalacticUnicorn.SWITCH_B):
        return MODE_SCOPE, now

    return current_mode, last_mode_ms


def _render_frame(vis, pkt, brightness, mode):
    """Render the appropriate visualisation for the current mode."""
    if mode == MODE_SCOPE:
        vis.render_scope(pkt["scope"], brightness)
    else:
        vis.render(pkt["columns"], brightness)


def _run_wifi(wifi, vis, gu, initial_brightness):
    """Main loop: receive packets over WiFi UDP."""
    last_frame_ms = time.ticks_ms()
    last_wifi_check_ms = time.ticks_ms()
    blank = bytes(53)
    local_brightness = initial_brightness
    last_lux_ms = 0
    lux_dirty_ms = 0
    mode = MODE_EQ
    last_mode_ms = 0

    while True:
        local_brightness, last_lux_ms, lux_dirty_ms = _poll_lux(
            gu, local_brightness, last_lux_ms, lux_dirty_ms
        )
        mode, last_mode_ms = _poll_mode(gu, mode, last_mode_ms)

        data = wifi.recv()
        if data:
            pkt = validate_packet(data)
            if pkt:
                _render_frame(vis, pkt, local_brightness, mode)
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

    saved = _load_lux()
    brightness = saved if saved is not None else 0.5
    gu.set_brightness(brightness)
    print(f"[main] Brightness: {brightness:.2f}" + (" (saved)" if saved is not None else " (default)"))

    vis = Visualizer(gu, gfx, flipped=FLIPPED)

    wifi = _connect_wifi()
    print("[main] Using WiFi transport")
    _run_wifi(wifi, vis, gu, brightness)


main()
