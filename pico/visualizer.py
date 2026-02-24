"""LED rendering for Galactic Unicorn visualisations.

EQ mode (button A):
    Colour gradient (classic VU meter):
        Rows 0-3   (bottom) : green
        Rows 4-7   (middle) : yellow
        Rows 8-10  (top)    : red
    Peak hold: white dot at column maximum, decays ~0.15 per frame.

Scope mode (button B):
    Classic phosphor-green oscilloscope waveform with connected
    line drawing and a dim centre reference line.

Spectrogram mode (button C):
    Time-scrolling frequency heat map.  Newest frame at bottom,
    oldest at top.  Colour encodes intensity (black -> blue ->
    cyan -> green -> yellow -> red -> white).

VU meter mode (button D):
    Stereo horizontal bar meter.  Top 5 rows = L channel,
    dim separator at row 5, bottom 5 rows = R channel.
    Green -> yellow -> red gradient with peak-hold markers.
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

# Spectrogram heat-map: 12 colours for intensity 0-11
_HEAT_COLOURS = [
    (0, 0, 0),        # 0  black (silence)
    (0, 0, 64),       # 1  dark blue
    (0, 0, 160),      # 2  blue
    (0, 0, 255),      # 3  bright blue
    (0, 128, 255),    # 4  cyan-blue
    (0, 255, 128),    # 5  cyan-green
    (0, 255, 0),      # 6  green
    (128, 255, 0),    # 7  yellow-green
    (255, 255, 0),    # 8  yellow
    (255, 128, 0),    # 9  orange
    (255, 0, 0),      # 10 red
    (255, 255, 255),  # 11 white (loudest)
]

# VU meter colour zones along 53 columns
VU_GREEN_END = 36   # columns 0-36
VU_YELLOW_END = 46  # columns 37-46
# columns 47-52 = red

VU_PEAK_DECAY = 0.3  # peak marker decay per frame (columns)


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
        # Scope pens
        self._scope_pen = graphics.create_pen(0, 255, 50)
        self._center_pen = graphics.create_pen(20, 40, 20)
        # Spectrogram pens and history buffer
        self._heat_pens = [graphics.create_pen(r, g, b) for r, g, b in _HEAT_COLOURS]
        self._sg_buf = [[0] * WIDTH for _ in range(HEIGHT)]
        # VU meter pens and peak state
        self._vu_green = graphics.create_pen(0, 255, 0)
        self._vu_yellow = graphics.create_pen(255, 255, 0)
        self._vu_red = graphics.create_pen(255, 0, 0)
        self._vu_sep = graphics.create_pen(30, 30, 30)
        self._vu_peaks = [0.0, 0.0]  # L, R peak hold on device

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

    def render_scope(self, scope_columns, brightness):
        """Draw one oscilloscope frame.

        scope_columns: bytes/list of 53 values 0-10 (Y positions,
        0 = bottom, 10 = top).
        """
        if isinstance(brightness, float):
            self._gu.set_brightness(brightness)
        else:
            self._gu.set_brightness(brightness / 255.0)

        gfx = self._gfx
        gfx.set_pen(self._black)
        gfx.clear()

        # Dim centre reference line (row 5)
        center_display_row = HEIGHT // 2
        gfx.set_pen(self._center_pen)
        for col in range(WIDTH):
            dx, dy = self._map(col, center_display_row)
            gfx.pixel(dx, dy)

        # Waveform trace
        gfx.set_pen(self._scope_pen)
        prev_y = min(scope_columns[0], HEIGHT - 1)
        for col in range(WIDTH):
            curr_y = min(scope_columns[col], HEIGHT - 1)

            # Fill vertical span between prev and current to connect the line
            if col > 0:
                y_lo = min(prev_y, curr_y)
                y_hi = max(prev_y, curr_y)
                for fill_y in range(y_lo, y_hi + 1):
                    dx, dy = self._map(col, HEIGHT - 1 - fill_y)
                    gfx.pixel(dx, dy)
            else:
                dx, dy = self._map(col, HEIGHT - 1 - curr_y)
                gfx.pixel(dx, dy)

            prev_y = curr_y

        self._gu.update(gfx)

    def render_spectrogram(self, columns, brightness):
        """Draw one spectrogram frame (time-frequency heat map).

        columns: bytes/list of 53 values 0-11 (current spectrum).
        Newest data appears at the bottom row, scrolls upward over time.
        """
        if isinstance(brightness, float):
            self._gu.set_brightness(brightness)
        else:
            self._gu.set_brightness(brightness / 255.0)

        # Shift history up: drop oldest (top), append new at bottom
        buf = self._sg_buf
        buf.pop(0)
        buf.append([min(c, MAX_BAR) for c in columns])

        gfx = self._gfx
        gfx.set_pen(self._black)
        gfx.clear()

        for row in range(HEIGHT):
            row_data = buf[row]
            for col in range(WIDTH):
                intensity = row_data[col]
                if intensity > 0:
                    gfx.set_pen(self._heat_pens[intensity])
                    # row 0 of buf = oldest = display top
                    dx, dy = self._map(col, row)
                    gfx.pixel(dx, dy)

        self._gu.update(gfx)

    def render_vu(self, vu_data, brightness):
        """Draw stereo VU meter.

        vu_data: bytes of 4 values (l_rms, l_peak, r_rms, r_peak),
        each 0-53 representing column position.
        Top 5 rows = L channel, row 5 = separator, bottom 5 rows = R.
        """
        if isinstance(brightness, float):
            self._gu.set_brightness(brightness)
        else:
            self._gu.set_brightness(brightness / 255.0)

        gfx = self._gfx
        gfx.set_pen(self._black)
        gfx.clear()

        l_rms = vu_data[0]
        l_peak = vu_data[1]
        r_rms = vu_data[2]
        r_peak = vu_data[3]

        # Device-side peak hold with decay
        for i, pk in enumerate([l_peak, r_peak]):
            if pk >= self._vu_peaks[i]:
                self._vu_peaks[i] = float(pk)
            else:
                self._vu_peaks[i] = max(0.0, self._vu_peaks[i] - VU_PEAK_DECAY)

        # Draw separator line at display row 5 (middle)
        gfx.set_pen(self._vu_sep)
        for col in range(WIDTH):
            dx, dy = self._map(col, 5)
            gfx.pixel(dx, dy)

        # Draw channel bars
        # L channel: display rows 0-4 (top), R channel: display rows 6-10 (bottom)
        channels = [
            (l_rms, self._vu_peaks[0], range(0, 5)),   # L: rows 0-4
            (r_rms, self._vu_peaks[1], range(6, 11)),   # R: rows 6-10
        ]

        for ch_idx, (rms_col, peak_col, row_range) in enumerate(channels):
            # RMS filled bar
            for col in range(min(rms_col, WIDTH)):
                if col <= VU_GREEN_END:
                    gfx.set_pen(self._vu_green)
                elif col <= VU_YELLOW_END:
                    gfx.set_pen(self._vu_yellow)
                else:
                    gfx.set_pen(self._vu_red)
                for row in row_range:
                    dx, dy = self._map(col, row)
                    gfx.pixel(dx, dy)

            # Peak hold marker (white vertical line)
            pk = int(self._vu_peaks[ch_idx] + 0.5)
            if 0 < pk < WIDTH:
                gfx.set_pen(self._white)
                for row in row_range:
                    dx, dy = self._map(pk, row)
                    gfx.pixel(dx, dy)

        self._gu.update(gfx)

    def _map(self, x, y):
        """Apply flip transform if board is mounted upside down."""
        if self._flipped:
            return WIDTH - 1 - x, HEIGHT - 1 - y
        return x, y
