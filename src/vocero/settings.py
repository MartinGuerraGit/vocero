from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime knobs for the MVP, overridable through environment variables."""

    model_size: str = "small"  # small/medium for better accuracy with technical terms
    device: str = "cpu"
    compute_type: str = "int8"
    language: str | None = None  # None = auto-detect for better code-switching
    sample_rate: int = 16_000
    paste_delay_ms: int = 250
    hotkey: str = "<f4>"
    auto_paste: bool = True
    cpu_threads: int = 0  # 0 = let CTranslate2 decide default

    @classmethod
    def from_env(cls) -> "Settings":
        config = _read_config()

        language = os.getenv("VOCERO_LANGUAGE", config.get("language", cls.language))
        if language == "auto":
            language = None

        return cls(
            model_size=os.getenv("VOCERO_MODEL", str(config.get("model_size", cls.model_size))),
            device=os.getenv("VOCERO_DEVICE", str(config.get("device", cls.device))),
            compute_type=os.getenv(
                "VOCERO_COMPUTE_TYPE",
                str(config.get("compute_type", cls.compute_type)),
            ),
            language=language,
            sample_rate=int(
                os.getenv("VOCERO_SAMPLE_RATE", str(config.get("sample_rate", cls.sample_rate)))
            ),
            paste_delay_ms=int(
                os.getenv(
                    "VOCERO_PASTE_DELAY_MS",
                    str(config.get("paste_delay_ms", cls.paste_delay_ms)),
                )
            ),
            hotkey=os.getenv("VOCERO_HOTKEY", str(config.get("hotkey", cls.hotkey))),
            auto_paste=_bool_from_env(
                "VOCERO_AUTO_PASTE",
                bool(config.get("auto_paste", cls.auto_paste)),
            ),
            cpu_threads=int(
                os.getenv(
                    "VOCERO_CPU_THREADS",
                    str(config.get("cpu_threads", cls.cpu_threads)),
                )
            ),
        )


def _read_config() -> dict:
    config_path = Path(os.getenv("VOCERO_CONFIG", "~/.config/vocero/config.toml")).expanduser()
    if not config_path.exists():
        return {}

    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    return data.get("vocero", data)


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
