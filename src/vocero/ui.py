from __future__ import annotations

import logging
import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QRegion,
)
from PySide6.QtWidgets import QApplication, QWidget

from vocero.audio import AudioRecorder
from vocero.clipboard import ClipboardInserter
from vocero.hotkeys import GlobalHotkeyListener
from vocero.settings import Settings
from vocero.transcriber import FasterWhisperTranscriber, Transcription, Transcriber

logger = logging.getLogger(__name__)


# ── avatar widget ────────────────────────────────────────────────────────────


class VoceroAvatar(QWidget):
    """Circular microphone avatar that animates with audio input."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level: float = 0.0
        self._target: float = 0.0
        self._status_text: str = ""
        self._status_sub: str = ""
        self._overlay: bool = False
        self._phase: float = 0.0

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(16)  # ~60 fps

        self.setFixedSize(180, 180)

    # -- public API -----------------------------------------------------------

    def set_audio_level(self, level: float) -> None:
        self._target = max(0.0, min(1.0, float(level)))

    def show_status(self, text: str, subtext: str = "") -> None:
        self._status_text = text
        self._status_sub = subtext
        self._overlay = True
        self.update()

    def hide_status(self) -> None:
        self._overlay = False
        self.update()

    # -- animation ------------------------------------------------------------

    def _tick(self) -> None:
        diff = self._target - self._level
        self._level += diff * 0.12
        self._phase = (self._phase + 0.035 + self._level * 0.045) % (math.tau)
        if abs(diff) < 0.0005:
            self._level = self._target
        self.update()

    # -- painting -------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0 - 10.0
        level = self._level
        breath = (math.sin(self._phase * 0.7) + 1.0) / 2.0

        bg = QPainterPath()
        bg.addEllipse(QPointF(cx, cy), r, r)

        # ── 1. outer glow halo ───────────────────────────────────────────────
        if level > 0.01 or breath > 0.3:
            halo_r = r + 6.0 + level * 14.0 + breath * 2.0
            halo_alpha = int(18 + level * 80 + breath * 12)
            halo = QRadialGradient(QPointF(cx, cy), halo_r)
            halo.setColorAt(0.6, QColor(34, 211, 238, halo_alpha))
            halo.setColorAt(0.8, QColor(139, 92, 246, int(halo_alpha * 0.5)))
            halo.setColorAt(1.0, QColor(34, 211, 238, 0))
            p.setBrush(QBrush(halo))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), halo_r, halo_r)
            p.setBrush(Qt.BrushStyle.NoBrush)

        # ── 2. gradient ring (border) ────────────────────────────────────────
        ring_grad = QConicalGradient(QPointF(cx, cy), self._phase * 12)
        ring_grad.setColorAt(0.00, QColor("#22d3ee"))
        ring_grad.setColorAt(0.50, QColor("#8b5cf6"))
        ring_grad.setColorAt(1.00, QColor("#22d3ee"))
        ring_width = 2.0 + level * 3.0 + breath * 0.3
        p.setPen(QPen(QBrush(ring_grad), ring_width))
        p.drawPath(bg)
        p.setPen(Qt.PenStyle.NoPen)

        # ── 3. dark sphere body ──────────────────────────────────────────────
        sphere = QRadialGradient(QPointF(cx, cy - r * 0.15), r * 1.1)
        sphere.setColorAt(0.0, QColor("#1e293b"))
        sphere.setColorAt(0.55, QColor("#0f172a"))
        sphere.setColorAt(1.0, QColor("#020617"))
        p.fillPath(bg, sphere)

        # ── 4. inner luminance ───────────────────────────────────────────────
        lum_alpha = int(20 + breath * 25 + level * 100)
        lum_r = r * (0.5 + level * 0.15 + breath * 0.04)
        luminance = QRadialGradient(QPointF(cx, cy), lum_r)
        luminance.setColorAt(0.0, QColor(34, 211, 238, lum_alpha))
        luminance.setColorAt(0.5, QColor(139, 92, 246, int(lum_alpha * 0.4)))
        luminance.setColorAt(1.0, QColor(15, 23, 42, 0))
        p.setBrush(QBrush(luminance))
        p.drawEllipse(QPointF(cx, cy), lum_r, lum_r)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # ── 5. audio pulse ring ──────────────────────────────────────────────
        self._draw_pulse_ring(p, cx, cy, r, level, breath)

        # ── 6. microphone icon ───────────────────────────────────────────────
        self._draw_mic(p, cx, cy, level, breath)

        # ── 7. status overlay ────────────────────────────────────────────────
        if self._overlay:
            self._draw_status(p, bg, cx, cy, r)

        p.end()

    def _draw_pulse_ring(
        self,
        p: QPainter,
        cx: float,
        cy: float,
        r: float,
        level: float,
        breath: float,
    ) -> None:
        """Single concentric ring that scales and fades with audio amplitude."""
        if level < 0.02 and breath < 0.25:
            return
        intensity = max(level, breath * 0.12)
        ring_r = r * (0.55 + intensity * 0.2 + breath * 0.03)
        alpha = int(30 + level * 150 + breath * 20)
        color = QColor(34, 211, 238, min(255, alpha))
        p.setPen(QPen(color, 1.4 + level * 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)
        p.setPen(Qt.PenStyle.NoPen)

    def _draw_status(
        self, p: QPainter, bg: QPainterPath, cx: float, cy: float, r: float
    ) -> None:
        """Clean status overlay with modern typography."""
        overlay = QColor(15, 23, 42, 210)
        p.fillPath(bg, overlay)

        f = p.font()
        f.setPointSize(12)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#f8fafc"))
        text_rect = QRectF(cx - r + 14, cy - 16, r * 2 - 28, 30)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._status_text)

        if self._status_sub:
            f.setPointSize(9)
            f.setBold(False)
            p.setFont(f)
            p.setPen(QColor("#cbd5e1"))
            sub_rect = QRectF(cx - r + 14, cy + 12, r * 2 - 28, 22)
            p.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self._status_sub)

    def _draw_mic(
        self, p: QPainter, cx: float, cy: float, level: float, breath: float
    ) -> None:
        """Minimal white microphone silhouette."""
        alpha = int(200 + level * 40 + breath * 15)
        color = QColor(255, 255, 255, min(255, alpha))

        mw = 24.0
        mh = 38.0
        cr = 12.0
        top = cy - 12.0

        # ── capsule body ────────────────────────────────────────────────────
        body = QPainterPath()
        body.addRoundedRect(QRectF(cx - mw / 2, top, mw, mh), cr, cr)
        p.fillPath(body, color)

        # ── cradle arc ──────────────────────────────────────────────────────
        arc_w = mw + 12.0
        arc_top = top + mh * 0.35
        arc_h = mh * 0.85
        p.setPen(QPen(color, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(
            QRectF(cx - arc_w / 2, arc_top, arc_w, arc_h),
            int(-10 * 16),
            int(-160 * 16),
        )

        # ── stem ────────────────────────────────────────────────────────────
        stem_top = arc_top + arc_h / 2 + arc_h * 0.38
        stem_bot = stem_top + 10.0
        p.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bot))

        # ── base dot ────────────────────────────────────────────────────────
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(QPointF(cx, stem_bot + 2.5), 3.0, 3.0)
        p.setBrush(Qt.BrushStyle.NoBrush)


# ── workers ──────────────────────────────────────────────────────────────────


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
        except Exception as exc:
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
        except Exception:
            pass
        finally:
            self.finished.emit()


# ── main widget ──────────────────────────────────────────────────────────────


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

        self.avatar = VoceroAvatar(self)
        self._build_window()
        self._connect_signals()
        self.show()
        self._move_to_bottom_center()
        self.avatar.show_status("Vocero", f"Mantené {settings.hotkey} y hablá")

    # ── window setup ────────────────────────────────────────────────────────

    def _build_window(self) -> None:
        self.setWindowTitle("Vocero")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        size = 196
        self.resize(size, size)

        padding = (size - self.avatar.width()) // 2
        self.avatar.move(padding, padding)

        mask = QRegion(0, 0, size, size, QRegion.RegionType.Ellipse)
        self.setMask(mask)

    def _connect_signals(self) -> None:
        self.hotkey_pressed.connect(self.start_push_to_talk)
        self.hotkey_released.connect(self.stop_push_to_talk)
        self.hotkey_error.connect(self._on_hotkey_error)
        self.audio_level_changed.connect(self.avatar.set_audio_level)

    # ── push-to-talk ────────────────────────────────────────────────────────

    def start_hotkey_listener(self) -> None:
        self.hotkey_listener.start()

    def start_push_to_talk(self) -> None:
        if self.worker is not None:
            return
        if self.recorder.is_recording:
            return

        try:
            self.recorder.start()
        except Exception as exc:
            self.avatar.show_status("Error de micrófono", str(exc))
            return

        self.avatar.set_audio_level(0.0)
        self.avatar.hide_status()
        self._move_to_bottom_center()
        self.show()
        self.raise_()

    def stop_push_to_talk(self) -> None:
        if not self.recorder.is_recording:
            return

        try:
            audio_path = self.recorder.stop()
        except Exception as exc:
            self.avatar.show_status("Error de grabación", str(exc))
            return

        self.avatar.set_audio_level(0.0)
        self.avatar.show_status("Transcribiendo...", "esperá un momento")

        self.worker = TranscriptionWorker(self.transcriber, audio_path)
        self.worker.transcribed.connect(self._on_transcribed)
        self.worker.failed.connect(self._on_transcription_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    # ── transcription results ───────────────────────────────────────────────

    def _on_transcribed(self, transcription: Transcription) -> None:
        text = transcription.text.strip()
        if not text:
            self.avatar.show_status("No se detectó texto", "")
            QTimer.singleShot(1500, self.hide)
            return

        if self.settings.auto_paste:
            self.clipboard.insert_with_best_effort(text)
        else:
            self.clipboard.copy(text)
        self.hide()

    def _on_transcription_failed(self, message: str) -> None:
        self.avatar.show_status("Error de transcripción", message)
        self.show()

    def _on_worker_finished(self) -> None:
        self.hide()
        self.worker = None

    def _on_hotkey_error(self, message: str) -> None:
        logger.error("Hotkey error: %s", message)
        self.avatar.show_status("Hotkey no disponible", message)

    # ── positioning ─────────────────────────────────────────────────────────

    def _move_to_bottom_center(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.x() + (geometry.width() - self.width()) // 2
        y = geometry.y() + geometry.height() - self.height() - 72
        self.move(x, y)

    # ── cleanup ─────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
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
