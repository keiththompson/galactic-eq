"""UDP broadcast sender for Galactic Unicorn equalizer.

Sends 59-byte equalizer packets to 255.255.255.255 for the
Pico W board on the local network.
"""

import socket

DEFAULT_PORT = 4210


class UDPSender:
    """Broadcasts equalizer packets over UDP."""

    def __init__(self, port=DEFAULT_PORT):
        self._port = port
        self._sock = None

    def open(self):
        """Create a broadcast-enabled UDP socket."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print(f"[udp] Broadcasting on port {self._port}")

    def send(self, packet: bytes):
        """Send a packet to the broadcast address."""
        if self._sock:
            try:
                self._sock.sendto(packet, ("255.255.255.255", self._port))
            except OSError as e:
                print(f"[udp] Send error: {e}")

    def close(self):
        """Tear down the socket."""
        if self._sock:
            self._sock.close()
            self._sock = None
