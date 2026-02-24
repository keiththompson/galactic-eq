"""Stereo level processor: computes L/R RMS and peak for VU meter display.

Maps stereo audio levels to 0-53 column positions suitable for the
53-column Galactic Unicorn display.
"""

import numpy as np

NUM_COLS = 53

# dB range and floor
DB_FLOOR = -60.0
DISPLAY_RANGE_DB = 54.0  # mapped onto 0..NUM_COLS

# RMS smoothing (medium integration, ~100 ms at 30 FPS)
RMS_ATTACK = 0.7
RMS_DECAY = 0.25

# Peak tracking: fast attack, slow decay for peak-hold markers
PEAK_ATTACK = 0.95
PEAK_RELEASE = 0.008  # ~4 s decay at 30 FPS

# Adaptive gain (same approach as FFTProcessor)
HEADROOM_DB = 3.0
GAIN_ATTACK_RATE = 0.9
GAIN_RELEASE_RATE = 0.005


class LevelProcessor:
    """Processes stereo audio into VU meter column positions."""

    def __init__(self):
        self._smoothed_rms = [0.0, 0.0]  # L, R
        self._peak_hold = [0.0, 0.0]     # L, R
        self._tracked_peak_db = DB_FLOOR

    def process(self, left: np.ndarray, right: np.ndarray) -> tuple[int, int, int, int]:
        """Process one stereo audio chunk into VU column positions.

        Args:
            left:  float32 left channel, shape (block_size,)
            right: float32 right channel, shape (block_size,)

        Returns:
            (l_rms, l_peak, r_rms, r_peak) as ints 0-53
        """
        channels = [left, right]
        result = []

        # Compute dB levels for both channels
        db_levels = []
        for ch in channels:
            rms = float(np.sqrt(np.mean(ch ** 2)))
            rms = max(rms, 1e-10)
            db_levels.append(20.0 * np.log10(rms))

        # Adaptive peak tracking across both channels
        current_peak_db = max(db_levels)
        if current_peak_db > self._tracked_peak_db:
            self._tracked_peak_db += GAIN_ATTACK_RATE * (
                current_peak_db - self._tracked_peak_db
            )
        else:
            self._tracked_peak_db += GAIN_RELEASE_RATE * (
                current_peak_db - self._tracked_peak_db
            )

        effective_ceil = self._tracked_peak_db + HEADROOM_DB
        effective_floor = max(effective_ceil - DISPLAY_RANGE_DB, DB_FLOOR)
        db_range = effective_ceil - effective_floor
        if db_range <= 0:
            db_range = 1.0

        for i, db in enumerate(db_levels):
            # Normalize to 0..1
            normalized = (db - effective_floor) / db_range
            normalized = max(0.0, min(1.0, normalized))
            target = normalized * NUM_COLS

            # RMS smoothing (asymmetric)
            if target >= self._smoothed_rms[i]:
                self._smoothed_rms[i] += RMS_ATTACK * (target - self._smoothed_rms[i])
            else:
                self._smoothed_rms[i] += RMS_DECAY * (target - self._smoothed_rms[i])

            # Peak hold
            if target >= self._peak_hold[i]:
                self._peak_hold[i] += PEAK_ATTACK * (target - self._peak_hold[i])
            else:
                self._peak_hold[i] = max(0.0, self._peak_hold[i] - PEAK_RELEASE * NUM_COLS)

            rms_col = int(round(self._smoothed_rms[i]))
            peak_col = int(round(self._peak_hold[i]))
            result.extend([
                max(0, min(NUM_COLS, rms_col)),
                max(0, min(NUM_COLS, peak_col)),
            ])

        return tuple(result)  # (l_rms, l_peak, r_rms, r_peak)
