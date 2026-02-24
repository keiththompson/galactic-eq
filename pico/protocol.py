"""Binary packet decoder for Galactic Unicorn serial protocol.

Packet format (59 bytes):
  Byte 0-1:  0xAA 0x55       Sync marker
  Byte 2:    Board ID        0x00 (single board)
  Byte 3:    Frame number    Rolling 0-255
  Byte 4:    Brightness      0-255
  Byte 5-57: Column data     53 bytes, each 0-11 (bar height)
  Byte 58:   Checksum        XOR of bytes 2-57

Uses a state machine for byte-at-a-time parsing so it works
with non-blocking reads and self-recovers from lost bytes.
"""

SYNC_0 = 0xAA
SYNC_1 = 0x55
HEADER_SIZE = 3      # board_id + frame + brightness
NUM_COLS = 53
PACKET_BODY = HEADER_SIZE + NUM_COLS  # 56 bytes after sync
PACKET_TOTAL = 2 + PACKET_BODY + 1   # 59 bytes

_STATE_SYNC0 = 0
_STATE_SYNC1 = 1
_STATE_BODY = 2


class PacketDecoder:
    """State-machine decoder that yields complete, validated frames."""

    def __init__(self):
        self._state = _STATE_SYNC0
        self._buf = bytearray(PACKET_BODY + 1)  # body + checksum
        self._pos = 0

    def feed(self, data):
        """Feed raw bytes; returns list of decoded packets (may be empty).

        Each returned packet is a dict:
            board_id:   int
            frame:      int
            brightness: int
            columns:    bytes (length 53, values 0-11)
        """
        results = []
        for b in data:
            if self._state == _STATE_SYNC0:
                if b == SYNC_0:
                    self._state = _STATE_SYNC1
            elif self._state == _STATE_SYNC1:
                if b == SYNC_1:
                    self._state = _STATE_BODY
                    self._pos = 0
                elif b == SYNC_0:
                    pass  # stay in SYNC1 — handles 0xAA 0xAA 0x55
                else:
                    self._state = _STATE_SYNC0
            elif self._state == _STATE_BODY:
                self._buf[self._pos] = b
                self._pos += 1
                if self._pos == PACKET_BODY + 1:
                    self._state = _STATE_SYNC0
                    # Validate checksum: XOR of bytes 2-57 (body sans checksum)
                    chk = 0
                    for i in range(PACKET_BODY):
                        chk ^= self._buf[i]
                    if chk == self._buf[PACKET_BODY]:
                        results.append({
                            "board_id": self._buf[0],
                            "frame": self._buf[1],
                            "brightness": self._buf[2],
                            "columns": bytes(self._buf[3:3 + NUM_COLS]),
                        })
        return results


def validate_packet(data):
    """Validate a complete 59-byte UDP datagram.

    Unlike PacketDecoder (which handles a byte stream), this checks a
    single buffer in one shot: sync marker, length, and XOR checksum.

    Returns a dict with board_id/frame/brightness/columns, or None if invalid.
    """
    if len(data) != PACKET_TOTAL:
        return None
    if data[0] != SYNC_0 or data[1] != SYNC_1:
        return None

    body = data[2:2 + PACKET_BODY]
    checksum = data[2 + PACKET_BODY]

    chk = 0
    for b in body:
        chk ^= b
    if chk != checksum:
        return None

    return {
        "board_id": body[0],
        "frame": body[1],
        "brightness": body[2],
        "columns": bytes(body[3:3 + NUM_COLS]),
    }
