"""Dual serial port manager for Galactic Unicorn boards.

Auto-detects Pico boards via /dev/cu.usbmodem* glob pattern
and sends binary packets to each.
"""

import glob
import serial

BAUD = 115200
PICO_GLOB = "/dev/cu.usbmodem*"


def find_pico_ports() -> list[str]:
    """Return sorted list of serial ports matching Pico pattern."""
    return sorted(glob.glob(PICO_GLOB))


class SerialManager:
    """Manages two serial connections to left and right Pico boards."""

    def __init__(self, left_port: str | None = None,
                 right_port: str | None = None):
        """
        Args:
            left_port:  Serial port for left board, or None for auto-detect.
            right_port: Serial port for right board, or None for auto-detect.
        """
        self._left_port = left_port
        self._right_port = right_port
        self._left: serial.Serial | None = None
        self._right: serial.Serial | None = None

    def open(self):
        """Open serial connections. Auto-detects ports if not specified."""
        if self._left_port and self._right_port:
            ports = [self._left_port, self._right_port]
        else:
            ports = find_pico_ports()
            if len(ports) < 2:
                raise RuntimeError(
                    f"Expected 2 Pico serial ports, found {len(ports)}: {ports}\n"
                    "Connect both Galactic Unicorn boards via USB."
                )
            if len(ports) > 2:
                print(f"[serial] Found {len(ports)} ports, using first two: "
                      f"{ports[0]}, {ports[1]}")
                ports = ports[:2]

        print(f"[serial] Left board:  {ports[0]}")
        print(f"[serial] Right board: {ports[1]}")

        self._left = serial.Serial(ports[0], BAUD, timeout=0)
        self._right = serial.Serial(ports[1], BAUD, timeout=0)

    def close(self):
        """Close both serial connections."""
        for conn in (self._left, self._right):
            if conn and conn.is_open:
                conn.close()
        self._left = None
        self._right = None

    def send_left(self, packet: bytes):
        """Send a packet to the left board."""
        if self._left and self._left.is_open:
            try:
                self._left.write(packet)
            except serial.SerialException as e:
                print(f"[serial] Left write error: {e}")

    def send_right(self, packet: bytes):
        """Send a packet to the right board."""
        if self._right and self._right.is_open:
            try:
                self._right.write(packet)
            except serial.SerialException as e:
                print(f"[serial] Right write error: {e}")

    @property
    def is_open(self) -> bool:
        return (self._left is not None and self._left.is_open and
                self._right is not None and self._right.is_open)
