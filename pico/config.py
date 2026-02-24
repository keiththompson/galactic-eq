# pico/config.py — edit per board before flashing
#
# BOARD_ID: 0x00 = left board (low frequencies, cols 0-52)
#           0x01 = right board (high frequencies, cols 53-105)
#
# FLIPPED:  True if the board is mounted upside down.
#           The visualizer will mirror both axes so the display
#           looks correct, and the startup label renders properly.

BOARD_ID = 0x01
FLIPPED = False
