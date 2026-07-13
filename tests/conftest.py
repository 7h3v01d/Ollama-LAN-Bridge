import os
import sys

# Make src/ importable as plain modules (gui, ollama_client) without turning
# the project into an installable package — keeps the "simple bridge" nature intact.
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
