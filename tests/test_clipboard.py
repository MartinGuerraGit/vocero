import subprocess

from vocero.clipboard import ClipboardInserter, InsertResult


class FakeClipboard:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


def test_copy_puts_text_on_clipboard():
    clipboard = FakeClipboard()
    inserter = ClipboardInserter(clipboard)

    result = inserter.copy("hola")

    assert clipboard.text == "hola"
    assert result.status == InsertResult.COPIED_ONLY


def test_best_effort_insert_falls_back_when_no_tool(monkeypatch):
    clipboard = FakeClipboard()
    inserter = ClipboardInserter(clipboard)

    monkeypatch.setattr("vocero.clipboard.shutil.which", lambda name: None)

    result = inserter.insert_with_best_effort("prompt")

    assert clipboard.text == "prompt"
    assert result.status == InsertResult.COPIED_ONLY
    assert "copiado" in result.message.lower()


def test_wayland_uses_wtype_when_available(monkeypatch):
    clipboard = FakeClipboard()
    inserter = ClipboardInserter(clipboard)
    calls = []

    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(
        "vocero.clipboard.shutil.which",
        lambda name: f"/usr/bin/{name}" if name == "wtype" else None,
    )
    monkeypatch.setattr(
        "vocero.clipboard.subprocess.run",
        lambda command, **kwargs: calls.append(command),
    )

    result = inserter.insert_with_best_effort("prompt")

    assert result.status == InsertResult.TYPED
    assert calls == [["wtype", "prompt"]]


def test_fallback_to_paste_when_type_fails(monkeypatch):
    clipboard = FakeClipboard()
    inserter = ClipboardInserter(clipboard)
    calls = []

    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.setattr(
        "vocero.clipboard.shutil.which",
        lambda name: f"/usr/bin/{name}" if name == "xdotool" else None,
    )

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[0] == "xdotool" and command[1] == "type":
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr("vocero.clipboard.subprocess.run", fake_run)

    result = inserter.insert_with_best_effort("prompt")

    assert any(cmd[0] == "xdotool" and cmd[1] == "type" for cmd in calls)
    assert any(cmd[0] == "xdotool" and cmd[1] == "key" for cmd in calls)
    assert result.status == InsertResult.PASTED


def test_fallback_to_clipboard_when_no_tools(monkeypatch):
    clipboard = FakeClipboard()
    inserter = ClipboardInserter(clipboard)

    monkeypatch.setattr("vocero.clipboard.shutil.which", lambda name: None)

    result = inserter.insert_with_best_effort("prompt")

    assert clipboard.text == "prompt"
    assert result.status == InsertResult.COPIED_ONLY
