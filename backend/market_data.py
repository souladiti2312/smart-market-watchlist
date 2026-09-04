import os
import requests

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path, override=True)

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")

STOCKS = {
    "RELIANCE": {
        "name": "Reliance Industries",
        "instrument_key": "NSE_EQ|INE002A01018"
    }
}


def get_stock_quote(instrument_key):
    url = "https://api.upstox.com/v3/market-quote/ltp"

    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    params = {
        "instrument_key": instrument_key
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        if result.get("status") != "success":
            return None

        stock_data = list(result["data"].values())[0]

        return {
            "price": stock_data.get("last_price"),
            "previous_close": stock_data.get("cp"),
            "volume": stock_data.get("volume")
        }

    except Exception as e:
        print("Market data error:", e)
        return None
    
def get_stock_by_symbol(symbol):
    stock = search_stock(symbol)

    if not stock:
        return None

    quote = get_stock_quote(stock["instrument_key"])

    if not quote:
        return None

    return {
        "symbol": stock["symbol"],
        "name": stock["name"],
        "instrument_key": stock["instrument_key"],
        "price": quote["price"],
        "previous_close": quote["previous_close"],
        "volume": quote["volume"]
    }

def search_stock(symbol):
    url = "https://api.upstox.com/v2/instruments/search"

    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    params = {
        "query": symbol.upper(),
        "exchanges": "NSE",
        "segments": "EQ",
        "page_number": 1,
        "records": 10
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        if result.get("status") != "success":
            return None

        stocks = result.get("data", [])

        # Prefer an exact NSE equity symbol match
        for stock in stocks:
            if (
                stock.get("trading_symbol", "").upper() == symbol.upper()
                and stock.get("segment") == "NSE_EQ"
            ):
                return {
                    "symbol": stock["trading_symbol"],
                    "name": stock.get("short_name") or stock["name"],
                    "instrument_key": stock["instrument_key"]
                }

        return None

    except Exception as e:
        print("Stock search error:", e)
        return None