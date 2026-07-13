import ollama
import requests
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

OLLAMA_PORT = 11434

class OllamaManager:
    def __init__(self, host='192.168.0.163', port=11434, idle_timeout=None):
        """
        idle_timeout: seconds of inactivity before the active model is auto-unloaded.
                      None (default) disables auto-unload — manual unload_current() still works.
        """
        self.base_url = f'http://{host}:{port}'
        self.client = ollama.Client(host=self.base_url, timeout=180) 
        self.active_model = None

        self.idle_timeout = idle_timeout
        self._last_activity = time.time()
        self._stop_idle = threading.Event()
        self._idle_thread = None
        if idle_timeout:
            self._idle_thread = threading.Thread(target=self._idle_watch, daemon=True)
            self._idle_thread.start()

    @staticmethod
    def discover_servers(port=OLLAMA_PORT, timeout=0.3):
        """Scans the local /24 subnet for machines with an Ollama server listening.
        Returns a list of IPs found (may be empty)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            return []

        subnet = '.'.join(local_ip.split('.')[:3])
        found = []

        def check(ip):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                if sock.connect_ex((ip, port)) == 0:
                    found.append(ip)
            except Exception:
                pass
            finally:
                sock.close()

        with ThreadPoolExecutor(max_workers=100) as pool:
            pool.map(check, [f"{subnet}.{i}" for i in range(1, 255)])

        return sorted(found, key=lambda ip: int(ip.split('.')[-1]))

    def _touch(self):
        """Marks the connection as active, resetting the idle-unload timer."""
        self._last_activity = time.time()

    def _idle_watch(self):
        """Background loop: periodically checks whether the active model has gone idle."""
        while not self._stop_idle.is_set():
            time.sleep(5)
            self._check_idle()

    def _check_idle(self):
        """Unloads the active model if it has been idle longer than idle_timeout.
        Split out from _idle_watch so it can be exercised directly in tests."""
        if self.active_model and self.idle_timeout and (time.time() - self._last_activity) > self.idle_timeout:
            print(f"\n[*] Idle for {self.idle_timeout}s — auto-unloading {self.active_model} to free VRAM.")
            self.unload_current()

    def stop_idle_watch(self):
        """Stops the background idle-watch thread (call on shutdown if idle_timeout was used)."""
        self._stop_idle.set()

    def get_models(self):
        """Returns a list of models available on the remote server."""
        self._touch()
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m['name'] for m in resp.json().get('models', [])]
            print(f"[!] Server responded with status {resp.status_code}")
            return []
        except requests.exceptions.ConnectionError:
            print(f"[!] Could not reach {self.base_url} (connection refused/unreachable)")
            return []
        except requests.exceptions.Timeout:
            print(f"[!] Connection to {self.base_url} timed out")
            return []
        except Exception as e:
            print(f"[!] Unexpected error fetching models: {e}")
            return []

    def unload_current(self):
        """Manually ejects the active model from VRAM."""
        if self.active_model:
            print(f"[*] Cleaning VRAM: Unloading {self.active_model}...")
            try:
                requests.post(f"{self.base_url}/api/chat", 
                              json={"model": self.active_model, "keep_alive": 0}, timeout=5)
                self.active_model = None
            except Exception as e:
                print(f"[!] Failed to unload {self.active_model}: {e}")

    def chat_safe(self, model_name, messages, retries=1):
        """Ensures VRAM is clear before switching models. Retries once on a dropped connection."""
        self._touch()
        if self.active_model and self.active_model != model_name:
            self.unload_current()

        self.active_model = model_name
        attempt = 0
        while True:
            try:
                return self.client.chat(model=model_name, messages=messages, stream=True)
            except Exception as e:
                if attempt < retries:
                    attempt += 1
                    print(f"\n[!] Connection hiccup ({e}). Retrying in 2s...")
                    time.sleep(2)
                    continue
                print(f"\n[!] Error during chat: {e}")
                return None