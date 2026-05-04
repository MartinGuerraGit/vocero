from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum

_LOGGER = logging.getLogger(__name__)


class InsertResult(str, Enum):
    """Outcome of an insert-with-best-effort attempt."""

    TYPED = "typed"
    PASTED = "pasted"
    COPIED_ONLY = "copied_only"


@dataclass(frozen=True)
class ClipboardInsertResult:
    """Immutable result of a clipboard/insert operation."""

    status: InsertResult
    message: str


class ClipboardInserter:
    """Clipboard boundary for reliable copy and best-effort Linux paste."""

    def __init__(self, clipboard) -> None:
        self._clipboard = clipboard

    def copy(self, text: str) -> ClipboardInsertResult:
        """Copy *text* to the system clipboard."""
        self._clipboard.setText(text)
        return ClipboardInsertResult(InsertResult.COPIED_ONLY, "Texto copiado al portapapeles.")

    def insert_with_best_effort(self, text: str) -> ClipboardInsertResult:
        """Type *text* into the focused window, falling back to paste or copy."""
        # Try direct typing first
        type_cmd = self._type_command(text)
        if type_cmd is not None:
            try:
                subprocess.run(type_cmd, check=True, timeout=10, capture_output=True)
                return ClipboardInsertResult(
                    InsertResult.TYPED,
                    "Texto insertado directamente.",
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
                _LOGGER.warning("Type command failed: %s", exc)

        # Fallback to clipboard paste
        self._clipboard.setText(text)
        paste_cmd = self._paste_command()
        if paste_cmd is not None:
            time.sleep(0.1)
            try:
                subprocess.run(paste_cmd, check=True, timeout=5.0, capture_output=True)
                return ClipboardInsertResult(
                    InsertResult.PASTED,
                    "Texto pegado en la aplicación activa.",
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
                _LOGGER.warning("Paste command failed: %s", exc)

        # Last resort: copy to clipboard for manual paste
        self._clipboard.setText(text)
        return ClipboardInsertResult(
            InsertResult.COPIED_ONLY,
            "Texto copiado al portapapeles. Instalá wtype, xdotool o ydotool para inserción automática.",
        )

    def _type_command(self, text: str) -> list[str] | None:
        """Return a command list that types *text* character by character, or None."""
        if shutil.which("ydotool"):
            return ["ydotool", "type", text]

        session_type = os.getenv("XDG_SESSION_TYPE", "").lower()
        if session_type == "wayland" and shutil.which("wtype"):
            return ["wtype", text]

        if shutil.which("xdotool"):
            return ["xdotool", "type", "--clearmodifiers", "--delay", "0", text]

        return None

    def _paste_command(self) -> list[str] | None:
        """Return a command list that pastes the clipboard contents, or None."""
        session_type = os.getenv("XDG_SESSION_TYPE", "").lower()

        if session_type == "wayland" and shutil.which("wtype"):
            return ["wtype", "-M", "ctrl", "-P", "v", "-p", "v", "-m", "ctrl"]

        if shutil.which("xdotool"):
            return ["xdotool", "key", "--clearmodifiers", "ctrl+v"]

        if shutil.which("wtype"):
            return ["wtype", "-M", "ctrl", "-P", "v", "-p", "v", "-m", "ctrl"]

        return None
