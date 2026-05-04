# Linux MVP Validation Notes

## Supported Path

- `Copy` is the primary insertion path and should work on X11 and Wayland because it only writes to the Qt clipboard.
- `Copy + Paste` is best effort:
  - Wayland: uses `wtype` when available.
  - X11: uses `xdotool` when available.
  - If neither tool exists, Spetex leaves the text copied and asks the user to paste manually.

## Manual Validation Checklist

- Start the app with `spetex` or `python3 -m spetex`.
- Hold the configured hotkey. Default: `<ctrl>+<shift>+.` to avoid conflicts with common developer hotkeys.
- Confirm that the overlay appears only while the hotkey is held.
- Speak a programming prompt and confirm that the sound bar moves with input level.
- Release the hotkey and wait for local transcription.
- Confirm that the result is copied or pasted into the target application.
- Install `wtype` on Wayland or `xdotool` on X11, then test automatic paste.
- Install `xdotool` for automatic paste on X11.

## Known Linux Limitations

- Wayland intentionally restricts cross-application input injection. Automatic paste may depend on compositor policy and installed tools.
- Wayland compositors can also restrict global hotkey listeners. If the listener cannot start, Spetex shows an error overlay.
- Microphone availability depends on the user audio stack and permissions.
- The first `faster-whisper` run may need network access to download the model. Once cached locally, transcription can run offline.
