from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path
from typing import Callable

import numpy as np

_LOGGER = logging.getLogger(__name__)


class AudioRecorder:
    """Record microphone audio into a temporary mono WAV file."""

    def __init__(self, sample_rate: int = 16_000, level_callback: Callable[[float], None] | None = None) -> None:
        self.sample_rate = sample_rate
        self._level_callback = level_callback
        self._stream = None
        self._chunks: list[np.ndarray] = []

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            raise RuntimeError("Recording is already in progress.")

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "sounddevice is required for microphone capture. "
                'Install dependencies with: pip install -e ".[dev]"'
            ) from exc

        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._on_audio,
        )
        self._stream.start()

    def stop(self) -> Path:
        if self._stream is None:
            raise RuntimeError("Recording is not in progress.")

        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None
        return self._write_wav()

    def _on_audio(self, indata, frames, time, status) -> None:
        del frames, time
        if status:
            _LOGGER.warning("Audio stream status: %s", status)
        self._chunks.append(indata.copy())
        if self._level_callback is not None:
            level = float(np.sqrt(np.mean(np.square(indata)))) if indata.size else 0.0
            self._level_callback(min(level * 8.0, 1.0))

    def _trim_silence(self, audio: np.ndarray, threshold_db: float = -40.0) -> np.ndarray:
        """Trim leading/trailing silence using an energy threshold.

        Args:
            audio: Mono audio array (float32), shape (n_samples,).
            threshold_db: Energy threshold in dBFS relative to full scale.
                -40 dBFS is very safe and will not clip normal speech.

        Returns:
            Trimmed audio array. If the entire clip is below threshold,
            returns the original to avoid producing an empty file.
        """
        if audio.size == 0:
            return audio

        energy = np.abs(audio)
        threshold = 10 ** (threshold_db / 20.0)
        mask = energy > threshold

        if not np.any(mask):
            return audio  # All silence; keep original

        start = np.argmax(mask)
        end = len(mask) - np.argmax(mask[::-1])
        return audio[start:end]

    def _write_wav(self) -> Path:
        audio = np.concatenate(self._chunks, axis=0) if self._chunks else np.zeros((0, 1))
        audio = np.clip(audio[:, 0], -1.0, 1.0)
        original_len = len(audio)
        audio = self._trim_silence(audio)
        _LOGGER.debug("Trimmed silence: %d -> %d samples", original_len, len(audio))
        pcm16 = (audio * 32767).astype(np.int16)

        handle = tempfile.NamedTemporaryFile(prefix="vocero-", suffix=".wav", delete=False)
        handle.close()
        path = Path(handle.name)

        try:
            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(pcm16.tobytes())
        except Exception as exc:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"Failed to write WAV file {path}: {exc}") from exc

        return path
