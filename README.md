# Galactic Equalizer

Dual Pimoroni Galactic Unicorn audio visualizer — two 53x11 LED matrices acting as a single 106x11 real-time equalizer driven by macOS system audio.

```
┌─────────────────────────────────────────────────┐
│              macOS Host (Python 3)               │
│  BlackHole audio → FFT → serial packets → USB   │
└──────────────────────┬──────────────────────────-┘
                USB Serial x2
          ┌────────────┴────────────┐
   ┌──────▼──────┐          ┌──────▼──────┐
   │ Pico LEFT   │          │ Pico RIGHT  │
   │ cols 0-52   │          │ cols 53-105 │
   │ 20Hz-~2kHz  │          │ ~2kHz-20kHz │
   └─────────────┘          └─────────────┘
```

## Prerequisites

- Two Pimoroni Galactic Unicorn boards (Pico W / Pico 2 W)
- macOS with Python 3.10+
- BlackHole virtual audio device

## Setup

### 1. Install BlackHole

BlackHole routes macOS system audio to the Python host app.

```bash
brew install blackhole-2ch
```

After installation, create a **Multi-Output Device** in Audio MIDI Setup:

1. Open **Audio MIDI Setup** (Spotlight → "Audio MIDI Setup")
2. Click **+** at bottom left → **Create Multi-Output Device**
3. Check both **BlackHole 2ch** and your normal output (e.g. MacBook Speakers or headphones)
4. Right-click the Multi-Output Device → **Use This Device For Sound Output**

Now all system audio plays through both your speakers and BlackHole simultaneously.

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Flash the Pico Boards

Each Galactic Unicorn needs the MicroPython firmware with Pimoroni libraries. See [Pimoroni's guide](https://github.com/pimoroni/pimoroni-pico) for flashing.

Copy the `pico/` files to each board:

**Left board:**
- Edit `pico/config.py`: set `BOARD_ID = 0x00`
- Copy all four files (`config.py`, `protocol.py`, `visualizer.py`, `main.py`) to the board

**Right board:**
- Edit `pico/config.py`: set `BOARD_ID = 0x01`
- Copy all four files to the board

If a board is mounted upside down, set `FLIPPED = True` in `config.py`.

## Usage

Connect both boards via USB, then:

```bash
python host/main.py
```

The host auto-detects both Pico serial ports (`/dev/cu.usbmodem*`).

### Options

```
--left PORT       Serial port for left board (skip auto-detect)
--right PORT      Serial port for right board (skip auto-detect)
--brightness N    LED brightness 0-255 (default: 180)
--console         Print ASCII bars to terminal instead of serial
```

### Console Test Mode

Test the FFT pipeline without boards connected:

```bash
python host/main.py --console
```

### Manual Port Selection

If auto-detect picks the wrong order:

```bash
python host/main.py --left /dev/cu.usbmodem1101 --right /dev/cu.usbmodem1201
```

## Board Startup

Each board shows "LEFT" or "RIGHT" for 2 seconds on boot so you can verify they're in the correct positions. If a label appears on the wrong side, swap the USB cables or swap the `--left`/`--right` port arguments.

## Display

- **106 frequency bands** mapped logarithmically from 20 Hz to 20 kHz
- **Classic VU meter colours**: green (bottom) → yellow (middle) → red (top)
- **Peak hold**: white dot at each column's recent maximum, decays over ~2.4 seconds
- **30 FPS** update rate

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "BlackHole audio device not found" | Install BlackHole: `brew install blackhole-2ch` |
| No audio visualized | Set Multi-Output Device as system output in Sound preferences |
| "Expected 2 Pico serial ports" | Connect both boards via USB; check with `ls /dev/cu.usbmodem*` |
| Boards show wrong sides | Swap USB cables or use `--left`/`--right` flags |
| Display upside down | Set `FLIPPED = True` in that board's `config.py` and re-flash |
