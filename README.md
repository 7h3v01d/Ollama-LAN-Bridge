# 📡 Ollama LAN Bridge

A lightweight Python bridge to run high-performance LLMs (like Llama 3.3 70B and Codestral) on a powerful server PC and access them from a less powerful client machine over a local network.

---

## 🚀 Key Features

- **VRAM Management:** Automatically unloads the previous model before loading a new one to prevent GPU memory overflow.
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
You'll be prompted for the server's IP (defaults to `192.168.0.163` if you just hit Enter). To skip the prompt, set it as an environment variable instead:
```Bash
set OLLAMA_HOST_IP=192.168.0.163
python src/gui.py
```

### 📂 Project Structure

- `src/ollama_client.py`: The core logic for network communication and VRAM management.
- `src/gui.py`: A terminal-based interface for chatting and benchmarking.

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
