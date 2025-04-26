import json
from pathlib import Path

# Percorsi dei file
STATE_FILE = Path(__file__).resolve().parent / "saved_state.json"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"


def save_state(languages, rarities):
    """Salva lo stato delle selezioni in un file JSON."""
    state = {
        "languages": languages,
        "rarities": rarities
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print("✅ Stato salvato!")


def load_state():
    """Carica lo stato delle selezioni da un file JSON."""
    if not STATE_FILE.exists():
        return {"languages": [], "rarities": []}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_token():
    """Legge il token JWT dal file config.json"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"❌ File {CONFIG_FILE} non trovato!")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    token = config.get("jwt_token")
    if not token:
        raise ValueError("❌ Token JWT mancante nel config.json!")

    return token
