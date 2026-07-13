import os
import json
import time
from ollama_client import OllamaManager

DEFAULT_SERVER_IP = '192.168.0.163'
DEFAULT_IDLE_TIMEOUT = 300      # seconds; set OLLAMA_IDLE_TIMEOUT=0 to disable
DEFAULT_MAX_HISTORY = 40        # messages (~20 exchanges); set OLLAMA_MAX_HISTORY=0 to disable trimming
CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.ollama_bridge.json')


def load_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(host, model):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump({"host": host, "model": model}, f)
    except OSError:
        pass  # non-critical, just skip remembering this time


def discover_or_prompt():
    """LAN auto-discovery, falling back to a manual prompt."""
    print("🔍 Scanning LAN for Ollama servers...")
    found = OllamaManager.discover_servers()

    if not found:
        print("   No servers found automatically.")
        return input(f"Server IP [{DEFAULT_SERVER_IP}]: ").strip() or DEFAULT_SERVER_IP

    if len(found) == 1:
        print(f"   Found 1 server: {found[0]}")
        return found[0]

    print(f"   Found {len(found)} servers:")
    for i, ip in enumerate(found):
        print(f"   [{i}] {ip}")
    try:
        idx = int(input("Select server index: "))
        return found[idx]
    except (ValueError, IndexError):
        print("[!] Invalid selection, falling back to manual entry.")
        return input(f"Server IP [{DEFAULT_SERVER_IP}]: ").strip() or DEFAULT_SERVER_IP


def resolve_connection(config):
    """Env var > remembered last connection > LAN discovery/prompt.
    Returns (host, remembered_model_or_None)."""
    env_ip = os.environ.get('OLLAMA_HOST_IP')
    if env_ip:
        return env_ip, None

    if config.get('host'):
        label = f"{config['host']} ({config.get('model', '?')})"
        ans = input(f"Reconnect to last server {label}? [Y/n]: ").strip().lower()
        if ans in ('', 'y', 'yes'):
            return config['host'], config.get('model')

    return discover_or_prompt(), None


def select_model(ai, preferred=None):
    """Fetches the model list and either confirms `preferred` or prompts the user to pick one."""
    models = ai.get_models()
    if not models:
        return None, None

    if preferred and preferred in models:
        return preferred, models

    print(f"\n--- 📡 Available models ---")
    for i, name in enumerate(models):
        print(f" [{i}] {name}")

    try:
        idx = int(input("\nSelect model index: "))
        return models[idx], models
    except ValueError:
        print("[!] Please enter a number.")
        return None, models
    except IndexError:
        print(f"[!] Invalid index. Choose between 0 and {len(models) - 1}.")
        return None, models


def print_help():
    print(
        "\nCommands:\n"
        "  /model         Switch to a different model (clears context)\n"
        "  /system <text> Set a system prompt for the rest of the session\n"
        "  /system        (no text) Clear the current system prompt\n"
        "  /save          Save the current conversation to a file\n"
        "  /clear         Clear conversation context (keeps the same model)\n"
        "  /stats         Show average tokens/sec for this session\n"
        "  /help          Show this list\n"
        "  exit           Unload the model and quit"
    )


def save_history(history, model):
    if not history:
        print("[!] Nothing to save yet.")
        return
    filename = f"chat_{model.replace(':', '-')}_{time.strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Chat with {model}\n\n")
        for msg in history:
            role = "**You**" if msg["role"] == "user" else "**AI**"
            f.write(f"{role}: {msg['content']}\n\n")
    print(f"[*] Saved conversation to {filename}")


def trim_history(history, max_messages):
    """Keeps only the most recent `max_messages` (user+assistant pairs) to keep prompts fast."""
    if max_messages and len(history) > max_messages:
        return history[-max_messages:]
    return history


def main():
    config = load_config()
    SERVER_IP, remembered_model = resolve_connection(config)

    idle_env = os.environ.get('OLLAMA_IDLE_TIMEOUT')
    idle_timeout = DEFAULT_IDLE_TIMEOUT if idle_env is None else int(idle_env)
    idle_timeout = idle_timeout or None  # 0 disables it

    max_history_env = os.environ.get('OLLAMA_MAX_HISTORY')
    max_history = DEFAULT_MAX_HISTORY if max_history_env is None else int(max_history_env)
    max_history = max_history or None  # 0 disables trimming

    ai = OllamaManager(host=SERVER_IP, idle_timeout=idle_timeout)

    model, models = select_model(ai, preferred=remembered_model)
    if not models:
        print(f"❌ Cannot connect to {SERVER_IP}. Check firewall/Ollama status.")
        return
    if not model:
        return

    save_config(SERVER_IP, model)

    print(f"\n--- 📡 Connected to {SERVER_IP} ---")
    if idle_timeout:
        print(f"[*] Auto-unload after {idle_timeout}s idle. Type /help for commands.")

    history = []
    system_prompt = None
    session_speeds = []
    print(f"\n--- Chatting with {model} (Type 'exit' to quit, /help for commands) ---")

    try:
        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'exit':
                break

            if user_input.startswith('/'):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == '/help':
                    print_help()
                elif cmd == '/clear':
                    history = []
                    print("[*] Context cleared.")
                elif cmd == '/save':
                    save_history(history, model)
                elif cmd == '/stats':
                    if session_speeds:
                        avg = sum(session_speeds) / len(session_speeds)
                        print(f"[📊] Avg speed this session: {avg:.2f} t/s over {len(session_speeds)} replies")
                    else:
                        print("[!] No completed replies yet.")
                elif cmd == '/system':
                    if arg:
                        system_prompt = arg
                        print(f"[*] System prompt set: \"{arg}\"")
                    else:
                        system_prompt = None
                        print("[*] System prompt cleared.")
                elif cmd == '/model':
                    new_model, new_list = select_model(ai)
                    if new_model:
                        model = new_model
                        history = []
                        save_config(SERVER_IP, model)
                        print(f"[*] Switched to {model}. Context cleared.")
                else:
                    print(f"[!] Unknown command: {user_input}. Type /help for the list.")
                continue

            history.append({"role": "user", "content": user_input})
            history = trim_history(history, max_history)
            print("AI: ", end="", flush=True)

            outgoing = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + history
            full_response = ""
            stream = ai.chat_safe(model, outgoing)

            if stream:
                final_chunk = None
                try:
                    for chunk in stream:
                        content = chunk['message']['content']
                        print(content, end="", flush=True)
                        full_response += content
                        final_chunk = chunk
                except KeyboardInterrupt:
                    print("\n[!] Response cancelled.")
                except Exception as e:
                    print(f"\n[!] Connection dropped mid-response: {e}")

                if full_response:
                    history.append({"role": "assistant", "content": full_response})

                # Show performance (only if we got a clean final chunk)
                if final_chunk and final_chunk.get('eval_count') and final_chunk.get('eval_duration'):
                    tps = final_chunk['eval_count'] / (final_chunk['eval_duration'] / 1e9)
                    session_speeds.append(tps)
                    print(f"\n[ 📊 Speed: {tps:.2f} t/s ]")
            else:
                print("\n[!] Connection error. Check that the server is still reachable.")
    except KeyboardInterrupt:
        print("\n[!] Interrupted.")
    finally:
        ai.unload_current()
        ai.stop_idle_watch()

if __name__ == "__main__":
    main()
