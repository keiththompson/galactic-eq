"""Binary packet codec for Galactic Unicorn protocol.

Packet format (112 bytes):
  Byte 0-1:    0xAA 0x55       Sync marker
  Byte 2:      Board ID        0x00 (single board)
  Byte 3:      Frame number    Rolling 0-255
  Byte 4:      Brightness      0-255
  Byte 5-57:   EQ columns      53 bytes, each 0-11 (bar height)
  Byte 58-110: Scope columns   53 bytes, each 0-10 (waveform Y)
  Byte 111:    Checksum        XOR of bytes 2-110
"""

SYNC_0 = 0xAA
SYNC_1 = 0x55
HEADER_SIZE = 3      # board_id + frame + brightness
NUM_COLS = 53
PACKET_BODY = HEADER_SIZE + NUM_COLS + NUM_COLS  # 109 bytes after sync
PACKET_TOTAL = 2 + PACKET_BODY + 1               # 112 bytes

def validate_packet(data):
    """Validate a complete 112-byte UDP datagram.

    Checks sync marker, length, and XOR checksum in one shot.

    Returns a dict with board_id/frame/brightness/columns/scope, or None.
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
        "scope": bytes(body[56:56 + NUM_COLS]),
    }
