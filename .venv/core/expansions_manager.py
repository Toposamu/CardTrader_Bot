from pathlib import Path
import json
import requests

# Percorsi assoluti
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "data/config.json"
DATA_DIR = BASE_DIR / "data"


def get_token():
    """Legge il token JWT dal file config.json."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config["jwt_token"]
    except Exception as e:
        print(f"❌ Errore lettura config: {str(e)}")
        return None


def fetch_expansions_from_api(game_id):
    """Recupera tutte le espansioni di un gioco specifico da CardTrader."""
    try:
        token = get_token()
        if not token:
            return []

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            "https://api.cardtrader.com/api/v2/expansions",
            headers=headers
        )
        response.raise_for_status()

        # Filtra solo le espansioni del gioco specifico
        all_expansions = response.json()
        return [exp for exp in all_expansions if exp.get("game_id") == game_id]
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore API: {str(e)}")
        return []


def load_local_expansions(game_name):
    """Carica la lista locale delle espansioni salvate."""
    try:
        file_path = DATA_DIR / game_name / "expansions.json"
        if not file_path.exists():
            print(f"❌ File locale non trovato: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Errore durante il caricamento delle espansioni locali: {str(e)}")
        return []


def save_expansions(expansions, game_name):
    """Salva la lista delle espansioni in formato JSON."""
    try:
        save_path = DATA_DIR / game_name / "expansions.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(expansions, f, indent=2, ensure_ascii=False)

        print(f"✅ Salvate {len(expansions)} espansioni in {save_path}")
    except Exception as e:
        print(f"❌ Errore durante il salvataggio: {str(e)}")


def check_and_update_expansions(game_id, game_name):
    """Confronta la lista locale con quella remota e aggiorna se necessario."""
    # Recupera le espansioni da CardTrader
    remote_expansions = fetch_expansions_from_api(game_id)

    if not remote_expansions:
        print("❌ Nessuna espansione trovata nell'API.")
        return

    # Carica le espansioni locali
    local_expansions = load_local_expansions(game_name)

    # Confronta le due liste
    if remote_expansions != local_expansions:
        print("🔄 Differenze trovate! Aggiornamento della lista locale...")
        save_expansions(remote_expansions, game_name)
    else:
        print("✅ La lista locale è già aggiornata.")
