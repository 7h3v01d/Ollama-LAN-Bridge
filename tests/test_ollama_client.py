import time
from unittest.mock import MagicMock, patch

import requests
from ollama_client import OllamaManager


def make_manager(**kwargs):
    """Builds an OllamaManager without starting a real idle-watch thread unless asked."""
    return OllamaManager(host='127.0.0.1', port=11434, **kwargs)


# --- get_models --------------------------------------------------------

def test_get_models_success():
    ai = make_manager()
    fake_resp = MagicMock(status_code=200)
    fake_resp.json.return_value = {"models": [{"name": "llama3.3:70b"}, {"name": "codestral"}]}
    with patch("requests.get", return_value=fake_resp):
        assert ai.get_models() == ["llama3.3:70b", "codestral"]


def test_get_models_bad_status():
    ai = make_manager()
    fake_resp = MagicMock(status_code=500)
    with patch("requests.get", return_value=fake_resp):
        assert ai.get_models() == []


def test_get_models_connection_error():
    ai = make_manager()
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        assert ai.get_models() == []


def test_get_models_timeout():
    ai = make_manager()
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        assert ai.get_models() == []


def test_get_models_touches_activity_timer():
    ai = make_manager()
    ai._last_activity = 0
    fake_resp = MagicMock(status_code=200)
    fake_resp.json.return_value = {"models": []}
    with patch("requests.get", return_value=fake_resp):
        ai.get_models()
    assert ai._last_activity > 0


# --- unload_current ------------------------------------------------------

def test_unload_current_clears_active_model_on_success():
    ai = make_manager()
    ai.active_model = "llama3.3:70b"
    with patch("requests.post", return_value=MagicMock()) as mock_post:
        ai.unload_current()
    assert ai.active_model is None
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["json"]["keep_alive"] == 0


def test_unload_current_keeps_active_model_on_failure():
    ai = make_manager()
    ai.active_model = "llama3.3:70b"
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
        ai.unload_current()
    # Failure shouldn't silently pretend the model was unloaded.
    assert ai.active_model == "llama3.3:70b"


def test_unload_current_noop_when_nothing_active():
    ai = make_manager()
    with patch("requests.post") as mock_post:
        ai.unload_current()
    mock_post.assert_not_called()


# --- chat_safe: VRAM hygiene + reconnect-on-drop -------------------------

def test_chat_safe_unloads_previous_model_on_switch():
    ai = make_manager()
    ai.active_model = "codestral"
    with patch.object(ai, "unload_current") as mock_unload, \
         patch.object(ai.client, "chat", return_value=iter([])):
        ai.chat_safe("llama3.3:70b", [{"role": "user", "content": "hi"}])
    mock_unload.assert_called_once()
    assert ai.active_model == "llama3.3:70b"


def test_chat_safe_no_unload_when_same_model():
    ai = make_manager()
    ai.active_model = "llama3.3:70b"
    with patch.object(ai, "unload_current") as mock_unload, \
         patch.object(ai.client, "chat", return_value=iter([])):
        ai.chat_safe("llama3.3:70b", [{"role": "user", "content": "hi"}])
    mock_unload.assert_not_called()


def test_chat_safe_retries_once_then_succeeds():
    ai = make_manager()
    stream = iter([{"message": {"content": "hi"}}])
    with patch.object(ai.client, "chat", side_effect=[requests.exceptions.ConnectionError, stream]) as mock_chat, \
         patch("time.sleep") as mock_sleep:
        result = ai.chat_safe("llama3.3:70b", [])
    assert result is stream
    assert mock_chat.call_count == 2
    mock_sleep.assert_called_once()


def test_chat_safe_gives_up_after_exhausting_retries():
    ai = make_manager()
    with patch.object(ai.client, "chat", side_effect=requests.exceptions.ConnectionError), \
         patch("time.sleep"):
        result = ai.chat_safe("llama3.3:70b", [], retries=1)
    assert result is None


# --- idle auto-unload -----------------------------------------------------

def test_check_idle_unloads_after_timeout_elapsed():
    ai = make_manager(idle_timeout=60)
    ai._stop_idle.set()  # prevent the real background thread from also running
    ai.active_model = "llama3.3:70b"
    ai._last_activity = time.time() - 120  # well past the 60s timeout
    with patch("requests.post", return_value=MagicMock()):
        ai._check_idle()
    assert ai.active_model is None


def test_check_idle_does_nothing_before_timeout_elapsed():
    ai = make_manager(idle_timeout=60)
    ai._stop_idle.set()
    ai.active_model = "llama3.3:70b"
    ai._last_activity = time.time()  # just touched
    with patch("requests.post") as mock_post:
        ai._check_idle()
    mock_post.assert_not_called()
    assert ai.active_model == "llama3.3:70b"


def test_check_idle_disabled_when_no_timeout_set():
    ai = make_manager()  # idle_timeout=None by default
    ai.active_model = "llama3.3:70b"
    ai._last_activity = 0  # "idle" for the entire epoch
    with patch("requests.post") as mock_post:
        ai._check_idle()
    mock_post.assert_not_called()
    assert ai.active_model == "llama3.3:70b"


def test_touch_resets_last_activity():
    ai = make_manager()
    ai._last_activity = 0
    ai._touch()
    assert ai._last_activity > 0


# --- discover_servers: graceful degradation --------------------------------

def test_discover_servers_returns_empty_list_when_network_unavailable():
    with patch("socket.socket") as mock_socket_cls:
        mock_socket_cls.return_value.connect.side_effect = OSError("network unreachable")
        assert OllamaManager.discover_servers() == []


def test_discover_servers_finds_matching_hosts():
    def fake_socket(family, kind):
        s = MagicMock()
        if kind == 2:  # SOCK_DGRAM — used only to learn our own local IP
            s.getsockname.return_value = ('192.168.1.42', 0)
        else:  # SOCK_STREAM — used for the actual per-host port probe
            # Pretend only 192.168.1.5 has the port open
            s.connect_ex.side_effect = lambda addr: 0 if addr[0] == '192.168.1.5' else 1
        return s

    with patch("socket.socket", side_effect=fake_socket), \
         patch("socket.AF_INET", 2), patch("socket.SOCK_DGRAM", 2), patch("socket.SOCK_STREAM", 1):
        found = OllamaManager.discover_servers(timeout=0.01)
    assert found == ['192.168.1.5']
