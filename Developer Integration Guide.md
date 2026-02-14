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

`OllamaManager(host, port)`

-	`host`: The IP of your server (default: '192.168.0.163').
-	`port`: The port Ollama is listening on (default: 11434).

`.chat_safe(model_name, messages)`
The most important method. It handles "VRAM Hygiene."

-	Logic: If the `model_name` is different from the last model used, it automatically triggers an unload of the old model before starting the new one.
-	Returns: A generator object (stream).
  
.`unload_current()`
-	Use case: Call this in your application's "Shutdown" or "Clean up" routine to ensure your server's GPU is freed up immediately when your app closes.
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

