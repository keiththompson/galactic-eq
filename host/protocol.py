"""Binary packet encoder for Galactic Unicorn serial protocol.

Packet format (59 bytes):
  Byte 0-1:  0xAA 0x55       Sync marker
  Byte 2:    Board ID        0x00=left, 0x01=right
  Byte 3:    Frame number    Rolling 0-255
  Byte 4:    Brightness      0-255
  Byte 5-57: Column data     53 bytes, each 0-11 (bar height)
  Byte 58:   Checksum        XOR of bytes 2-57
"""

SYNC = bytes([0xAA, 0x55])
BOARD_LEFT = 0x00
BOARD_RIGHT = 0x01
NUM_COLS = 53


def encode_packet(board_id: int, frame: int, brightness: int,
                  columns: bytes | list[int]) -> bytes:
    """Build a 59-byte binary packet for one board.

    Args:
        board_id:   BOARD_LEFT (0x00) or BOARD_RIGHT (0x01)
        frame:      Rolling frame counter 0-255
        brightness: Global brightness 0-255
        columns:    53 bar heights, each 0-11
    """
    body = bytearray(56)  # header(3) + columns(53)
    body[0] = board_id & 0xFF
    body[1] = frame & 0xFF
    body[2] = brightness & 0xFF
    for i in range(NUM_COLS):
        body[3 + i] = min(max(int(columns[i]), 0), 11)

    checksum = 0
    for b in body:
        checksum ^= b

    return SYNC + bytes(body) + bytes([checksum])
