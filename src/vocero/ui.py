from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from vocero.audio import AudioRecorder
from vocero.clipboard import ClipboardInserter
from vocero.hotkeys import GlobalHotkeyListener
from vocero.settings import Settings
from vocero.transcriber import FasterWhisperTranscriber, Transcription, Transcriber

logger = logging.getLogger(__name__)


class TranscriptionWorker(QThread):
    transcribed = Signal(object)
    failed = Signal(str)

    def __init__(self, transcriber: Transcriber, audio_path: Path) -> None:
        super().__init__()
        self._transcriber = transcriber
        self._audio_path = audio_path

    def run(self) -> None:
        try:
            self.transcribed.emit(self._transcriber.transcribe(self._audio_path))
        except Exception as exc:  # noqa: BLE001 - UI boundary should surface any backend failure.
            self.failed.emit(str(exc))
        finally:
            self._audio_path.unlink(missing_ok=True)


class WarmupWorker(QThread):
    finished = Signal()

    def __init__(self, transcriber: FasterWhisperTranscriber) -> None:
        super().__init__()
        self._transcriber = transcriber

    def run(self) -> None:
        try:
            self._transcriber._get_model()
        except Exception:  # noqa: BLE001 - warm-up failure is non-fatal.
            pass
        finally:
            self.finished.emit()


class FloatingDictationWidget(QWidget):
    hotkey_pressed = Signal()
    hotkey_released = Signal()
    hotkey_error = Signal(str)
    audio_level_changed = Signal(float)

    def __init__(
        self,
        settings: Settings,
        recorder: AudioRecorder | None = None,
        transcriber: Transcriber | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.recorder = recorder or AudioRecorder(
            sample_rate=settings.sample_rate,
            level_callback=self.audio_level_changed.emit,
        )
        self.transcriber = transcriber or FasterWhisperTranscriber(
            model_size=settings.model_size,
            device=settings.device,
            compute_type=settings.compute_type,
            language=settings.language,
            cpu_threads=settings.cpu_threads,
            beam_size=1,
        )
        self._warmup_worker = WarmupWorker(self.transcriber)
        self._warmup_worker.finished.connect(self._warmup_worker.deleteLater)
        self._warmup_worker.start()
        self.clipboard = ClipboardInserter(QApplication.clipboard())
        self.hotkey_listener = GlobalHotkeyListener(
            hotkey=settings.hotkey,
            on_pressed=self.hotkey_pressed.emit,
            on_released=self.hotkey_released.emit,
            on_error=self.hotkey_error.emit,
        )
        self.worker: TranscriptionWorker | None = None

        self.card = QFrame()
        self.title_label = QLabel("Escuchando")
        self.status_label = QLabel(f"Mantené {settings.hotkey} y hablá")
        self.level_bar = QProgressBar()

        self._build_window()
        self._connect_signals()
        self.show()
        self._move_to_bottom_center()

    def _build_window(self) -> None:
        self.setWindowTitle("Vocero")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(440, 132)

        self.card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)

        self.title_label.setObjectName("title")
        self.status_label.setObjectName("status")
        self.level_bar.setRange(0, 100)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedHeight(16)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(10)
        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.level_bar)
        card_layout.addWidget(self.status_label)
        self.card.setLayout(card_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.card)
        self.setLayout(layout)
        self.setStyleSheet(
            """
            QFrame#card {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 18px;
            }
            QLabel#title {
                color: #f9fafb;
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#status {
                color: #9ca3af;
                font-size: 12px;
            }
            QProgressBar {
                background: #1f2937;
                border: 0;
                border-radius: 8px;
            }
            QProgressBar::chunk {
                background: #38bdf8;
                border-radius: 8px;
            }
            """
        )

    def _connect_signals(self) -> None:
        self.hotkey_pressed.connect(self.start_push_to_talk)
        self.hotkey_released.connect(self.stop_push_to_talk)
        self.hotkey_error.connect(self._on_hotkey_error)
        self.audio_level_changed.connect(self._set_audio_level)

    def start_hotkey_listener(self) -> None:
        self.hotkey_listener.start()

    def start_push_to_talk(self) -> None:
        if self.worker is not None:
            return
        if self.recorder.is_recording:
            return

        try:
            self.recorder.start()
        except Exception as exc:  # noqa: BLE001 - show operational audio errors in the widget.
            self._show_overlay("Error de micrófono", str(exc))
            return

        self._set_audio_level(0.0)
        if self.isVisible():
            self.title_label.setText("Escuchando")
            self.status_label.setText("Soltá el hotkey para transcribir")
        else:
            self._show_overlay("Escuchando", "Soltá el hotkey para transcribir")

    def stop_push_to_talk(self) -> None:
        if not self.recorder.is_recording:
            return

        try:
            audio_path = self.recorder.stop()
        except Exception as exc:  # noqa: BLE001
            self._show_overlay("Error de grabación", str(exc))
            return

        self._show_overlay("Transcribiendo...", "espera un momento")

        self.worker = TranscriptionWorker(self.transcriber, audio_path)
        self.worker.transcribed.connect(self._on_transcribed)
        self.worker.failed.connect(self._on_transcription_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_transcribed(self, transcription: Transcription) -> None:
        text = transcription.text.strip()
        if not text:
            self._show_overlay("No se detectó texto", "")
            QTimer.singleShot(1500, self.hide)
            return

        if self.settings.auto_paste:
            self.clipboard.insert_with_best_effort(text)
        else:
            self.clipboard.copy(text)
        self.hide()

    def _on_transcription_failed(self, message: str) -> None:
        self._show_overlay("Error de transcripción", message)
        self.show()

    def _on_worker_finished(self) -> None:
        self.hide()
        self.worker = None

    def _on_hotkey_error(self, message: str) -> None:
        logger.error("Hotkey error: %s", message)
        self._show_overlay("Hotkey no disponible", message)

    def _show_overlay(self, title: str, message: str) -> None:
        self.title_label.setText(title)
        self.status_label.setText(message)
        self._move_to_bottom_center()
        self.show()
        self.raise_()

    def _set_audio_level(self, level: float) -> None:
        self.level_bar.setValue(max(0, min(100, int(level * 100))))

    def _move_to_bottom_center(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.x() + (geometry.width() - self.width()) // 2
        y = geometry.y() + geometry.height() - self.height() - 72
        self.move(x, y)

    def closeEvent(self, event) -> None:
        self.hotkey_listener.stop()
        if self.recorder.is_recording:
            try:
                self.recorder.stop()
            except Exception:
                pass
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(5000)
        if hasattr(self, "_warmup_worker") and self._warmup_worker.isRunning():
            self._warmup_worker.wait(5000)
        super().closeEvent(event)
