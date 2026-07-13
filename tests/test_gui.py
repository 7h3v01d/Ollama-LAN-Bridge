import json
import os
from unittest.mock import MagicMock, patch

import gui


# --- config persistence ----------------------------------------------------

def test_save_and_load_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(gui, "CONFIG_PATH", str(tmp_path / "config.json"))
    gui.save_config("192.168.1.5", "llama3.3:70b")
    assert gui.load_config() == {"host": "192.168.1.5", "model": "llama3.3:70b"}


def test_load_config_missing_file_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(gui, "CONFIG_PATH", str(tmp_path / "does_not_exist.json"))
    assert gui.load_config() == {}


def test_load_config_corrupt_file_returns_empty_dict(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("{not valid json")
    monkeypatch.setattr(gui, "CONFIG_PATH", str(path))
    assert gui.load_config() == {}


def test_save_config_survives_unwritable_path(tmp_path, monkeypatch):
    # Point at a path inside a directory that doesn't exist -> OSError on open().
    monkeypatch.setattr(gui, "CONFIG_PATH", str(tmp_path / "nope" / "config.json"))
    gui.save_config("192.168.1.5", "llama3.3:70b")  # should not raise


# --- resolve_connection: env var > remembered config > discovery -----------

def test_resolve_connection_env_var_takes_priority(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST_IP", "10.0.0.9")
    with patch("gui.discover_or_prompt") as mock_discover:
        host, model = gui.resolve_connection({"host": "192.168.1.5", "model": "codestral"})
    assert (host, model) == ("10.0.0.9", None)
    mock_discover.assert_not_called()


def test_resolve_connection_reuses_remembered_config_on_yes(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST_IP", raising=False)
    with patch("builtins.input", return_value="y"), patch("gui.discover_or_prompt") as mock_discover:
        host, model = gui.resolve_connection({"host": "192.168.1.5", "model": "codestral"})
    assert (host, model) == ("192.168.1.5", "codestral")
    mock_discover.assert_not_called()


def test_resolve_connection_declining_remembered_config_falls_back_to_discovery(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST_IP", raising=False)
    with patch("builtins.input", return_value="n"), patch("gui.discover_or_prompt", return_value="192.168.1.99") as mock_discover:
        host, model = gui.resolve_connection({"host": "192.168.1.5", "model": "codestral"})
    assert (host, model) == ("192.168.1.99", None)
    mock_discover.assert_called_once()


def test_resolve_connection_no_config_goes_straight_to_discovery(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST_IP", raising=False)
    with patch("gui.discover_or_prompt", return_value="192.168.1.99") as mock_discover:
        host, model = gui.resolve_connection({})
    assert (host, model) == ("192.168.1.99", None)
    mock_discover.assert_called_once()


# --- select_model ------------------------------------------------------------

def test_select_model_uses_preferred_when_still_available():
    ai = MagicMock()
    ai.get_models.return_value = ["codestral", "llama3.3:70b"]
    with patch("builtins.input") as mock_input:
        model, models = gui.select_model(ai, preferred="llama3.3:70b")
    assert model == "llama3.3:70b"
    mock_input.assert_not_called()  # shouldn't need to prompt at all


def test_select_model_prompts_when_preferred_no_longer_available():
    ai = MagicMock()
    ai.get_models.return_value = ["codestral", "llama3.3:70b"]
    with patch("builtins.input", return_value="1"):
        model, models = gui.select_model(ai, preferred="mistral")  # no longer on the server
    assert model == "llama3.3:70b"


def test_select_model_prompts_when_no_preference_given():
    ai = MagicMock()
    ai.get_models.return_value = ["codestral", "llama3.3:70b"]
    with patch("builtins.input", return_value="0"):
        model, models = gui.select_model(ai)
    assert model == "codestral"


def test_select_model_handles_invalid_index():
    ai = MagicMock()
    ai.get_models.return_value = ["codestral"]
    with patch("builtins.input", return_value="99"):
        model, models = gui.select_model(ai)
    assert model is None
    assert models == ["codestral"]  # list is still returned so caller knows server was reachable


def test_select_model_handles_non_numeric_input():
    ai = MagicMock()
    ai.get_models.return_value = ["codestral"]
    with patch("builtins.input", return_value="banana"):
        model, models = gui.select_model(ai)
    assert model is None


def test_select_model_no_server_models_returns_none_none():
    ai = MagicMock()
    ai.get_models.return_value = []
    model, models = gui.select_model(ai)
    assert (model, models) == (None, None)


# --- trim_history ------------------------------------------------------------

def test_trim_history_caps_to_max_messages():
    history = [{"role": "user", "content": str(i)} for i in range(50)]
    trimmed = gui.trim_history(history, 10)
    assert len(trimmed) == 10
    assert trimmed[-1]["content"] == "49"


def test_trim_history_disabled_when_max_is_none():
    history = [{"role": "user", "content": str(i)} for i in range(50)]
    assert gui.trim_history(history, None) == history


def test_trim_history_noop_when_under_the_cap():
    history = [{"role": "user", "content": "hi"}]
    assert gui.trim_history(history, 40) == history


# --- save_history --------------------------------------------------------

def test_save_history_writes_readable_transcript(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    gui.save_history(history, "llama3.3:70b")
    saved_files = list(tmp_path.glob("chat_llama3.3-70b_*.md"))
    assert len(saved_files) == 1
    content = saved_files[0].read_text(encoding="utf-8")
    assert "hello" in content and "hi there" in content
    assert "**You**" in content and "**AI**" in content


def test_save_history_with_empty_history_does_not_create_a_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    gui.save_history([], "llama3.3:70b")
    assert list(tmp_path.glob("*.md")) == []
    assert "Nothing to save" in capsys.readouterr().out
