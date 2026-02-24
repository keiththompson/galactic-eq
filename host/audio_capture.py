"""Audio capture from BlackHole virtual audio device via sounddevice.

Provides a threaded InputStream that mixes stereo to mono and
delivers chunks to a callback.
"""

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
BLOCK_SIZE = 2048  # ~46 ms at 44.1 kHz — good FFT resolution


def find_blackhole_device() -> int | None:
    """Return the device index for BlackHole 2ch, or None."""
    for i, dev in enumerate(sd.query_devices()):
        if "blackhole" in dev["name"].lower() and dev["max_input_channels"] >= 2:
            return i
    return None


class AudioCapture:
    """Captures audio from BlackHole and delivers mono float32 chunks."""

    def __init__(self, callback, device=None, sample_rate=SAMPLE_RATE,
                 block_size=BLOCK_SIZE):
        """
        Args:
            callback: Called with (mono_chunk: np.ndarray) for each block.
                      mono_chunk is float32, shape (block_size,).
            device:   sounddevice device index.  None = auto-detect BlackHole.
            sample_rate: Sample rate in Hz.
            block_size:  Samples per block.
        """
        if device is None:
            device = find_blackhole_device()
            if device is None:
                raise RuntimeError(
                    "BlackHole audio device not found. "
                    "Install it with: brew install blackhole-2ch"
                )
        self._callback = callback
        self._device = device
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._stream = None

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def block_size(self):
        return self._block_size

    def start(self):
        """Open and start the audio stream."""
        self._stream = sd.InputStream(
            device=self._device,
            channels=2,
            samplerate=self._sample_rate,
            blocksize=self._block_size,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self):
        """Stop and close the audio stream."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[audio] {status}")
        # Mix stereo to mono
        mono = indata.mean(axis=1)
        self._callback(mono)
