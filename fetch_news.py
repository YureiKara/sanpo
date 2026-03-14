"""
SANPO — fetch_news.py
Fetches all RSS feeds and writes news.json
Run by GitHub Actions on demand
"""

import feedparser
import json
import urllib.request
from html import unescape
import re
from datetime import datetime
import pytz

_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

NEWS_FEEDS = {
    'Macro': [
        ('S&P 500',    'https://news.google.com/rss/search?q=S%26P+500+index&hl=en&gl=US&ceid=US:en'),
        ('Gold',       'https://news.google.com/rss/search?q=gold+price+XAU&hl=en&gl=US&ceid=US:en'),
        ('Bitcoin',    'https://news.google.com/rss/search?q=bitcoin+BTC+price&hl=en&gl=US&ceid=US:en'),
        ('Oil',        'https://news.google.com/rss/search?q=crude+oil+WTI+price&hl=en&gl=US&ceid=US:en'),
        ('Fed',        'https://news.google.com/rss/search?q=Federal+Reserve+interest+rates&hl=en&gl=US&ceid=US:en'),
    ],
    'Singapore': [
        ('CNA',        'https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511'),
        ('SGX',        'https://news.google.com/rss/search?q=SGX+Singapore+Exchange&hl=en&gl=SG&ceid=SG:en'),
        ('STI',        'https://news.google.com/rss/search?q=Straits+Times+Index+STI&hl=en&gl=SG&ceid=SG:en'),
    ],
    'Regional': [
        ('SCMP',       'https://www.scmp.com/rss/5/feed'),
        ('Nikkei Asia','https://asia.nikkei.com/rss/feed/nar'),
        ('Malay Mail',  'https://www.malaymail.com/feed/rss/money'),
    ],
    'World': [
        ('Bloomberg',  'https://feeds.bloomberg.com/markets/news.rss'),
        ('CNBC',       'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258'),
        ('BBC Biz',    'https://feeds.bbci.co.uk/news/business/rss.xml'),
        ('FT',         'https://www.ft.com/rss/home'),
    ],
    'Tech': [
        ('TechCrunch', 'https://techcrunch.com/category/artificial-intelligence/feed/'),
        ('CoinDesk',   'https://www.coindesk.com/arc/outboundfeeds/rss/'),
        ('The Verge',  'https://www.theverge.com/rss/index.xml'),
    ],
}

def _clean(raw):
    if not raw: return ''
    t = re.sub(r'<[^>]+>', '', raw)
    return re.sub(r'\s+', ' ', unescape(t)).strip()

def fetch_feed(name, url, max_items=5):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': _UA, 'Accept': 'application/rss+xml,*/*'})
        resp = urllib.request.urlopen(req, timeout=12)
        feed = feedparser.parse(resp.read())
        items = []
        for entry in feed.entries[:max_items]:
            title = _clean(getattr(entry, 'title', ''))
            link  = getattr(entry, 'link', '')
            pub   = getattr(entry, 'published', getattr(entry, 'updated', ''))
            if not title: continue
            date_str = ''
            sort_key = ''
            if pub:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub)
                    date_str = dt.strftime('%d %b %Y %H:%M')
                    sort_key = dt.isoformat()
                except:
                    date_str = pub[:16]
            items.append({
                'source': name,
                'title': title,
                'url': link,
                'date': date_str,
                'sort_key': sort_key,
            })
        return items
    except Exception as e:
        print(f"  Error [{name}]: {e}")
        return []

def main():
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).isoformat()

    result = {
        'updated': now_str,
        'source': 'SANPO News Feed',
        'categories': {},
        'all_headlines': [],
        'total': 0
    }

    all_items = []
    for category, feeds in NEWS_FEEDS.items():
        print(f"Fetching {category}...")
        cat_items = []
        for name, url in feeds:
            items = fetch_feed(name, url, max_items=5)
            cat_items.extend(items)
            print(f"  {name}: {len(items)} items")
        cat_items.sort(key=lambda x: x.get('sort_key', ''), reverse=True)
        result['categories'][category] = cat_items[:10]
        all_items.extend(cat_items)

    # Deduplicate by title
    seen = set()
    unique = []
    for h in sorted(all_items, key=lambda x: x.get('sort_key', ''), reverse=True):
        if h['title'] not in seen:
            seen.add(h['title'])
            unique.append(h)

    result['all_headlines'] = unique[:60]
    result['total'] = len(unique)

    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nDone! {len(unique)} headlines written to news.json")

if __name__ == '__main__':
    main()
