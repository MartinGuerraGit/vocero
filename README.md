# Vocero 🎙️

> Tu portavoz digital — dictado por voz local, privado y ultrarrápido para Linux

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![faster-whisper](https://img.shields.io/badge/STT-faster--whisper-green.svg)](https://github.com/SYSTRAN/faster-whisper)

---

**Vocero** is a floating push-to-talk dictation widget for Linux. Hold a hotkey, speak, release — and your words appear wherever you're typing. Fully offline, fully private.

---

## ¿Qué es Vocero? / What is Vocero?

- **Floating widget** that sits on top of your desktop, visible only while you're dictating
- **Push-to-talk**: hold hotkey → speak → release → text appears in your active app
- **100% local/offline** powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — zero cloud, zero latency
- **Privacy-first**: your voice never leaves your machine
- **Direct typing** via ydotool, wtype, or xdotool into any application + clipboard fallback
- **Optimized for speed**: pre-warmed model, greedy decoding (beam_size=1), temperature locked at 0.0, silence trimming

---

## Instalación / Installation

### Dependencias del sistema / System dependencies

```bash
# Debian/Ubuntu
sudo apt install build-essential xdotool portaudio19-dev

# Wayland users — optional but recommended for direct typing
sudo apt install wtype ydotool
```

### Instalación / Install

```bash
# Desde fuente (recomendado para desarrollo)
git clone https://github.com/tuusuario/vocero.git
cd vocero
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# O via pip (próximamente)
pip install vocero
```

La primera transcripción descargará automáticamente el modelo Whisper seleccionado. Después de eso, Vocero funciona completamente offline.

---

## Uso rápido / Quick start

```bash
vocero
# o:
python -m vocero
```

Hotkey por defecto: **F4**

Mantené F4, hablá, soltá — el texto aparece donde estés escribiendo.

---

## Configuración / Configuration

Vocero se configura mediante variables de entorno o archivo TOML.

### Variables de entorno / Environment variables

```bash
VOCERO_HOTKEY="<ctrl>+<shift>+d" vocero
VOCERO_MODEL=medium VOCERO_DEVICE=cpu vocero
VOCERO_AUTO_PASTE=false vocero
VOCERO_LANGUAGE=en vocero
```

### Archivo de configuración / Config file

`~/.config/vocero/config.toml`:

```toml
[vocero]
hotkey = "<f4>"
auto_paste = true
model_size = "small"      # tiny, base, small, medium, large-v3
device = "cpu"
compute_type = "int8"     # int8, int8_float16, float16
language = "es"            # null o "auto" para detección automática
cpu_threads = 0            # 0 = detección automática por CTranslate2
paste_delay_ms = 250
```

| Opción | Variable de entorno | Default | Descripción |
|--------|-------------------|---------|-------------|
| `hotkey` | `VOCERO_HOTKEY` | `<f4>` | Tecla de push-to-talk |
| `auto_paste` | `VOCERO_AUTO_PASTE` | `true` | Pegar automáticamente tras transcribir |
| `model_size` | `VOCERO_MODEL` | `small` | Tamaño del modelo Whisper |
| `device` | `VOCERO_DEVICE` | `cpu` | Dispositivo de inferencia |
| `compute_type` | `VOCERO_COMPUTE_TYPE` | `int8` | Precisión de cómputo |
| `language` | `VOCERO_LANGUAGE` | `null` | Idioma (`"es"`, `"en"`, `null` para auto) |
| `sample_rate` | `VOCERO_SAMPLE_RATE` | `16000` | Frecuencia de muestreo de audio |
| `cpu_threads` | `VOCERO_CPU_THREADS` | `0` | Threads de CPU (0 = auto) |
| `paste_delay_ms` | `VOCERO_PASTE_DELAY_MS` | `250` | Delay antes del pegado |
| `config_path` | `VOCERO_CONFIG` | `~/.config/vocero/config.toml` | Ruta del archivo de configuración |

---

## Comportamiento en Linux / Linux behavior

### Pegado / Paste

Vocero intenta insertar texto directamente en la aplicación activa:

1. **ydotool** — primera opción, funciona en X11 y Wayland
2. **wtype** — en sesiones Wayland
3. **xdotool type** — en sesiones X11
4. **Ctrl+V** — fallback vía xdotool/wtype
5. **Portapapeles** — último recurso, el texto queda copiado para pegado manual

Si el pegado automático falla, el texto queda en el portapapeles y podés pegarlo manualmente.

### Hotkeys globales / Global hotkeys

Las hotkeys globales funcionan mejor en X11 vía `pynput`. En Wayland, algunos compositores pueden restringir la escucha global de teclas.

> **Nota Wayland:** Si la hotkey no funciona bajo tu compositor Wayland, probá ejecutar Vocero bajo XWayland o configurá un atajo global en tu window manager.

---

## ¿Por qué Vocero? / Why Vocero?

### vs. dictado en la nube / cloud dictation

| | Vocero | Cloud (Whisper API, etc.) |
|---|---|---|
| **Privacidad** | Tu voz nunca sale de tu máquina | Audio enviado a servidores |
| **Internet** | No requiere conexión | Requiere internet |
| **Costo** | Gratis, sin suscripción | Pago por uso |
| **Latencia** | Local, inmediata | Depende de la red |

### vs. faster-whisper sin optimizar / stock faster-whisper

- **Modelo pre-calentado**: sin espera al iniciar una transcripción
- **Decodificación greedy**: beam_size=1, más rápido que beam search
- **Temperatura bloqueada en 0.0**: evita el costoso loop de reintentos con fallback
- **Trimming de silencio**: recorta audio antes de transcribir
- **~2-3x más rápido** que faster-whisper sin tuning

### vs. otras herramientas locales / other local tools

- **Widget flotante**: no necesitás cambiar de ventana para dictar
- **Inserción directa**: tipea en cualquier app, no solo pega
- **Soporte Wayland**: ydotool y wtype para Wayland nativo
- **Idioma español por defecto**: pensado para hispanohablantes

---

## Desarrollo / Development

```bash
# Clonar e instalar dependencias de desarrollo
git clone https://github.com/tuusuario/vocero.git
cd vocero
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Ejecutar tests
python -m pytest
```

---

## Licencia / License

MIT — hacé lo que quieras, solo mantené el aviso de copyright.

---

## Contribuir / Contributing

PRs bienvenidas. Abrí un issue para discutir cambios grandes antes de mandar PR.

1. Fork el repo
2. Creá tu branch (`git checkout -b feature/nombre`)
3. Commit changes (`git commit -m 'feat: agrego X'`)
4. Push (`git push origin feature/nombre`)
5. Abrí un Pull Request
