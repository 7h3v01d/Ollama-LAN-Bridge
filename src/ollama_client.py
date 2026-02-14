import ollama
import requests

class OllamaManager:
    def __init__(self, host='192.168.0.163', port=11434):
        self.base_url = f'http://{host}:{port}'
        self.client = ollama.Client(host=self.base_url, timeout=180) 
        self.active_model = None

    def get_models(self):
        """Returns a list of models available on the remote server."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return [m['name'] for m in resp.json().get('models', [])] if resp.status_code == 200 else []
        except:
            return []

    def unload_current(self):
        """Manually ejects the active model from VRAM."""
        if self.active_model:
            print(f"[*] Cleaning VRAM: Unloading {self.active_model}...")
            try:
                requests.post(f"{self.base_url}/api/chat", 
                              json={"model": self.active_model, "keep_alive": 0}, timeout=5)
                self.active_model = None
            except:
                pass

    def chat_safe(self, model_name, messages):
        """Ensures VRAM is clear before switching models."""
        if self.active_model and self.active_model != model_name:
            self.unload_current()
        
        self.active_model = model_name
        try:
            return self.client.chat(model=model_name, messages=messages, stream=True)
        except Exception as e:
            print(f"\n[!] Error during chat: {e}")
            return None