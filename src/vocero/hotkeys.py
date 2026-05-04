from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class GlobalHotkeyListener:
    """Best-effort global hold hotkey listener backed by pynput."""

    def __init__(
        self,
        hotkey: str,
        on_pressed: Callable[[], None],
        on_released: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.hotkey = hotkey
        self._on_pressed = on_pressed
        self._on_released = on_released
        self._on_error = on_error
        self._listener = None
        self._target_keys = set()
        self._pressed_keys = set()
        self._active = False

    def start(self) -> None:
        try:
            from pynput import keyboard

            raw_targets = set(keyboard.HotKey.parse(self.hotkey))
            self._target_keys = {self._canonical(k) for k in raw_targets}
            logger.debug("Parsed hotkey %r -> %s", self.hotkey, self._target_keys)
            self._listener = keyboard.Listener(
                on_press=self._handle_press,
                on_release=self._handle_release,
            )
            self._listener.start()
            logger.debug("Hotkey listener started, waiting for %s", self.hotkey)
        except Exception as exc:
            logger.debug("Hotkey parse failed: %s", exc)
            self._on_error(f"No pude registrar el hotkey {self.hotkey}: {exc}")

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _handle_press(self, key) -> None:
        key = self._canonical(key)
        if key in self._pressed_keys:
            # Ignore OS key-repeat events for already-held keys
            return
        if key in self._target_keys:
            self._pressed_keys.add(key)
        logger.debug("Press %s, pressed=%s, target=%s, active=%s", key, self._pressed_keys, self._target_keys, self._active)

        if not self._active and self._target_keys.issubset(self._pressed_keys):
            self._active = True
            self._on_pressed()

    def _handle_release(self, key) -> None:
        key = self._canonical(key)
        self._pressed_keys.discard(key)
        logger.debug("Release %s, pressed=%s, target=%s, active=%s", key, self._pressed_keys, self._target_keys, self._active)

        if self._active and not self._target_keys.issubset(self._pressed_keys):
            self._active = False
            self._on_released()

    def _canonical(self, key):
        from pynput.keyboard import KeyCode

        if self._listener is not None:
            key = self._listener.canonical(key)

        # Use virtual key code for character keys so that shifted symbols
        # (e.g. ':' when Shift+'.' is pressed) still match the target.
        if isinstance(key, KeyCode) and key.vk is not None:
            return KeyCode.from_vk(key.vk)
        return key
