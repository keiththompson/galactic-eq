"""LED rendering for Galactic Unicorn equalizer bars.

Colour gradient (classic VU meter):
    Rows 0-3   (bottom) : green
    Rows 4-7   (middle) : yellow
    Rows 8-10  (top)    : red

Peak hold: white dot at column maximum, decays ~0.15 per frame
(~2.4 s full decay at 30 FPS).
"""

from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN

WIDTH = GalacticUnicorn.WIDTH   # 53
HEIGHT = GalacticUnicorn.HEIGHT  # 11
MAX_BAR = HEIGHT                # 11

# Pre-built colour table per row (bottom = row 0)
# Each entry is (r, g, b)
_ROW_COLOURS = [
    (0, 255, 0),    # 0  green
    (0, 255, 0),    # 1
    (0, 255, 0),    # 2
    (0, 255, 0),    # 3
    (255, 255, 0),  # 4  yellow
    (255, 255, 0),  # 5
    (255, 200, 0),  # 6
    (255, 150, 0),  # 7
    (255, 60, 0),   # 8  red
    (255, 20, 0),   # 9
    (255, 0, 0),    # 10
]

PEAK_DECAY = 0.15
LOCAL_SMOOTH = 0.8  # blend toward new value each frame

# Minimal 5×7 bitmap font for startup labels (5 bits per row, MSB = left)
_LABEL_FONT = {
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x10, 0x13, 0x11, 0x0E),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
}


class Visualizer:
    def __init__(self, gu, graphics, flipped=False):
        self._gu = gu
        self._gfx = graphics
        self._flipped = flipped
        self._peaks = [0.0] * WIDTH
        self._smooth = [0.0] * WIDTH
        # Pre-create pen objects for each row colour + black + white
        self._row_pens = [graphics.create_pen(r, g, b) for r, g, b in _ROW_COLOURS]
        self._black = graphics.create_pen(0, 0, 0)
        self._white = graphics.create_pen(255, 255, 255)

    def render(self, columns, brightness):
        """Draw one frame.  columns: bytes/list of 53 values 0-11.

        brightness: float 0.0-1.0 (local lux control) or int 0-255
        (legacy host packet).
        """
        if isinstance(brightness, float):
            self._gu.set_brightness(brightness)
        else:
            self._gu.set_brightness(brightness / 255.0)
        gfx = self._gfx
        gfx.set_pen(self._black)
        gfx.clear()

        for col in range(WIDTH):
            target = min(columns[col], MAX_BAR)

            # Local smoothing
            self._smooth[col] += LOCAL_SMOOTH * (target - self._smooth[col])
            bar = int(self._smooth[col] + 0.5)

            # Peak hold
            if bar >= self._peaks[col]:
                self._peaks[col] = float(bar)
            else:
                self._peaks[col] = max(0.0, self._peaks[col] - PEAK_DECAY)

            peak_row = int(self._peaks[col] + 0.5) - 1  # -1 because bar=1 means row 0 lit

            # Map to display coordinates
            # Display row 0 is top, but we want row 0 of our bar at the bottom
            for row in range(bar):
                dx, dy = self._map(col, HEIGHT - 1 - row)
                gfx.set_pen(self._row_pens[row])
                gfx.pixel(dx, dy)

            # Peak dot (white)
            if peak_row >= 0 and peak_row < HEIGHT:
                dx, dy = self._map(col, HEIGHT - 1 - peak_row)
                gfx.set_pen(self._white)
                gfx.pixel(dx, dy)

        self._gu.update(gfx)

    def show_label(self, text):
        """Display a centred label (e.g. 'LEFT' or 'RIGHT')."""
        gfx = self._gfx
        gfx.set_pen(self._black)
        gfx.clear()
        gfx.set_pen(self._white)
        if self._flipped:
            # Draw pixel-by-pixel through _map() so glyphs rotate with
            # the board — gfx.text() can't rotate its built-in bitmaps.
            tw = len(text) * 6
            x0 = (WIDTH - tw) // 2
            y0 = (HEIGHT - 7) // 2
            for ci, ch in enumerate(text):
                glyph = _LABEL_FONT.get(ch)
                if glyph is None:
                    continue
                for row, bits in enumerate(glyph):
                    for col in range(5):
                        if bits & (0x10 >> col):
                            dx, dy = self._map(x0 + ci * 6 + col, y0 + row)
                            gfx.pixel(dx, dy)
        else:
            tw = len(text) * 6
            x = (WIDTH - tw) // 2
            y = (HEIGHT - 8) // 2
            gfx.text(text, x, y, -1, 1)
        self._gu.update(gfx)

    def _map(self, x, y):
        """Apply flip transform if board is mounted upside down."""
        if self._flipped:
            return WIDTH - 1 - x, HEIGHT - 1 - y
        return x, y
