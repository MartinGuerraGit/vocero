# Vocero

> Your digital spokesperson — local, private, ultra-fast voice dictation for Linux

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![faster-whisper](https://img.shields.io/badge/STT-faster--whisper-green.svg)](https://github.com/SYSTRAN/faster-whisper)

**Vocero** is a floating push-to-talk dictation widget for Linux. Hold a hotkey, speak, release — your words appear wherever you're typing. Fully offline, fully private.

## Features

- **Floating widget** that sits on top of your desktop, visible only while dictating
- **Push-to-talk**: hold hotkey &rarr; speak &rarr; release &rarr; text appears in your active app
- **100% local/offline** powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — no cloud, no network latency
- **Privacy-first**: your voice never leaves your machine
- **Direct typing** via ydotool, wtype, or xdotool into any application (clipboard fallback)
- **Optimized for speed**: pre-warmed model, greedy decoding (`beam_size=1`), temperature locked at 0.0, silence trimming

## Requirements

- Python 3.11+
- Linux (X11 or Wayland)
- A working microphone
- ~1 GB disk for the default `small` Whisper model (downloaded on first use)

## Installation

### 1. System dependencies

Vocero needs PortAudio for microphone access and a text-input tool to type into other apps.

**Debian / Ubuntu:**

```bash
sudo apt install build-essential portaudio19-dev xdotool
```

**Wayland users** — add these for native direct-typing support:

```bash
sudo apt install wtype ydotool
```

**Fedora:**

```bash
sudo dnf install portaudio-devel xdotool gcc
```

### 2. Install Vocero

```bash
git clone https://github.com/tuusuario/vocero.git
cd vocero
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

> For development (includes pytest): `pip install -e ".[dev]"`

### 3. Verify

```bash
python -c "import vocero; print(vocero.__name__)"
```

If this prints `vocero`, you're ready.

## Running

```bash
source .venv/bin/activate
vocero
```

Or without activating the venv:

```bash
.venv/bin/vocero
```

A small floating orb appears at the bottom-center of your screen.

**Default hotkey: F4**

1. Hold **F4**
2. Speak
3. Release **F4**
4. Your words are typed into the focused application

> On first run, Vocero downloads the Whisper model (~500 MB for `small`). This only happens once — after that it works fully offline.

## Hotkeys

### F4 in tmux with Ghostty

Ghostty reports `F4` as `ESC O S` (`kf4=\EOS`). If `F4` appears as repeated `[S` text inside CLI tools running under tmux, add this to `~/.tmux.conf`:

```tmux
set -g default-terminal "tmux-256color"
set -g xterm-keys on
set -as terminal-features ',xterm-ghostty:RGB'
set -as terminal-overrides ',xterm-ghostty:kf4=\EOS'
```

Reload tmux if a server is already running:

```bash
tmux source-file ~/.tmux.conf
```

If no tmux server is running, the next tmux session will load the config automatically. Existing panes may need a fresh tmux session to pick up terminal changes.

## Configuration

Configure via environment variables or a TOML file.

### Environment variables

```bash
VOCERO_HOTKEY="<ctrl>+<shift>+d" vocero
VOCERO_MODEL=medium VOCERO_DEVICE=cpu vocero
VOCERO_AUTO_PASTE=false vocero
VOCERO_LANGUAGE=en vocero
```

### Config file

`~/.config/vocero/config.toml`:

```toml
[vocero]
hotkey = "<f4>"
auto_paste = true
model_size = "small"      # tiny, base, small, medium, large-v3
device = "cpu"
compute_type = "int8"     # int8, int8_float16, float16
language = "es"           # null or "auto" for automatic detection
cpu_threads = 0           # 0 = auto-detect by CTranslate2
paste_delay_ms = 250
```

| Option | Environment variable | Default | Description |
|--------|---------------------|---------|-------------|
| `hotkey` | `VOCERO_HOTKEY` | `<f4>` | Push-to-talk key |
| `auto_paste` | `VOCERO_AUTO_PASTE` | `true` | Auto-paste after transcription |
| `model_size` | `VOCERO_MODEL` | `small` | Whisper model size |
| `device` | `VOCERO_DEVICE` | `cpu` | Inference device |
| `compute_type` | `VOCERO_COMPUTE_TYPE` | `int8` | Compute precision |
| `language` | `VOCERO_LANGUAGE` | `null` | Language (`"es"`, `"en"`, `null` for auto) |
| `sample_rate` | `VOCERO_SAMPLE_RATE` | `16000` | Audio sample rate |
| `cpu_threads` | `VOCERO_CPU_THREADS` | `0` | CPU threads (0 = auto) |
| `paste_delay_ms` | `VOCERO_PASTE_DELAY_MS` | `250` | Delay before paste |
| `config_path` | `VOCERO_CONFIG` | `~/.config/vocero/config.toml` | Config file path |

## Linux behavior

### Text insertion

Vocero tries to insert text directly into the active application using the best available method:

1. **ydotool** — preferred, works on both X11 and Wayland
2. **wtype** — Wayland sessions
3. **xdotool type** — X11 sessions
4. **Ctrl+V** — fallback via xdotool/wtype
5. **Clipboard** — last resort, text is copied for manual paste

If auto-paste fails, text remains in your clipboard for manual pasting.

### Global hotkeys

Global hotkeys work best on X11 via `pynput`. On Wayland, some compositors may restrict global key listening.

> **Wayland note:** If the hotkey doesn't work under your Wayland compositor, try running Vocero under XWayland or configure a global shortcut in your window manager.

## Why Vocero?

### vs. cloud dictation

| | Vocero | Cloud (Whisper API, etc.) |
|---|---|---|
| **Privacy** | Voice never leaves your machine | Audio sent to servers |
| **Internet** | No connection required | Requires internet |
| **Cost** | Free, no subscription | Pay per use |
| **Latency** | Local, immediate | Network-dependent |

### vs. stock faster-whisper

- **Pre-warmed model**: no startup delay per transcription
- **Greedy decoding**: `beam_size=1`, faster than beam search
- **Temperature locked at 0.0**: avoids costly retry loop with fallback temperatures
- **Silence trimming**: trims audio before transcription
- **~2-3x faster** than untuned faster-whisper

### vs. other local tools

- **Floating widget**: no window switching needed to dictate
- **Direct insertion**: types into any app, not just paste
- **Wayland support**: ydotool and wtype for native Wayland
- **Spanish by default**: built with Spanish speakers in mind

## Development

```bash
git clone https://github.com/tuusuario/vocero.git
cd vocero
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
python -m pytest
```

## License

MIT — do what you want, just keep the copyright notice.

## Contributing

PRs welcome. Open an issue to discuss large changes before submitting.

1. Fork the repo
2. Create your branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'feat: add X'`)
4. Push (`git push origin feature/name`)
5. Open a Pull Request
