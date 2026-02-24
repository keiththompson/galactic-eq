"""Binary packet encoder for Galactic Unicorn serial protocol.

Packet format (116 bytes):
  Byte 0-1:    0xAA 0x55       Sync marker
  Byte 2:      Board ID        0x00 (single board)
  Byte 3:      Frame number    Rolling 0-255
  Byte 4:      Brightness      0-255
  Byte 5-57:   EQ columns      53 bytes, each 0-11 (bar height)
  Byte 58-110: Scope columns   53 bytes, each 0-10 (waveform Y)
  Byte 111:    VU L RMS        0-53 (bar column position)
  Byte 112:    VU L Peak       0-53
  Byte 113:    VU R RMS        0-53
  Byte 114:    VU R Peak       0-53
  Byte 115:    Checksum        XOR of bytes 2-114
"""

SYNC = bytes([0xAA, 0x55])
BOARD_ID = 0x00
NUM_COLS = 53
VU_FIELDS = 4  # l_rms, l_peak, r_rms, r_peak


def encode_packet(board_id: int, frame: int, brightness: int,
                  columns: bytes | list[int],
                  scope_columns: bytes | list[int] | None = None,
                  vu: tuple[int, int, int, int] | None = None) -> bytes:
    """Build a 116-byte binary packet.

    Args:
        board_id:      Board identifier (default 0x00)
        frame:         Rolling frame counter 0-255
        brightness:    Global brightness 0-255
        columns:       53 EQ bar heights, each 0-11
        scope_columns: 53 scope Y positions, each 0-10 (zeros if None)
        vu:            (l_rms, l_peak, r_rms, r_peak) each 0-53 (zeros if None)
    """
    body = bytearray(3 + NUM_COLS + NUM_COLS + VU_FIELDS)  # 113 bytes
    body[0] = board_id & 0xFF
    body[1] = frame & 0xFF
    body[2] = brightness & 0xFF
    for i in range(NUM_COLS):
        body[3 + i] = min(max(int(columns[i]), 0), 11)
    if scope_columns is not None:
        for i in range(NUM_COLS):
            body[56 + i] = min(max(int(scope_columns[i]), 0), 10)
    if vu is not None:
        for i in range(VU_FIELDS):
            body[109 + i] = min(max(int(vu[i]), 0), NUM_COLS)

    checksum = 0
    for b in body:
        checksum ^= b

    return SYNC + bytes(body) + bytes([checksum])
