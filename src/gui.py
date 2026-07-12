import os
import time
from ollama_client import OllamaManager

DEFAULT_SERVER_IP = '192.168.0.163'
DEFAULT_IDLE_TIMEOUT = 300  # seconds; set OLLAMA_IDLE_TIMEOUT=0 to disable


def resolve_server_ip():
    """Env var override > LAN auto-discovery > manual prompt."""
    env_ip = os.environ.get('OLLAMA_HOST_IP')
    if env_ip:
        return env_ip

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


def select_model(ai):
    """Fetches the model list from the server and prompts the user to pick one."""
    models = ai.get_models()
    if not models:
        return None, None

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
        "  /model   Switch to a different model (clears context)\n"
        "  /save    Save the current conversation to a file\n"
        "  /clear   Clear conversation context (keeps the same model)\n"
        "  /stats   Show average tokens/sec for this session\n"
        "  /help    Show this list\n"
        "  exit     Unload the model and quit"
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


def main():
    SERVER_IP = resolve_server_ip()

    idle_env = os.environ.get('OLLAMA_IDLE_TIMEOUT')
    idle_timeout = DEFAULT_IDLE_TIMEOUT if idle_env is None else int(idle_env)
    idle_timeout = idle_timeout or None  # 0 disables it

    ai = OllamaManager(host=SERVER_IP, idle_timeout=idle_timeout)

    model, models = select_model(ai)
    if not models:
        print(f"❌ Cannot connect to {SERVER_IP}. Check firewall/Ollama status.")
        return
    if not model:
        return

    print(f"\n--- 📡 Connected to {SERVER_IP} ---")
    if idle_timeout:
        print(f"[*] Auto-unload after {idle_timeout}s idle. Type /help for commands.")

    history = []
    session_speeds = []
    print(f"\n--- Chatting with {model} (Type 'exit' to quit, /help for commands) ---")

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input:
            continue

        if user_input.lower() == 'exit':
            ai.unload_current()
            ai.stop_idle_watch()
            break

        if user_input.startswith('/'):
            cmd = user_input.lower()
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
            elif cmd == '/model':
                new_model, new_list = select_model(ai)
                if new_model:
                    model = new_model
                    history = []
                    print(f"[*] Switched to {model}. Context cleared.")
            else:
                print(f"[!] Unknown command: {user_input}. Type /help for the list.")
            continue

        history.append({"role": "user", "content": user_input})
        print("AI: ", end="", flush=True)

        full_response = ""
        stream = ai.chat_safe(model, history)

        if stream:
            final_chunk = None
            for chunk in stream:
                content = chunk['message']['content']
                print(content, end="", flush=True)
                full_response += content
                final_chunk = chunk

            history.append({"role": "assistant", "content": full_response})

            # Show performance
            if final_chunk and final_chunk.get('eval_count') and final_chunk.get('eval_duration'):
                tps = final_chunk['eval_count'] / (final_chunk['eval_duration'] / 1e9)
                session_speeds.append(tps)
                print(f"\n[ 📊 Speed: {tps:.2f} t/s ]")
        else:
            print("\n[!] Connection error.")
            break

if __name__ == "__main__":
    main()
