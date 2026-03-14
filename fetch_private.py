"""
SANPO — fetch_private.py
Fetches private company data via yfinance and writes private.json
Run by GitHub Actions on demand
"""

import json
import yfinance as yf
from datetime import datetime
import pytz

PRIVATE_COMPANIES = [
    ("AIPVT=X", "Anthropic"), ("STRIVEPVT=X", "Stripe"), ("SPACEXPVT=X", "SpaceX"),
    ("CLOROPVT=X", "Klarna"), ("BYTEDPVT=X", "ByteDance"), ("OPENAPVT=X", "OpenAI"),
    ("CANOOPVT=X", "Canoo"), ("NUROOPVT=X", "Nuro"), ("RIBBOPVT=X", "Ribbon Health"),
    ("CHIMEPVT=X", "Chime"), ("PLAIDPVT=X", "Plaid"), ("BREXPVT=X", "Brex"),
    ("FIGMAPVT=X", "Figma"), ("DATABPVT=X", "Databricks"), ("EPICPVT=X", "Epic Games"),
    ("FANDUEPVT=X", "FanDuel"), ("INSTACPVT=X", "Instacart"), ("NUBANPVT=X", "Nubank"),
    ("REVOLUPVT=X", "Revolut"), ("GRABPVT=X", "Grab"),
]

def fetch_company(symbol, name):
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        price = getattr(fi, 'last_price', None)
        high52 = getattr(fi, 'year_high', None)
        low52 = getattr(fi, 'year_low', None)
        mktcap = getattr(fi, 'market_cap', None)
        pct_52w = None
        if price and low52 and high52 and (high52 - low52) > 0:
            pct_52w = round(((price - low52) / low52) * 100, 1)
        info = t.info
        return {
            'symbol': symbol,
            'name': name,
            'price': round(price, 4) if price else None,
            'price_52w_pct': pct_52w,
            'market_cap': mktcap,
            'sector': info.get('sector', ''),
            'total_raised': info.get('totalCash', None),
            'latest_round': info.get('lastFundingRound', ''),
            'latest_date': info.get('lastFundingDate', ''),
        }
    except Exception as e:
        return {'symbol': symbol, 'name': name, 'error': str(e)}

def main():
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).isoformat()

    results = []
    for symbol, name in PRIVATE_COMPANIES:
        print(f"Fetching {name}...")
        data = fetch_company(symbol, name)
        results.append(data)

    # Sort by market cap descending
    results.sort(key=lambda x: x.get('market_cap') or 0, reverse=True)

    output = {
        'updated': now_str,
        'source': 'SANPO Private Companies',
        'count': len(results),
        'companies': results
    }

    with open('private.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nDone! {len(results)} companies written to private.json")

if __name__ == '__main__':
    main()
