from vocero.settings import Settings


def test_default_hotkey_avoids_browser_refresh(monkeypatch):
    monkeypatch.delenv("VOCERO_HOTKEY", raising=False)

    settings = Settings.from_env()

    assert settings.hotkey == "<f4>"


def test_settings_from_env_supports_auto_language(monkeypatch):
    monkeypatch.setenv("VOCERO_MODEL", "small")
    monkeypatch.setenv("VOCERO_DEVICE", "cpu")
    monkeypatch.setenv("VOCERO_COMPUTE_TYPE", "int8")
    monkeypatch.setenv("VOCERO_LANGUAGE", "auto")
    monkeypatch.setenv("VOCERO_SAMPLE_RATE", "22050")
    monkeypatch.setenv("VOCERO_HOTKEY", "<ctrl>+<shift>+d")
    monkeypatch.setenv("VOCERO_AUTO_PASTE", "false")
    monkeypatch.setenv("VOCERO_CPU_THREADS", "4")

    settings = Settings.from_env()

    assert settings.model_size == "small"
    assert settings.device == "cpu"
    assert settings.compute_type == "int8"
    assert settings.language is None
    assert settings.sample_rate == 22050
    assert settings.hotkey == "<ctrl>+<shift>+d"
    assert settings.auto_paste is False
    assert settings.cpu_threads == 4


def test_default_cpu_threads():
    settings = Settings()
    assert settings.cpu_threads == 0


def test_settings_from_config_file(monkeypatch, tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        [vocero]
        model_size = "tiny"
        hotkey = "<ctrl>+<alt>+d"
        auto_paste = false
        """,
        encoding="utf-8",
    )
    monkeypatch.setenv("VOCERO_CONFIG", str(config_path))

    settings = Settings.from_env()

    assert settings.model_size == "tiny"
    assert settings.hotkey == "<ctrl>+<alt>+d"
    assert settings.auto_paste is False
