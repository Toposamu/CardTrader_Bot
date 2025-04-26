import json
import requests
from pathlib import Path
from datetime import datetime

def update(game_id, local_file, jwt_token):
    """Aggiorna la lista delle espansioni"""
    try:
        # Carica dati locali
        try:
            with open(local_file, 'r') as f:
                local_data = json.load(f)
        except FileNotFoundError:
            local_data = []

        # Recupera dati remoti
        headers = {'Authorization': f'Bearer {jwt_token}'}
        response = requests.get(
            'https://api.cardtrader.com/api/v2/expansions',
            headers=headers
        )
        response.raise_for_status()
        remote_data = response.json()

        # Filtra per game_id
        filtered_remote = [exp for exp in remote_data if exp.get("game_id") == game_id]

        # Confronto
        local_codes = {exp['code'] for exp in local_data}
        new_expansions = [exp for exp in filtered_remote if exp['code'] not in local_codes]

        # Salvataggio
        if new_expansions:
            merged_data = local_data + new_expansions
            with open(local_file, 'w') as f:
                json.dump(merged_data, f, indent=2)

        # Log timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        log_file = local_file.parent / "last_check.log"
        with open(log_file, 'w') as f:
            f.write(timestamp)

        return (new_expansions, timestamp)

    except Exception as e:
        print(f"❌ Errore durante l'aggiornamento: {str(e)}")
        return ([], None)
