from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from vocero.settings import Settings
from vocero.ui import FloatingDictationWidget


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    settings = Settings.from_env()
    widget = FloatingDictationWidget(settings)
    widget.start_hotkey_listener()
    return app.exec()
