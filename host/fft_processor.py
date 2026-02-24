"""FFT processing: Hanning window, log-frequency band mapping, smoothing.

Converts raw audio chunks into 106 bar heights (0-11) suitable for
the dual 53-column Galactic Unicorn display.
"""

import numpy as np

NUM_BANDS = 106  # 53 per board
MAX_HEIGHT = 11
FREQ_MIN = 20.0
FREQ_MAX = 20000.0

# Smoothing: fast attack, slow decay
ATTACK = 0.8   # quickly follow rising levels
DECAY = 0.3    # slowly release falling levels

# dB range mapped to 0..MAX_HEIGHT
DB_FLOOR = -60.0
DB_CEIL = 0.0


class FFTProcessor:
    """Processes audio chunks into 106 equalizer bar heights."""

    def __init__(self, sample_rate: int, block_size: int):
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._window = np.hanning(block_size)
        self._smoothed = np.zeros(NUM_BANDS, dtype=np.float64)

        # Pre-compute log-spaced frequency band edges
        self._band_edges = np.logspace(
            np.log10(FREQ_MIN), np.log10(FREQ_MAX), NUM_BANDS + 1
        )

        # Map band edges to FFT bin indices
        freq_resolution = sample_rate / block_size
        self._bin_edges = np.round(self._band_edges / freq_resolution).astype(int)
        # Clamp to valid range
        max_bin = block_size // 2
        self._bin_edges = np.clip(self._bin_edges, 0, max_bin)

    def process(self, chunk: np.ndarray) -> np.ndarray:
        """Process one audio chunk into bar heights.

        Args:
            chunk: float32 mono audio, shape (block_size,)

        Returns:
            np.ndarray of int, shape (106,), values 0-11
        """
        # Windowed FFT
        windowed = chunk * self._window
        spectrum = np.abs(np.fft.rfft(windowed))

        # Aggregate into log-frequency bands
        band_magnitudes = np.zeros(NUM_BANDS, dtype=np.float64)
        for i in range(NUM_BANDS):
            lo = self._bin_edges[i]
            hi = self._bin_edges[i + 1]
            if hi <= lo:
                hi = lo + 1  # ensure at least one bin
            band_magnitudes[i] = np.mean(spectrum[lo:hi])

        # Convert to dB
        band_magnitudes = np.maximum(band_magnitudes, 1e-10)
        db = 20.0 * np.log10(band_magnitudes)

        # Normalize dB range to 0..MAX_HEIGHT
        normalized = (db - DB_FLOOR) / (DB_CEIL - DB_FLOOR)
        normalized = np.clip(normalized, 0.0, 1.0)
        heights = normalized * MAX_HEIGHT

        # Asymmetric smoothing
        for i in range(NUM_BANDS):
            if heights[i] >= self._smoothed[i]:
                self._smoothed[i] += ATTACK * (heights[i] - self._smoothed[i])
            else:
                self._smoothed[i] += DECAY * (heights[i] - self._smoothed[i])

        return np.round(self._smoothed).astype(int)
