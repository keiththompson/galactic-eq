"""WiFi UDP receiver for Galactic Unicorn visualiser.

Connects to WiFi using credentials from secrets.py, then listens
for 112-byte visualiser packets on UDP port 4210.
"""

import network
import socket
import time

UDP_PORT = 4210


class WiFiReceiver:
    """Receives equalizer packets over WiFi UDP broadcast."""

    def __init__(self, ssid, password):
        self._ssid = ssid
        self._password = password
        self._wlan = network.WLAN(network.STA_IF)
        self._sock = None

    def connect(self, timeout_s=10):
        """Activate WLAN and connect. Raises OSError on timeout."""
        self._wlan.active(True)
        self._wlan.connect(self._ssid, self._password)

        start = time.ticks_ms()
        while not self._wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > timeout_s * 1000:
                raise OSError("WiFi connect timeout")
            time.sleep_ms(100)

        ip = self._wlan.ifconfig()[0]
        print(f"[wifi] Connected: {ip}")

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("0.0.0.0", UDP_PORT))
        self._sock.setblocking(False)

    def recv(self):
        """Non-blocking receive. Returns bytes or None."""
        try:
            data, _addr = self._sock.recvfrom(128)
            return data
        except OSError:
            return None

    def check_reconnect(self):
        """Re-connect if WiFi dropped."""
        if not self._wlan.isconnected():
            print("[wifi] Disconnected, reconnecting...")
            try:
                self.close()
                self.connect()
            except OSError as e:
                print(f"[wifi] Reconnect failed: {e}")

    def close(self):
        """Tear down socket and WLAN."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._wlan.active(False)
