from unittest.mock import MagicMock, patch

import pytest

from vocero.hotkeys import GlobalHotkeyListener


class FakeKeyCode:
    def __init__(self, char=None, vk=None):
        self.char = char
        self.vk = vk
        if self.vk is None and self.char is not None:
            self.vk = ord(self.char)

    @classmethod
    def from_vk(cls, vk):
        return cls(char=None, vk=vk)

    def __eq__(self, other):
        if not isinstance(other, FakeKeyCode):
            return NotImplemented
        if self.vk is not None and other.vk is not None:
            return self.vk == other.vk
        return self.char == other.char and self.vk == other.vk

    def __hash__(self):
        if self.vk is not None:
            return hash(self.vk)
        return hash((self.char, self.vk))

    def __repr__(self):
        if self.char:
            return f"KeyCode({self.char!r})"
        return f"KeyCode(vk={self.vk})"


class FakeKey:
    ctrl = "ctrl"
    ctrl_l = "ctrl_l"
    shift = "shift"
    shift_r = "shift_r"
    alt = "alt"
    alt_r = "alt_r"


@pytest.fixture
def mock_keyboard():
    mock_mod = MagicMock()
    mock_mod.KeyCode = FakeKeyCode
    mock_mod.Key = FakeKey

    listener_instance = MagicMock()
    listener_instance.canonical = lambda k: k

    def make_listener(on_press=None, on_release=None):
        listener_instance.on_press = on_press
        listener_instance.on_release = on_release
        return listener_instance

    mock_mod.Listener = MagicMock(side_effect=make_listener)

    def fake_parse(hotkey):
        if hotkey == "invalid":
            raise ValueError("bad hotkey")
        parts = hotkey.replace("<", "").replace(">", "").split("+")
        result = []
        for part in parts:
            part = part.strip()
            if part in ("ctrl", "ctrl_l"):
                result.append(FakeKey.ctrl)
            elif part == "shift":
                result.append(FakeKey.shift)
            elif part == "alt":
                result.append(FakeKey.alt)
            else:
                result.append(FakeKeyCode(char=part))
        return result

    mock_mod.HotKey.parse = staticmethod(fake_parse)

    with patch("pynput.keyboard", mock_mod):
        yield listener_instance


def test_basic_activation(mock_keyboard):
    pressed = []
    released = []

    listener = GlobalHotkeyListener(
        hotkey="<ctrl>+a",
        on_pressed=lambda: pressed.append(True),
        on_released=lambda: released.append(True),
        on_error=lambda msg: pytest.fail(f"Unexpected error: {msg}"),
    )
    listener.start()

    on_press = mock_keyboard.on_press

    on_press(FakeKey.ctrl)
    assert not pressed

    on_press(FakeKeyCode(char="a"))
    assert len(pressed) == 1
    assert not released


def test_release_deactivation(mock_keyboard):
    pressed = []
    released = []

    listener = GlobalHotkeyListener(
        hotkey="<ctrl>+a",
        on_pressed=lambda: pressed.append(True),
        on_released=lambda: released.append(True),
        on_error=lambda msg: pytest.fail(f"Unexpected error: {msg}"),
    )
    listener.start()

    on_press = mock_keyboard.on_press
    on_release = mock_keyboard.on_release

    on_press(FakeKey.ctrl)
    on_press(FakeKeyCode(char="a"))
    assert len(pressed) == 1

    on_release(FakeKeyCode(char="a"))
    assert len(released) == 1
    assert not listener._active


def test_key_repeat_ignored(mock_keyboard):
    pressed = []

    listener = GlobalHotkeyListener(
        hotkey="a",
        on_pressed=lambda: pressed.append(True),
        on_released=lambda: None,
        on_error=lambda msg: pytest.fail(f"Unexpected error: {msg}"),
    )
    listener.start()

    on_press = mock_keyboard.on_press
    a_key = FakeKeyCode(char="a")

    on_press(a_key)
    assert len(pressed) == 1

    # Same object repeated
    on_press(a_key)
    assert len(pressed) == 1

    # Different object with same vk (OS repeat event)
    on_press(FakeKeyCode(char="a"))
    assert len(pressed) == 1


def test_shifted_character_match(mock_keyboard):
    pressed = []

    listener = GlobalHotkeyListener(
        hotkey=".",
        on_pressed=lambda: pressed.append(True),
        on_released=lambda: None,
        on_error=lambda msg: pytest.fail(f"Unexpected error: {msg}"),
    )
    listener.start()

    on_press = mock_keyboard.on_press

    # '.' and ':' share the same vk; pressing Shift+. produces ':'
    colon_key = FakeKeyCode(char=":", vk=ord("."))

    on_press(colon_key)
    assert len(pressed) == 1


def test_canonical_normalization(mock_keyboard):
    pressed = []
    released = []

    def canonical(key):
        if key == FakeKey.ctrl_l:
            return FakeKey.ctrl
        return key

    mock_keyboard.canonical = canonical

    listener = GlobalHotkeyListener(
        hotkey="<ctrl>+a",
        on_pressed=lambda: pressed.append(True),
        on_released=lambda: released.append(True),
        on_error=lambda msg: pytest.fail(f"Unexpected error: {msg}"),
    )
    listener.start()

    on_press = mock_keyboard.on_press
    on_release = mock_keyboard.on_release

    # Use left ctrl; canonical normalizes it to generic ctrl
    on_press(FakeKey.ctrl_l)
    assert not pressed

    on_press(FakeKeyCode(char="a"))
    assert len(pressed) == 1

    on_release(FakeKey.ctrl_l)
    assert len(released) == 1


def test_parse_error_handling(mock_keyboard):
    errors = []

    listener = GlobalHotkeyListener(
        hotkey="invalid",
        on_pressed=lambda: pytest.fail("Should not be called"),
        on_released=lambda: pytest.fail("Should not be called"),
        on_error=lambda msg: errors.append(msg),
    )
    listener.start()

    assert len(errors) == 1
    assert "No pude registrar el hotkey" in errors[0]
    assert "invalid" in errors[0]
