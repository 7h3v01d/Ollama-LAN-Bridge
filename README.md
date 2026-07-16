# 📡 Ollama LAN Bridge

A lightweight Python bridge to run high-performance LLMs (like Llama 3.3 70B and Codestral) on a powerful server PC and access them from a less powerful client machine over a local network.

⚠️ **LICENSE & USAGE NOTICE — READ FIRST**

This repository is **source-available for private technical evaluation and testing only**.

- ❌ No commercial use  
- ❌ No production use  
- ❌ No academic, institutional, or government use  
- ❌ No research, benchmarking, or publication  
- ❌ No redistribution, sublicensing, or derivative works  
- ❌ No independent development based on this code  

All rights remain exclusively with the author.  
Use of this software constitutes acceptance of the terms defined in **LICENSE.txt**.

---

## 🚀 Key Features

- **LAN Auto-Discovery:** Scans your local subnet on startup and finds Ollama servers automatically — no need to know or type an IP.
- **Remembers Your Last Connection:** Saves the last server + model to `~/.ollama_bridge.json` and offers to reconnect instantly next time, skipping the scan.
- **VRAM Management:** Automatically unloads the previous model before loading a new one to prevent GPU memory overflow.
- **Idle Auto-Unload:** Frees the GPU on its own after a period of inactivity, no need to remember to type `exit`.
- **Reconnect on Drop:** Automatically retries once if the connection hiccups mid-request instead of just dying.
- **In-Chat Commands:** `/model`, `/system`, `/save`, `/clear`, `/stats` — switch models, set a system prompt, save transcripts, and check performance without leaving the chat.
- **Safe Cancel:** Ctrl+C during a response cancels just that reply, not the whole session.
- **Context Trimming:** Automatically caps conversation history so long sessions on big models don't slow to a crawl.
- **Network Stability:** Built-in retry logic and extended timeouts for loading massive models (70B+).
- **Performance Tracking:** Real-time benchmark data (tokens per second) for every response.
- **Stateless Bridge:** A clean `OllamaManager` class you can drop into any other Python project.

## 🛠️ Setup Instructions

### 1. The Server (Powerhouse PC)

1. Install [Ollama](https://ollama.com).
2. Set the environment variable `OLLAMA_HOST` to `0.0.0.0` (This allows network connections).
3. Ensure Windows Firewall allows inbound traffic on port `11434`.

### 2. The Client (Struggling PC)

1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
Run it:
```Bash
python src/gui.py
```
On startup, if you've connected before, it'll offer to reconnect to your last server + model instantly. Otherwise it scans your LAN for an Ollama server automatically, falling back to a manual IP prompt (defaults to `192.168.0.163`). To skip both entirely:
```Bash
set OLLAMA_HOST_IP=192.168.0.163
python src/gui.py
```
By default the model auto-unloads from VRAM after 5 minutes idle, and conversation history is capped at 40 messages to keep prompts fast on big models. Adjust or disable either with:
```Bash
set OLLAMA_IDLE_TIMEOUT=600
:: or 0 to disable auto-unload entirely
set OLLAMA_MAX_HISTORY=100
:: or 0 to disable trimming entirely
```

### 💬 In-Chat Commands
While chatting, type any of these instead of a message:

- `/model` — switch to a different model (clears context)
- `/system <text>` — set a system prompt for the rest of the session (`/system` alone clears it)
- `/save` — save the conversation to a `.md` file
- `/clear` — clear context, keep the same model
- `/stats` — show average tokens/sec for the session
- `/help` — list commands

Ctrl+C during a response cancels just that reply — you'll land back at the prompt, not get kicked out of the program.

### 📂 Project Structure

- `src/ollama_client.py`: The core logic for network communication, discovery, and VRAM management.
- `src/gui.py`: A terminal-based interface for chatting and benchmarking.
- `tests/`: Pytest suite covering both of the above (see Testing below).

### ✅ Testing

The suite mocks all network calls (`requests`, `socket`, and the Ollama client itself), so it runs instantly with no server or GPU required.

```bash
pip install -r requirements-dev.txt
pytest
```

Covers: model listing and its error paths, VRAM unload/switch behavior, the reconnect-on-drop retry, idle auto-unload logic, LAN discovery's graceful failure when no network is available, config persistence (remembering your last server/model), connection-resolution priority (env var > remembered config > discovery), model selection edge cases, history trimming, and transcript saving.

### 📊 Performance Note
Since this runs over LAN, network latency is negligible. The speed is determined entirely by the GPU of the server machine. 70B models may take 30-60 seconds to "wake up" the first time they are loaded into VRAM.

---

### Contribution Policy

Feedback, bug reports, and suggestions are welcome.

You may submit:

- Issues
- Design feedback
- Pull requests for review

However:

- Contributions do not grant any license or ownership rights
- The author retains full discretion over acceptance and future use
- Contributors receive no rights to reuse, redistribute, or derive from this code

---

### License
This project is not open-source.

It is licensed under a private evaluation-only license.
See LICENSE.txt for full terms.