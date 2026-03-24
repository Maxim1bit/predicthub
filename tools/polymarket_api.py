"""
PredictHub — Polymarket API Module
Usage:
    python tools/polymarket_api.py markets "bitcoin"       (search markets)
    python tools/polymarket_api.py hot                      (top markets by volume)
    python tools/polymarket_api.py price TOKEN_ID           (get current price)
    python tools/polymarket_api.py buy TOKEN_ID 10 0.35     (buy 10 shares at $0.35)
    python tools/polymarket_api.py positions                (show open positions)
    python tools/polymarket_api.py balance                  (show USDC balance)
    python tools/polymarket_api.py export                   (export hot markets to JSON)
"""

import requests
import json
import sys
import os
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
REPORTS_DIR = os.getenv('REPORTS_DIR', os.path.join(os.path.dirname(__file__), '..', 'reports'))

# --- READ-ONLY FUNCTIONS (no auth needed) ---

def search_markets(query, limit=10):
    """Search markets by keyword"""
    resp = requests.get(f"{GAMMA_API}/markets", params={
        "closed": False,
        "limit": limit,
        "order": "volume24hr",
        "ascending": False,
        "tag": query if len(query) < 20 else None
    })
    markets = resp.json()

    # Filter by query in question
    if query:
        markets = [m for m in markets if query.lower() in m.get('question', '').lower()]

    results = []
    for m in markets[:limit]:
        # Parse yes_price from various formats
        raw_prices = m.get("outcomePrices", None)
        yes_price = "0"
        if raw_prices:
            if isinstance(raw_prices, str):
                try:
                    parsed = json.loads(raw_prices)
                    yes_price = str(parsed[0]) if parsed else "0"
                except (json.JSONDecodeError, IndexError):
                    yes_price = "0"
            elif isinstance(raw_prices, list) and raw_prices:
                yes_price = str(raw_prices[0])

        results.append({
            "id": m.get("id"),
            "question": m.get("question"),
            "yes_price": yes_price,
            "volume": m.get("volume", 0),
            "volume_24h": m.get("volume24hr", 0),
            "liquidity": m.get("liquidity", 0),
            "end_date": m.get("endDate"),
            "category": m.get("groupSlug", ""),
        })

    return results

def get_hot_markets(limit=10):
    """Get top markets by 24h volume"""
    resp = requests.get(f"{GAMMA_API}/markets", params={
        "closed": False,
        "limit": limit,
        "order": "volume24hr",
        "ascending": False
    })
    markets = resp.json()

    results = []
    for m in markets[:limit]:
        yes_price = "0"
        if m.get("outcomePrices"):
            try:
                yes_price = m["outcomePrices"][0] if isinstance(m["outcomePrices"], list) else json.loads(m["outcomePrices"])[0]
            except (IndexError, json.JSONDecodeError):
                pass

        results.append({
            "id": m.get("id"),
            "question": m.get("question", "Unknown"),
            "yes_price": yes_price,
            "volume": float(m.get("volume", 0)),
            "volume_24h": float(m.get("volume24hr", 0)),
            "liquidity": float(m.get("liquidity", 0)),
            "category": m.get("groupSlug", ""),
        })

    return results

def get_market_price(condition_id):
    """Get current price for a specific market"""
    resp = requests.get(f"{CLOB_API}/price", params={"token_id": condition_id})
    return resp.json()

def export_hot_markets():
    """Export hot markets to JSON file for other tools"""
    markets = get_hot_markets(10)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    filepath = os.path.join(REPORTS_DIR, "daily-markets.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(markets, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(markets)} markets to {filepath}")
    return markets

# --- TRADING FUNCTIONS (auth needed) ---

def get_trading_client():
    """Initialize authenticated trading client"""
    try:
        from py_clob_client.client import ClobClient
        private_key = os.getenv('POLYMARKET_PRIVATE_KEY')
        if not private_key:
            print("ERROR: POLYMARKET_PRIVATE_KEY not set in .env")
            return None
        return ClobClient(
            host=CLOB_API,
            key=private_key,
            chain_id=137
        )
    except ImportError:
        print("ERROR: py-clob-client not installed. Run: pip install py-clob-client")
        return None

def buy_shares(token_id, amount, price, side="BUY"):
    """Buy/sell shares on a market"""
    client = get_trading_client()
    if not client:
        return None

    order = client.create_and_post_order(
        token_id=token_id,
        price=price,
        size=amount,
        side=side
    )

    result = {
        "status": "order_placed",
        "token_id": token_id,
        "side": side,
        "price": price,
        "amount": amount,
        "total": price * amount,
        "timestamp": datetime.now().isoformat()
    }
    print(json.dumps(result, indent=2))

    # Log trade
    log_trade(result)
    return result

def get_positions():
    """Get current open positions"""
    client = get_trading_client()
    if not client:
        return None
    return client.get_positions()

def get_balance():
    """Get USDC balance"""
    client = get_trading_client()
    if not client:
        return None
    return client.get_balance()

def log_trade(trade_data):
    """Log trade to file"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    log_path = os.path.join(REPORTS_DIR, "trades.jsonl")
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(trade_data) + "\n")

# --- CLI ---

def print_markets(markets):
    """Pretty-print market list"""
    print(f"\n{'#':>3} {'Yes':>6} {'Vol 24h':>12} Question")
    print("-" * 70)
    for i, m in enumerate(markets, 1):
        yes = float(m['yes_price'])
        vol = float(m.get('volume_24h', 0))
        q = m['question'][:50]
        print(f"{i:>3} {yes:>5.0%} ${vol:>10,.0f}  {q}")
    print()
    print()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python polymarket_api.py [markets|hot|price|buy|positions|balance|export]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'markets':
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        results = search_markets(query)
        print_markets(results)

    elif cmd == 'hot':
        results = get_hot_markets(10)
        print_markets(results)

    elif cmd == 'price':
        token_id = sys.argv[2]
        price = get_market_price(token_id)
        print(json.dumps(price, indent=2))

    elif cmd == 'buy':
        if len(sys.argv) < 5:
            print("Usage: python polymarket_api.py buy TOKEN_ID AMOUNT PRICE")
            sys.exit(1)
        token_id = sys.argv[2]
        amount = float(sys.argv[3])
        price = float(sys.argv[4])
        buy_shares(token_id, amount, price)

    elif cmd == 'positions':
        positions = get_positions()
        print(json.dumps(positions, indent=2))

    elif cmd == 'balance':
        balance = get_balance()
        print(f"Balance: {balance}")

    elif cmd == 'export':
        markets = export_hot_markets()
        print_markets(markets)

    else:
        print(f"Unknown command: {cmd}")
