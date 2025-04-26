import requests
import json
from pathlib import Path




def get_token():
    """Legge il token JWT dal file config.json"""
    config_file = Path(__file__).resolve().parent.parent / "data" / "config.json"
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config["jwt_token"]
    except Exception as e:
        raise FileNotFoundError(f"❌ Errore lettura config.json: {str(e)}")


def fetch_prices(blueprint_id):
    """Recupera i prezzi di mercato per una carta specifica"""
    jwt_token = get_token()
    headers = {'Authorization': f'Bearer {jwt_token}'}
    url = 'https://api.cardtrader.com/api/v2/marketplace/products'

    try:
        response = requests.get(
            url,
            headers=headers,
            params={
                'blueprint_id': blueprint_id,
                'condition': 'Near Mint',
                'per_page': 100,
                'sort_by': 'price_asc'
            },
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"❌ Errore API: {str(e)}")


def analyze_price_differences(data, blueprint_id):
    """Analizza le differenze di prezzo con supplemento per assenza hub"""
    if not data or str(blueprint_id) not in data:
        print("❌ Nessun dato trovato o formato risposta non valido")
        return

    # Raggruppa le offerte per lingua con supplemento hub
    lang_groups = {}
    for product in data[str(blueprint_id)]:
        lang = product['properties_hash'].get('onepiece_language', 'unknown')
        price_eur = product['price_cents'] / 100
        hub = product['user']['can_sell_via_hub']

        # Aggiungi supplemento se non disponibile via hub
        if not hub:
            print(f"⚠️ Applicato supplemento 3€ a {price_eur}€ (senza hub)")
            price_eur += 3

        if lang not in lang_groups:
            lang_groups[lang] = []

        lang_groups[lang].append(price_eur)

    # Analizza ogni gruppo linguistico
    for lang, prices in lang_groups.items():
        sorted_prices = sorted(prices)
        lang_name = {
            'en': 'Inglese',
            'jp': 'Giapponese',
            'fr': 'Francese',
            'kr': 'Coreano',
            'zh-CN': 'Cinese'
        }.get(lang, lang.title())  # Default al codice lingua in title case

        print(f"\n📌 Analisi per lingua: {lang_name}")

        # Confronto 1°-2° prezzo
        if len(sorted_prices) >= 2:
            price1 = sorted_prices[0]
            price2 = sorted_prices[1]
            diff_abs = round(price2 - price1, 2)
            diff_pct = round(((price2 - price1) / price1) * 100, 2)
            print(f"• 1°-2° prezzo: €{diff_abs} ({diff_pct}%)")
        else:
            print("• Non ci sono abbastanza offerte per il confronto 1°-2°")

        # Confronto 2°-3° prezzo
        if len(sorted_prices) >= 3:
            price2 = sorted_prices[1]
            price3 = sorted_prices[2]
            diff_abs = round(price3 - price2, 2)
            diff_pct = round(((price3 - price2) / price2) * 100, 2)
            print(f"• 2°-3° prezzo: €{diff_abs} ({diff_pct}%)")
        else:
            print("• Non ci sono abbastanza offerte per il confronto 2°-3°")


if __name__ == "__main__":
    try:
        blueprint_id = 250098  # ID della carta Rob Lucci
        prices_data = fetch_prices(blueprint_id)
        analyze_price_differences(prices_data, blueprint_id)

    except Exception as e:
        print(f"\n❌ Errore durante l'esecuzione: {str(e)}")
