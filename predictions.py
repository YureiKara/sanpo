"""
SANPO — Predictions tab
Pulls from Polymarket Gamma API (public, no auth)
Shows top markets by volume with odds and expiry
"""

import streamlit as st
import requests
from datetime import datetime
import pytz
import logging
from streamlit.components.v1 import html as st_html

from config import THEMES, FONTS

logger = logging.getLogger(__name__)


def get_theme():
    tn = st.session_state.get('theme', 'Dark')
    return THEMES.get(tn, THEMES['Dark'])


CATEGORIES = {
    'All':         None,
    'Finance':     120,
    'Crypto':      21,
    'Politics':    2,
    'Tech':        1401,
    'Geopolitics': 100265,
    'Culture':     596,
}


@st.cache_data(ttl=300, max_entries=5, show_spinner=False)
def fetch_markets(category='All', limit=30):
    import json as _json
    try:
        tag_id = CATEGORIES.get(category)
        params = {
            'limit': limit,
            'closed': 'false',
            'order': 'volume24hr',
            'ascending': 'false',
            'related_tags': 'true',
        }
        if tag_id:
            params['tag_id'] = tag_id

        r = requests.get(
            'https://gamma-api.polymarket.com/events',
            params=params,
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        r.raise_for_status()
        events = r.json()
        if not isinstance(events, list):
            events = events.get('data', [])

        results = []
        for ev in events:
            # Each event can have multiple markets
            markets = ev.get('markets', [])
            question = ev.get('title', ev.get('question', ''))
            slug = ev.get('slug', ev.get('id', ''))
            vol = float(ev.get('volume', 0) or 0)
            vol24 = float(ev.get('volume24hr', 0) or 0)

            end_date = ev.get('endDate', ev.get('end_date_iso', ''))
            expiry_str = ''
            if end_date:
                try:
                    dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    expiry_str = dt.strftime('%d %b %Y')
                except Exception:
                    expiry_str = str(end_date)[:10]

            # Build outcomes from markets
            outcome_list = []
            for m in markets:
                outcomes = m.get('outcomes', '[]')
                prices   = m.get('outcomePrices', '[]')
                if isinstance(outcomes, str):
                    try:
                        outcomes = _json.loads(outcomes)
                        prices   = _json.loads(prices)
                    except Exception:
                        outcomes = []
                        prices   = []
                for o, p in zip(outcomes, prices):
                    try:
                        pct = round(float(p) * 100, 1)
                    except Exception:
                        pct = None
                    outcome_list.append({'label': o, 'pct': pct})

            # If single binary market, just show Yes/No
            if not outcome_list and markets:
                m = markets[0]
                outcomes = m.get('outcomes', '[]')
                prices   = m.get('outcomePrices', '[]')
                if isinstance(outcomes, str):
                    try:
                        outcomes = _json.loads(outcomes)
                        prices   = _json.loads(prices)
                    except Exception:
                        outcomes = []
                        prices   = []
                for o, p in zip(outcomes, prices):
                    try:
                        pct = round(float(p) * 100, 1)
                    except Exception:
                        pct = None
                    outcome_list.append({'label': o, 'pct': pct})

            outcome_list.sort(key=lambda x: x['pct'] or 0, reverse=True)

            results.append({
                'question': question,
                'outcomes': outcome_list[:4],
                'volume': vol,
                'volume24': vol24,
                'expiry': expiry_str,
                'url': f"https://polymarket.com/event/{slug}",
            })

        results.sort(key=lambda x: x['volume'], reverse=True)
        return results

    except Exception as e:
        logger.warning(f"Polymarket fetch error: {e}")
        return []


def _fmt_vol(v):
    if v >= 1e6:
        return f"${v/1e6:.1f}M"
    if v >= 1e3:
        return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


def _pct_color(pct, pos_c, neg_c, mut):
    if pct is None:
        return mut
    if pct >= 70:
        return pos_c
    if pct <= 15:
        return neg_c
    return '#60a5fa'


def _build_table(markets, theme):
    bg2   = theme.get('bg2', '#0a0f1a')
    bg3   = theme.get('bg3', '#0f172a')
    bdr   = theme.get('border', '#1e293b')
    mut   = theme.get('muted', '#475569')
    txt   = theme.get('text', '#e2e8f0')
    txt2  = theme.get('text2', '#94a3b8')
    acc   = theme.get('accent', '#4ade80')
    pos_c = theme.get('pos', '#4ade80')
    neg_c = theme.get('neg', '#f59e0b')
    blue  = '#60a5fa'

    HDR = "font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f8fafc"

    if not markets:
        return f"<div style='padding:40px;text-align:center;font-family:{FONTS};color:{mut};font-size:11px'>No markets found — check connection</div>"

    html = f"""<div style='font-family:{FONTS}'>
        <div style='display:flex;align-items:center;padding:5px 12px;
                    border-bottom:1px solid {bdr};gap:8px'>
            <div style='flex:2;{HDR}'>QUESTION</div>
            <div style='flex:3;{HDR}'>TOP OUTCOMES</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>VOLUME</div>
            <div style='width:65px;flex-shrink:0;{HDR};text-align:right'>24H VOL</div>
            <div style='width:80px;flex-shrink:0;{HDR};text-align:center'>EXPIRY</div>
        </div>"""

    for i, m in enumerate(markets):
        row_bg = bg2 if i % 2 == 0 else bg3
        vol_str   = _fmt_vol(m['volume'])
        vol24_str = _fmt_vol(m['volume24'])

        # Outcomes chips
        chips = ''
        for o in m['outcomes'][:3]:
            pct = o['pct']
            color = _pct_color(pct, pos_c, neg_c, mut)
            pct_str = f"{pct:.0f}%" if pct is not None else '—'
            chips += (
                f"<span style='display:inline-flex;align-items:center;gap:4px;"
                f"background:{color}18;border:1px solid {color}40;"
                f"border-radius:3px;padding:1px 6px;margin-right:4px;white-space:nowrap'>"
                f"<span style='font-size:9px;color:{txt2}'>{o['label']}</span>"
                f"<span style='font-size:10px;font-weight:700;color:{color}'>{pct_str}</span>"
                f"</span>"
            )

        html += f"""
        <a href='{m["url"]}' target='_blank' style='text-decoration:none;display:block'>
        <div style='display:flex;align-items:center;background:{row_bg};
                    padding:7px 12px;border-bottom:1px solid {bdr}12;gap:8px;
                    transition:background 0.1s'>
            <div style='flex:2;font-size:11px;font-weight:600;color:#f8fafc;
                        line-height:1.3'>{m['question']}</div>
            <div style='flex:3;display:flex;flex-wrap:wrap;gap:2px;align-items:center'>{chips}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;font-weight:600;
                        color:{acc};text-align:right'>{vol_str}</div>
            <div style='width:65px;flex-shrink:0;font-size:10px;
                        color:{txt2};text-align:right'>{vol24_str}</div>
            <div style='width:80px;flex-shrink:0;font-size:10px;
                        color:{txt2};text-align:center'>{m['expiry']}</div>
        </div>
        </a>"""

    html += "</div>"
    return html


def _wrap(body, height):
    t   = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bdr = t.get('border', '#1e293b')
    txt = t.get('text', '#e2e8f0')
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>"
        "<style>"
        "* { margin:0; padding:0; box-sizing:border-box; }"
        f"body {{ background:transparent; font-family:{FONTS}; color:{txt}; overflow:hidden; }}"
        f"::-webkit-scrollbar {{ width:4px; }}"
        f"::-webkit-scrollbar-track {{ background:{bg2}; }}"
        f"::-webkit-scrollbar-thumb {{ background:{bdr}; border-radius:2px; }}"
        "a:hover > div { background:#1a2744 !important; }"
        "</style></head><body>"
        f"<div style='height:{height}px;overflow-y:auto;overflow-x:hidden'>{body}</div>"
        "</body></html>"
    )


def render_predictions_tab(is_mobile):
    t   = get_theme()
    mut = t.get('muted', '#475569')
    acc = t.get('accent', '#4ade80')
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).strftime('%d %b %Y %H:%M SGT')

    # Controls
    col_cat, col_spacer, col_ts = st.columns([1, 4, 1])
    with col_cat:
        st.markdown(
            f"<div style='font-size:9px;font-weight:700;color:#e2e8f0;"
            f"font-family:{FONTS};text-transform:uppercase;"
            f"letter-spacing:0.08em;margin-bottom:-18px'>CATEGORY</div>",
            unsafe_allow_html=True
        )
        category = st.selectbox(
            'pred_cat', list(CATEGORIES.keys()),
            key='pred_category', label_visibility='collapsed'
        )
    with col_ts:
        st.markdown(
            f"<div style='font-size:9px;color:#f8fafc;font-family:{FONTS};"
            f"padding:28px 0 0 0;text-align:right'>Updated: {now_str}</div>",
            unsafe_allow_html=True
        )

    with st.spinner('Loading prediction markets...'):
        markets = fetch_markets(category)

    n = len(markets)
    st.markdown(
        f"<div style='font-size:9px;color:{mut};font-family:{FONTS};"
        f"padding:2px 0 4px 0'>{n} markets · Powered by "
        f"<span style='color:{acc}'>Polymarket</span></div>",
        unsafe_allow_html=True
    )

    height = 720
    st_html(_wrap(_build_table(markets, t), height), height=height)
