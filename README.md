# Galactic Equalizer

Pimoroni Galactic Unicorn audio visualizer -- a 53x11 LED matrix real-time equalizer driven by macOS system audio.

```
┌─────────────────────────────────────────────────┐
│              macOS Host (Python 3)               │
│  BlackHole audio -> FFT -> serial packet -> USB  │
└──────────────────────┬──────────────────────────-┘
                USB Serial
            ┌──────────▼──────────┐
            │   Pico W / Pico 2 W │
            │   53 cols, 11 rows  │
            │   20 Hz - 20 kHz    │
            └─────────────────────┘
```

## Prerequisites

- One Pimoroni Galactic Unicorn board (Pico W / Pico 2 W)
- macOS with Python 3.10+
- BlackHole virtual audio device

## Setup

### 1. Install BlackHole

BlackHole routes macOS system audio to the Python host app.

```bash
brew install blackhole-2ch
```

After installation, create a **Multi-Output Device** in Audio MIDI Setup:

1. Open **Audio MIDI Setup** (Spotlight -> "Audio MIDI Setup")
2. Click **+** at bottom left -> **Create Multi-Output Device**
3. Check both **BlackHole 2ch** and your normal output (e.g. MacBook Speakers or headphones)
4. Right-click the Multi-Output Device -> **Use This Device For Sound Output**

Now all system audio plays through both your speakers and BlackHole simultaneously.

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Flash the Pico Board

The Galactic Unicorn needs the MicroPython firmware with Pimoroni libraries. See [Pimoroni's guide](https://github.com/pimoroni/pimoroni-pico) for flashing.

Copy the `pico/` files to the board. If the board is mounted upside down, set `FLIPPED = True` in `config.py` before copying.

## Usage

Connect the board via USB, then:

```bash
python host/main.py
```

The host auto-detects the Pico serial port (`/dev/cu.usbmodem*`).

### Options

```
--port PORT       Serial port for the board (skip auto-detect)
--brightness N    LED brightness 0-255 (default: 180)
--console         Print ASCII bars to terminal instead of serial
```

### Console Test Mode

Test the FFT pipeline without a board connected:

```bash
python host/main.py --console
```

### Manual Port Selection

```bash
python host/main.py --port /dev/cu.usbmodem1101
```

## Display

- **53 frequency bands** mapped logarithmically from 20 Hz to 20 kHz
- **Classic VU meter colours**: green (bottom) -> yellow (middle) -> red (top)
- **Peak hold**: white dot at each column's recent maximum, decays over ~2.4 seconds
- **30 FPS** update rate

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "BlackHole audio device not found" | Install BlackHole: `brew install blackhole-2ch` |
| No audio visualized | Set Multi-Output Device as system output in Sound preferences |
| No Pico serial port found | Connect the board via USB; check with `ls /dev/cu.usbmodem*` |
| Display upside down | Set `FLIPPED = True` in `config.py` and re-flash |
