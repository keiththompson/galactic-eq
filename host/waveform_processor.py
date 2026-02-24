"""Waveform processor: downsamples audio to 53 Y-positions for scope display.

Uses rising zero-crossing trigger detection to stabilise the waveform
on screen, and adaptive gain so quiet and loud signals both fill the
display nicely.
"""

import numpy as np

NUM_COLS = 53
MAX_Y = 10  # 0-10 across 11 display rows

# Adaptive gain tracking
GAIN_ATTACK = 0.9
GAIN_RELEASE = 0.01
MIN_AMPLITUDE = 0.001


class WaveformProcessor:
    """Downsamples audio chunks to 53 scope Y-positions (0-10)."""

    def __init__(self, block_size: int):
        self._block_size = block_size
        self._tracked_peak = MIN_AMPLITUDE

    def process(self, chunk: np.ndarray) -> np.ndarray:
        """Process one audio chunk into scope column values.

        Args:
            chunk: float32 mono audio, shape (block_size,)

        Returns:
            np.ndarray of int, shape (53,), values 0-10
        """
        trigger = self._find_trigger(chunk)

        # Show roughly half the block from the trigger point
        window_size = self._block_size // 2
        end = min(trigger + window_size, len(chunk))
        segment = chunk[trigger:end]

        if len(segment) < NUM_COLS:
            segment = np.pad(segment, (0, NUM_COLS - len(segment)))

        # Downsample to 53 points via linear interpolation
        indices = np.linspace(0, len(segment) - 1, NUM_COLS)
        downsampled = np.interp(indices, np.arange(len(segment)), segment)

        # Adaptive gain
        peak = float(np.max(np.abs(downsampled)))
        if peak > self._tracked_peak:
            self._tracked_peak += GAIN_ATTACK * (peak - self._tracked_peak)
        else:
            self._tracked_peak += GAIN_RELEASE * (peak - self._tracked_peak)
        self._tracked_peak = max(self._tracked_peak, MIN_AMPLITUDE)

        normalized = np.clip(downsampled / self._tracked_peak, -1.0, 1.0)

        # Map -1..1 → 0..10  (centre line at 5)
        y = ((normalized + 1.0) * 0.5 * MAX_Y).astype(int)
        return np.clip(y, 0, MAX_Y)

    def _find_trigger(self, chunk: np.ndarray) -> int:
        """Rising zero-crossing in the first quarter of the buffer."""
        search_end = len(chunk) // 4
        for i in range(1, search_end):
            if chunk[i - 1] <= 0.0 and chunk[i] > 0.0:
                return i
        return 0
