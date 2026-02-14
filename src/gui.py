import os
from ollama_client import OllamaManager

def main():
    # Configuration
    SERVER_IP = '192.168.0.163'
    ai = OllamaManager(host=SERVER_IP)
    
    # 1. Fetch Models
    models = ai.get_models()
    if not models:
        print(f"❌ Cannot connect to {SERVER_IP}. Check firewall/Ollama status.")
        return

    print(f"\n--- 📡 Connected to {SERVER_IP} ---")
    for i, name in enumerate(models):
        print(f" [{i}] {name}")
    
    try:
        idx = int(input("\nSelect model index: "))
        model = models[idx]
    except: return

    # 2. Chat Loop
    history = []
    print(f"\n--- Chatting with {model} (Type 'exit' to quit) ---")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == 'exit':
            ai.unload_current()
            break
            
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
            if final_chunk and 'eval_count' in final_chunk:
                tps = final_chunk['eval_count'] / (final_chunk['eval_duration'] / 1e9)
                print(f"\n[ 📊 Speed: {tps:.2f} t/s ]")
        else:
            print("\n[!] Connection error.")
            break

if __name__ == "__main__":
    main()