import requests
from pathlib import Path
import json
import time
import threading

def get_token():
    config_file = Path(__file__).resolve().parent.parent / "data" / "config.json"
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config["jwt_token"]

def fetch_card_prices(blueprint_id):
    jwt_token = get_token()
    headers = {'Authorization': f'Bearer {jwt_token}'}
    url = 'https://api.cardtrader.com/api/v2/marketplace/products'
    try:
        response = requests.get(
            url,
            headers=headers,
            params={
                'blueprint_id': blueprint_id,
                'properties[condition]': 'Near Mint',
                'per_page': 100,
                'sort_by': 'price_asc'
            },
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore API per carta {blueprint_id}: {str(e)}")
        return None

def analyze_card_prices(prices_data, blueprint_id, selected_languages, only_zero=False):
    if not prices_data or str(blueprint_id) not in prices_data:
        return []

    lang_prices = {}
    lang_products = {}

    for product in prices_data[str(blueprint_id)]:

        if product['properties_hash'].get('condition', '') != 'Near Mint':
            continue
        if only_zero and not product['user']['can_sell_via_hub']:
            continue

        lang = product['properties_hash'].get('onepiece_language', '').lower()
        if lang not in [l.lower() for l in selected_languages]:
            continue

        price = product['price_cents'] / 100
        if not product['user']['can_sell_via_hub']:
            price += 3

        if lang not in lang_prices:
            lang_prices[lang] = []
            lang_products[lang] = []

        lang_prices[lang].append(price)
        lang_products[lang].append(product)

    results = []

    for lang, prices in lang_prices.items():
        if len(prices) >= 2:
            # Ordina i prezzi e trova l'indice del più basso e del secondo più basso
            sorted_indices = sorted(range(len(prices)), key=lambda i: prices[i])
            price1 = prices[sorted_indices[0]]
            price2 = prices[sorted_indices[1]]
            diff_abs = price2 - price1
            diff_pct = (diff_abs / price1) * 100 if price1 != 0 else 0

            # Prendi il product_id del prodotto con prezzo più basso
            cheapest_product = lang_products[lang][sorted_indices[0]]
            product_id = cheapest_product['id']

            results.append({
                'language': lang,
                'price1': round(price1, 2),
                'price2': round(price2, 2),
                'diff_abs': round(diff_abs, 2),
                'diff_pct': round(diff_pct, 2),
                'url': f"https://www.cardtrader.com/cards/{blueprint_id}",
                'product_id': product_id
            })

    return results


def search_opportunities_popup(expansions_ids, selected_languages, selected_rarities, min_price, max_price, min_diff, only_zero, callback):
    analizzate = 0
    for exp_id in expansions_ids:
        expansion_file = (
            Path(__file__).resolve().parent.parent
            / "data" / "onepiece" / "blueprints" / f"{exp_id}.json"
        )
        if not expansion_file.exists():
            continue
        with open(expansion_file, "r", encoding="utf-8") as f:
            cards = json.load(f)
        for card in cards:
            if card.get('rarity', '') not in selected_rarities:
                continue
            prices_data = fetch_card_prices(card['id'])
            time.sleep(0.4)
            if not prices_data:
                continue
            analyses = analyze_card_prices(prices_data, card['id'], selected_languages, only_zero)
            analizzate += 1
            for analysis in analyses:
                if (
                    analysis['price1'] >= min_price and
                    analysis['price2'] <= max_price and
                    analysis['diff_abs'] >= min_diff and
                    analysis['diff_pct'] > 25
                ):
                    lang_name = {
                        'en': 'Inglese',
                        'jp': 'Giapponese',
                        'fr': 'Francese',
                        'kr': 'Coreano',
                        'zh-cn': 'Cinese'
                    }.get(analysis['language'], analysis['language'].upper())  # Usa analysis['language']

                    card_info = {
                        "nome": f"{card['name']} ({lang_name})",
                        "url": analysis["url"],
                        "img_url": card.get("image_url", ""),  # Assicurati che ci sia nel blueprint!
                        "p1": analysis["price1"],
                        "p2": analysis["price2"],
                        "diff_pct": analysis["diff_pct"],
                        "diff_abs": analysis["diff_abs"],
                        "product_id": analysis["product_id"]
                    }
                    callback(card_info, analizzate)
            # Aggiorna comunque il progresso anche se nessuna carta trovata
            callback({"update_only": True}, analizzate)



def search_opportunities(expansions_ids, selected_languages, selected_rarities, min_price, max_price, min_diff, only_zero):

    # --- DEBUG: stampa i parametri selezionati ---
    print("\n⚙️ Parametri di ricerca:")
    print(f"- Espansioni selezionate: {expansions_ids}")
    print(f"- Lingue selezionate: {selected_languages}")
    print(f"- Rarità selezionate: {selected_rarities}\n")
    print(f"- Solo carte CardTrader Zero: {only_zero}\n")
    # ---------------------------------------------

    for exp_id in expansions_ids:
        expansion_file = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "onepiece"
            / "blueprints"
            / f"{exp_id}.json"
        )

        if not expansion_file.exists():
            print(f"❌ File espansione {exp_id} non trovato")
            continue

        try:
            with open(expansion_file, "r", encoding="utf-8") as f:
                cards = json.load(f)
        except Exception as e:
            print(f"❌ Errore lettura file {exp_id}: {str(e)}")
            continue

        print(f"\n🔍 Analizzo espansione {exp_id} - Carte compatibili con i filtri:")
        for card in cards:
            card_rarity = card.get('rarity', '')
            if card_rarity not in selected_rarities:
                continue
            print(f" - {card['name']} (Rarità: {card['rarity']}, ID: {card['id']})")

        # Ricerca vera e propria
        for card in cards:
            card_rarity = card.get('rarity', '')
            if card_rarity not in selected_rarities:
                continue

            prices_data = fetch_card_prices(card['id'])
            time.sleep(0.4)
            if not prices_data:
                continue

            analyses = analyze_card_prices(prices_data, card['id'], selected_languages, only_zero)
            for analysis in analyses:
                # Solo se la differenza supera il 25%
                if (
                        analysis['price1'] >= min_price and
                        analysis['price2'] <= max_price and
                        analysis['diff_abs'] >= min_diff and
                        analysis['diff_pct'] > 25
                ):
                    lang_name = {
                        'en': 'Inglese',
                        'jp': 'Giapponese',
                        'fr': 'Francese',
                        'kr': 'Coreano',
                        'zh-cn': 'Cinese'
                    }.get(analysis['language'], analysis['language'].upper())
                    print(
                        f"{card['name']} ({lang_name}) - "
                        f"P1: {analysis['price1']}€ P2: {analysis['price2']}€ "
                        f"P%: {analysis['diff_pct']}% Diff: {analysis['diff_abs']}€ "
                        f"Link: {analysis['url']}"
                    )
