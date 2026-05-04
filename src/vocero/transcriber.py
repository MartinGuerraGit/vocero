from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class Transcription:
    text: str
    language: str | None
    language_probability: float | None
    duration: float | None


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> Transcription:
        """Return a transcription for a local audio file."""


class FasterWhisperTranscriber:
    """Lazy faster-whisper wrapper so the model is loaded only when needed."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = "es",
        cpu_threads: int = 0,
        beam_size: int = 1,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.cpu_threads = cpu_threads
        self.beam_size = beam_size
        self._model = None

    def transcribe(self, audio_path: Path) -> Transcription:
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        model = self._get_model()
        try:
            segments, info = model.transcribe(
                str(audio_path),
                beam_size=self.beam_size,
                language=self.language,
                vad_filter=True,
                temperature=0.0,  # Prevent expensive fallback retry loop
            )
        except Exception as exc:
            raise RuntimeError(
                f"Transcription failed for {audio_path}: {exc}"
            ) from exc

        text = " ".join(segment.text.strip() for segment in segments).strip()
        return Transcription(
            text=text,
            language=getattr(info, "language", None),
            language_probability=getattr(info, "language_probability", None),
            duration=getattr(info, "duration", None),
        )

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper is required for local transcription. "
                    'Install dependencies with: pip install -e ".[dev]"'
                ) from exc

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
        return self._model
