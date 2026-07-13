# 📘 Developer Integration Guide: Ollama LAN Bridge

This guide explains how to integrate the `OllamaManager` module into your existing Python applications to leverage high-performance LLMs over your local network.

## 1. Project Ingestion (Setup)

To use the bridge, your project must be able to "see" the `ollama_client.py` file. You have two primary ways to do this:

Option A: Local Import (Simple)<br>
Copy `ollama_client.py` directly into your project's root directory.
```text
your_project/
├── main.py
├── ollama_client.py  <-- Place it here
└── requirements.txt
```
### Option B: Shared Library (Advanced)

If you have multiple projects, you can add the folder containing your bridge to your `PYTHONPATH` or install it in "editable" mode:

```Bash
pip install -e /path/to/olamcon
```
________________________________________

## 2. Core Integration Pattern
The bridge is designed as a Singleton-capable Manager. You should initialize it once and pass the instance to your classes or functions.

**The Standard Hook** 
```Python
from ollama_client import OllamaManager

# Initialize the bridge with your Powerhouse PC's IP
ai_bridge = OllamaManager(host='192.168.0.163')

def process_data(user_query):
    # Always use chat_safe to handle VRAM clearing automatically
    response_stream = ai_bridge.chat_safe(
        model_name="llama3.1:8b", 
        messages=[{"role": "user", "content": user_query}]
    )
    
    # Process the stream
    for chunk in response_stream:
        yield chunk['message']['content']
```
________________________________________

## 3. Developer API Reference

`OllamaManager(host, port, idle_timeout=None)`

-	`host`: The IP of your server (default: '192.168.0.163').
-	`port`: The port Ollama is listening on (default: 11434).
-	`idle_timeout`: Seconds of inactivity before the active model is auto-unloaded from VRAM in the background. `None` (default) disables this — call `unload_current()` yourself when you're done.

`OllamaManager.discover_servers(port=11434, timeout=0.3)` *(static method)*
Scans the caller's local /24 subnet for machines with an Ollama server listening and returns a list of IPs (may be empty). Handy for a zero-config "just find my GPU box" startup flow instead of hardcoding an IP:
```Python
from ollama_client import OllamaManager

candidates = OllamaManager.discover_servers()
host = candidates[0] if candidates else '192.168.0.163'
ai_bridge = OllamaManager(host=host, idle_timeout=300)
```

`.chat_safe(model_name, messages, retries=1)`
The most important method. It handles "VRAM Hygiene."

-	Logic: If the `model_name` is different from the last model used, it automatically triggers an unload of the old model before starting the new one.
-	Resilience: If the connection drops when starting the request, it retries once (2s backoff) before giving up. Note this covers connection failures at request start — a drop mid-stream (server dies while generating) will surface as an exception when you iterate the returned generator, so wrap your iteration loop in a try/except too (see `gui.py` for an example).
-	Returns: A generator object (stream), or `None` if the request ultimately failed.
  
.`unload_current()`
-	Use case: Call this in your application's "Shutdown" or "Clean up" routine to ensure your server's GPU is freed up immediately when your app closes.
-	Note: If you passed `idle_timeout`, this also happens automatically after the given number of idle seconds — call `stop_idle_watch()` on shutdown to stop that background thread.
________________________________________

## 4. Best Practices for Integration

**Handling "Warming Up"**
Large models (70B) can take up to 60 seconds to load into VRAM over the network.
>Developer Tip: When your app starts, consider sending an empty "Pulse" request to preload the model so the user doesn't face a long delay on their first message.

**Error Handling**

Always wrap your AI calls in a try/except block to catch network timeouts:
```Python
try:
    stream = ai_bridge.chat_safe("llama3.1:70b", messages)
except Exception as e:
    print("AI Server Busy or Offline")
```
**Context Persistence**
The bridge does not store history internally by design (to keep it "stateless"). You are responsible for maintaining the `messages` list in your own application state if you want a multi-turn conversation.
________________________________________

## 5. Troubleshooting the Connection

If your integration fails to connect:

1.	Ping Test: Run ping `192.168.0.163` from your client terminal.
2.	API Test: Open a browser and go to `http://192.168.0.163:11434/api/tags`. If it doesn't load a list of models, the Firewall on the powerhouse PC is likely still blocking port 11434.
3.	Admin Rights: Ensure you ran the `setup_ollama_lan.bat` as Administrator on the server.

## 6. Testing

The repo ships a pytest suite (`tests/`) covering `OllamaManager` and the reference CLI, with all network calls mocked — no live server needed:

```Bash
pip install -r requirements-dev.txt
pytest
```

If you're integrating `OllamaManager` into your own app and want to unit test around it, the suite is a useful reference for the mocking points:

- `requests.get` / `requests.post` — patch these to fake `get_models()` and `unload_current()` responses without a real server.
- `ai_bridge.client.chat` — patch this (it's the underlying `ollama.Client`) to fake `chat_safe()` streaming responses.
- `socket.socket` — patch this if you're testing code that calls `discover_servers()`.
- `OllamaManager._check_idle()` — the idle-unload check is split out from the background thread's sleep loop specifically so it can be called directly in a test (set `_last_activity` into the past, call `_check_idle()`, assert `active_model` was cleared) instead of waiting on real time to pass.


