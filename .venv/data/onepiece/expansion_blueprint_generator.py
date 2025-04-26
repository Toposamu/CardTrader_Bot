import json
import time
from pathlib import Path
import requests


def get_token():
    """Legge il token JWT dal file config.json"""
    config_file = Path(__file__).resolve().parent.parent / "config.json"
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        token = config.get("jwt_token")
        if not token:
            raise ValueError("❌ Token JWT mancante nel config.json!")
        return token
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ File {config_file} non trovato!")
    except ValueError as e:
        raise ValueError(str(e))


def load_expansions():
    """Carica la lista delle espansioni da expansions.json"""
    expansions_file = Path(__file__).resolve().parent / "expansions.json"
    try:
        with open(expansions_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ File {expansions_file} non trovato!")
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ Errore nel parsing di expansions.json: {str(e)}")


def fetch_blueprints(expansion_id, jwt_token):
    """Recupera i blueprint per un'espansione specifica"""
    try:
        headers = {"Authorization": f"Bearer {jwt_token}"}
        response = requests.get(
            f"https://api.cardtrader.com/api/v2/blueprints/export?expansion_id={expansion_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore API per expansion_id {expansion_id}: {str(e)}")
        return None


def process_blueprints(raw_blueprints):
    """Filtra e processa i blueprint per mantenere solo i dati necessari"""
    processed = []
    for bp in raw_blueprints:
        if bp.get("category_id") != 192:  # Filtra solo le carte
            continue

        processed.append({
            "id": bp["id"],
            "name": bp["name"],
            "rarity": bp.get("fixed_properties", {}).get("onepiece_rarity", "Unknown"),
            "collector_number": bp.get("fixed_properties", {}).get("collector_number", ""),
            "image_url": f"https://cardtrader.com{bp['image']['url']}" if bp.get("image") else None,
            "card_url": f"https://www.cardtrader.com/cards/{bp['id']}",
            "card_market_ids": bp.get("card_market_ids", [])
        })
    return processed


def check_and_update_cards(expansion_code=None):
    """Aggiorna le carte per una specifica espansione"""
    if expansion_code:
        print(f"🔍 Processing expansion: {expansion_code}")

    jwt_token = get_token()
    if expansion_code:
        expansions = [exp for exp in load_expansions() if exp["code"] == expansion_code]
    else:
        expansions = load_expansions()  # Solo per chiamate senza parametri

    update_report = {
        "total_expansions": len(expansions),
        "updated_expansions": 0,
        "new_cards": 0,
        "updated_cards": 0,
        "details": {}
    }

    print("🔍 Inizio controllo aggiornamenti carte...")

    for exp in expansions:
        exp_id = exp["id"]
        exp_code = exp["code"]
        local_file = Path(__file__).resolve().parent / "blueprints" / f"{exp_id}.json"

        print(f"\n🔄 Controllo espansione: {exp_code} ({exp['name']})")

        # 1. Recupera dati remoti
        raw_remote = fetch_blueprints(exp_id, jwt_token)
        if not raw_remote:
            print(f"⚠️ Nessun dato remoto trovato per l'espansione {exp_code}")
            continue

        remote_data = process_blueprints(raw_remote)
        if not remote_data:
            print(f"⚠️ Nessuna carta valida trovata per l'espansione {exp_code}")
            continue

        # 2. Carica dati locali
        if not local_file.exists():
            print("⚠️ File locale non trovato, creazione nuovo file...")
            with open(local_file, "w", encoding="utf-8") as f:
                json.dump(remote_data, f, indent=2, ensure_ascii=False)
            update_report["details"][exp_code] = {"action": "created", "new_cards": len(remote_data)}
            update_report["new_cards"] += len(remote_data)
            update_report["updated_expansions"] += 1
            continue

        try:
            with open(local_file, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ Errore nel caricamento del file locale {local_file}: {str(e)}")
            continue

        # 3. Confronta i dati
        local_dict = {card["id"]: card for card in local_data}
        remote_dict = {card["id"]: card for card in remote_data}

        new_cards = [card for card_id, card in remote_dict.items() if card_id not in local_dict]
        updated_cards = []

        # Controlla aggiornamenti per carte esistenti
        for card_id, remote_card in remote_dict.items():
            local_card = local_dict.get(card_id)
            if local_card and local_card != remote_card:
                updated_cards.append({
                    "old": local_card,
                    "new": remote_card
                })

        # 4. Applica aggiornamenti se necessario
        if new_cards or updated_cards:
            merged_data = list(remote_dict.values())
            with open(local_file, "w", encoding="utf-8") as f:
                json.dump(merged_data, f, indent=2, ensure_ascii=False)

            update_report["details"][exp_code] = {
                "new_cards": len(new_cards),
                "updated_cards": len(updated_cards),
                "cards": new_cards + [uc["new"] for uc in updated_cards]
            }
            update_report["new_cards"] += len(new_cards)
            update_report["updated_cards"] += len(updated_cards)
            update_report["updated_expansions"] += 1

            print(f"✅ Trovati {len(new_cards)} nuove carte e {len(updated_cards)} aggiornamenti")

        else:
            print("✅ Nessun aggiornamento necessario")

        time.sleep(0.5)  # Rispetta rate limits

    return update_report


# Per testare prima dell'integrazione nell'interfaccia
if __name__ == "__main__":
    report = check_and_update_cards()
    print("\n📊 Report finale:")
    print(f"• Espansioni aggiornate: {report['updated_expansions']}/{report['total_expansions']}")
    print(f"• Nuove carte: {report['new_cards']}")
    print(f"• Carte aggiornate: {report['updated_cards']}")

    for exp_code, details in report["details"].items():
        print(f"\n📦 Espansione {exp_code}:")
        if "action" in details:
            print(f"• Creato nuovo file con {details['new_cards']} carte")
        else:
            print(f"• Nuove carte: {details['new_cards']}")
            print(f"• Carte aggiornate: {details['updated_cards']}")
