# Galactic Equalizer

Pimoroni Galactic Unicorn audio visualizer -- a 53x11 LED matrix driven by macOS system audio over WiFi.

```
┌──────────────────────────────────────────────────┐
│               macOS Host (Python 3)              │
│  BlackHole audio -> FFT / scope / VU -> UDP pkt  │
└──────────────────────┬───────────────────────────┘
              WiFi UDP broadcast
            ┌──────────▼──────────┐
            │   Pico W / Pico 2 W │
            │   53 cols, 11 rows  │
            │   20 Hz – 20 kHz    │
            └─────────────────────┘
```

## Prerequisites

- One Pimoroni Galactic Unicorn board (Pico W / Pico 2 W)
- macOS with Python 3.10+
- BlackHole virtual audio device
- WiFi network accessible by both the Mac and the Pico

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

### 2. Install uv (package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install Python Dependencies

```bash
uv sync
```

### 4. Configure WiFi on the Pico

Copy the secrets template and fill in your WiFi credentials:

```bash
cp pico/secrets_template.py pico/secrets.py
```

Edit `pico/secrets.py` with your network name and password.

### 5. Flash the Pico Board

The Galactic Unicorn needs the MicroPython firmware with Pimoroni libraries. See [Pimoroni's guide](https://github.com/pimoroni/pimoroni-pico) for flashing.

If the board is mounted upside down, set `FLIPPED = True` in `pico/config.py` before deploying.

Deploy the `pico/` files to the board over USB:

```bash
./deploy.sh
```

Or specify a port explicitly:

```bash
./deploy.sh /dev/cu.usbmodem1201
```

## Usage

Power the board (USB or external) and make sure it's on the same WiFi network, then:

```bash
uv run python host/main.py
```

The host broadcasts UDP packets on port 4210. The Pico picks them up automatically.

### Options

```
--brightness N    LED brightness 0-255 (default: 180)
--udp-port PORT   UDP broadcast port (default: 4210)
--console         Print ASCII bars to terminal instead of sending
```

### Console Test Mode

Test the FFT pipeline without a board connected:

```bash
uv run python host/main.py --console
```

## Visualisation Modes

Switch modes using the buttons on the Galactic Unicorn:

| Button | Mode | Description |
|--------|------|-------------|
| **A** | Spectrum EQ | 53 log-frequency bands with green/yellow/red gradient and white peak-hold dots |
| **B** | Oscilloscope | Phosphor-green waveform with zero-crossing trigger and centre reference line |
| **C** | Spectrogram | Time-scrolling frequency heat map (newest at bottom, black -> blue -> cyan -> green -> yellow -> red -> white) |
| **D** | VU Meter | Stereo horizontal bar meter (L top, R bottom) with green/yellow/red gradient and peak-hold markers |

**Brightness** is adjusted with the Lux +/- buttons on the board and persists across reboots.

All modes run at **30 FPS**.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "BlackHole audio device not found" | Install BlackHole: `brew install blackhole-2ch` |
| No audio visualized | Set Multi-Output Device as system output in Sound preferences |
| Board shows nothing | Confirm the Pico and Mac are on the same WiFi network |
| Board not found during deploy | Connect via USB; check with `ls /dev/cu.usbmodem*` |
| Display upside down | Set `FLIPPED = True` in `pico/config.py` and redeploy |
| WiFi keeps dropping | Move the board closer to the access point; the Pico reconnects automatically |
