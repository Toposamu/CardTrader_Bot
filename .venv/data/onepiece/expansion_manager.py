# data/onepiece/expansion_manager.py
import json
from pathlib import Path

EXCLUDED_FILE = Path(__file__).resolve().parent / "excluded_expansions.json"

def save_excluded_expansions(excluded_expansions):
    with open(EXCLUDED_FILE, "w", encoding="utf-8") as f:
        json.dump(excluded_expansions, f)

def load_excluded_expansions():
    try:
        with open(EXCLUDED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
