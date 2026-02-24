"""Serial port manager for Galactic Unicorn board.

Auto-detects a Pico board via /dev/cu.usbmodem* glob pattern
and sends binary packets to it.
"""

import glob
import serial

BAUD = 115200
PICO_GLOB = "/dev/cu.usbmodem*"


def find_pico_ports() -> list[str]:
    """Return sorted list of serial ports matching Pico pattern."""
    return sorted(glob.glob(PICO_GLOB))


class SerialManager:
    """Manages a serial connection to a Pico board."""

    def __init__(self, port: str | None = None):
        """
        Args:
            port: Serial port path, or None for auto-detect.
        """
        self._port_path = port
        self._conn: serial.Serial | None = None

    def open(self):
        """Open serial connection. Auto-detects port if not specified."""
        if self._port_path:
            port = self._port_path
        else:
            ports = find_pico_ports()
            if not ports:
                raise RuntimeError(
                    "No Pico serial port found.\n"
                    "Connect the Galactic Unicorn board via USB."
                )
            if len(ports) > 1:
                print(f"[serial] Found {len(ports)} ports, using first: {ports[0]}")
            port = ports[0]

        print(f"[serial] Board: {port}")
        self._conn = serial.Serial(port, BAUD, timeout=0)

    def close(self):
        """Close the serial connection."""
        if self._conn and self._conn.is_open:
            self._conn.close()
        self._conn = None

    def send(self, packet: bytes):
        """Send a packet to the board."""
        if self._conn and self._conn.is_open:
            try:
                self._conn.write(packet)
            except serial.SerialException as e:
                print(f"[serial] Write error: {e}")

    @property
    def is_open(self) -> bool:
        return self._conn is not None and self._conn.is_open
