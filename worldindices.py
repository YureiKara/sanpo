"""
SANPO — World Indices tab
Single panel, bar format matching PULSE gainers/losers style
"""

import streamlit as st
import yfinance as yf
from datetime import datetime
import pytz
import logging
from streamlit.components.v1 import html as st_html

from config import THEMES, FONTS

logger = logging.getLogger(__name__)


def get_theme():
    tn = st.session_state.get('theme', 'Dark')
    return THEMES.get(tn, THEMES['Dark'])


WORLD_INDICES = {
    'Asia': [
        ('^STI',      'Singapore STI'),
        ('^HSI',      'Hang Seng'),
        ('000001.SS', 'Shanghai'),
        ('^N225',     'Nikkei 225'),
        ('^AXJO',     'ASX 200'),
        ('^BSESN',    'India Sensex'),
        ('^KS11',     'KOSPI'),
        ('^KLSE',     'Malaysia KLCI'),
        ('^TWII',     'Taiwan TWSE'),
    ],
    'Europe': [
        ('^FTSE',     'FTSE 100'),
        ('^GDAXI',    'Germany DAX'),
        ('^FCHI',     'France CAC 40'),
        ('^STOXX50E', 'Euro Stoxx 50'),
    ],
    'Americas': [
        ('^GSPC',     'S&P 500'),
        ('^IXIC',     'Nasdaq'),
        ('^DJI',      'Dow Jones'),
        ('^RUT',      'Russell 2000'),
        ('^GSPTSE',   'Canada TSX'),
        ('^BVSP',     'Brazil IBOVESPA'),
        ('^MXX',      'Mexico IPC'),
    ],
}

ALL_TICKERS = [sym for region in WORLD_INDICES.values() for sym, _ in region]


@st.cache_data(ttl=300, max_entries=5, show_spinner=False)
def fetch_world_indices():
    results = {}
    try:
        raw = yf.download(
            ALL_TICKERS, period='1y', interval='1d',
            auto_adjust=True, progress=False, threads=True,
        )
        close = raw['Close'] if 'Close' in raw else raw
        for ticker in ALL_TICKERS:
            try:
                if ticker not in close.columns:
                    results[ticker] = {'day': None, 'ytd': None, 'price': None}
                    continue
                s = close[ticker].dropna()
                if len(s) < 2:
                    results[ticker] = {'day': None, 'ytd': None, 'price': None}
                    continue
                price = float(s.iloc[-1])
                prev  = float(s.iloc[-2])
                day_chg = (price - prev) / prev * 100 if prev else None
                this_year = datetime.now().year
                ytd_s = s[s.index.year >= this_year]
                if len(ytd_s) >= 2:
                    ytd_start = float(ytd_s.iloc[0])
                    ytd_chg = (price - ytd_start) / ytd_start * 100 if ytd_start else None
                else:
                    ytd_chg = None
                results[ticker] = {'day': day_chg, 'ytd': ytd_chg, 'price': price}
            except Exception as e:
                logger.warning(f"Error {ticker}: {e}")
                results[ticker] = {'day': None, 'ytd': None, 'price': None}
    except Exception as e:
        logger.warning(f"Fetch error: {e}")
        for ticker in ALL_TICKERS:
            results[ticker] = {'day': None, 'ytd': None, 'price': None}
    return results


def _fmt(val):
    if val is None:
        return '—', '#475569'
    sign = '+' if val >= 0 else ''
    color = '#4ade80' if val >= 0 else '#f59e0b'
    return f"{sign}{val:.2f}%", color


def _bar_row(name, price_str, day, ytd, max_abs, pos_c, neg_c, bg, bdr):
    day_str, day_c = _fmt(day)
    ytd_str, ytd_c = _fmt(ytd)
    bar_pct = (abs(day) / max_abs * 100) if day is not None and max_abs > 0 else 0
    bar_pct = min(bar_pct, 100)
    bar_color = pos_c if (day or 0) >= 0 else neg_c

    return f"""
    <div style='display:flex;align-items:center;background:{bg};
                padding:0 12px;height:28px;border-bottom:1px solid {bdr}15;gap:10px'>
        <div style='width:130px;font-size:11px;font-weight:600;
                    color:#f8fafc;flex-shrink:0;white-space:nowrap;
                    overflow:hidden;text-overflow:ellipsis'>{name}</div>
        <div style='width:72px;font-size:10px;font-weight:500;
                    color:#ffffff;flex-shrink:0;text-align:right;
                    font-variant-numeric:tabular-nums'>{price_str}</div>
        <div style='flex:1;position:relative;height:16px;border-radius:2px;
                    background:{bar_color}18'>
            <div style='position:absolute;left:0;top:0;height:100%;
                        width:{bar_pct:.1f}%;background:{bar_color}55;
                        border-radius:2px'></div>
            <span style='position:absolute;left:6px;top:50%;
                         transform:translateY(-50%);font-size:10px;
                         font-weight:700;color:{bar_color};
                         font-variant-numeric:tabular-nums'>{day_str}</span>
        </div>
        <div style='width:60px;font-size:11px;font-weight:700;
                    color:{ytd_c};text-align:right;flex-shrink:0;
                    font-variant-numeric:tabular-nums'>{ytd_str}</div>
    </div>"""


def _build_panel(data):
    t = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bg3 = t.get('bg3', '#0f172a')
    bdr = t.get('border', '#1e293b')
    mut = t.get('muted', '#475569')
    pos_c = t.get('pos', '#4ade80')
    neg_c = t.get('neg', '#f59e0b')

    # Max abs day change for bar scaling PER REGION
    all_days = [abs(data.get(sym, {}).get('day') or 0)
                for region in WORLD_INDICES.values()
                for sym, _ in region]
    max_abs = max(all_days) if all_days else 1.0

    # Header row
    html = f"""<div style='font-family:{FONTS}'>
        <div style='display:flex;align-items:center;padding:5px 12px;
                    border-bottom:1px solid {bdr};gap:10px'>
            <div style='width:130px;font-size:8px;font-weight:700;
                        letter-spacing:0.1em;text-transform:uppercase;
                        color:{mut}'>INDEX</div>
            <div style='width:72px;font-size:8px;font-weight:700;
                        letter-spacing:0.1em;text-transform:uppercase;
                        color:{mut};text-align:right'>PRICE</div>
            <div style='flex:1;font-size:8px;font-weight:700;
                        letter-spacing:0.1em;text-transform:uppercase;
                        color:{mut}'>DAY %</div>
            <div style='width:60px;font-size:8px;font-weight:700;
                        letter-spacing:0.1em;text-transform:uppercase;
                        color:{mut};text-align:right'>YTD %</div>
        </div>"""

    first = True
    for region, indices in WORLD_INDICES.items():
        sep = '' if first else f'margin-top:6px;border-top:1px solid {bdr};'
        first = False
        # Region header
        html += f"""
        <div style='display:flex;align-items:center;gap:8px;
                    padding:6px 12px 4px 12px;{sep}'>
            <div style='font-size:9px;font-weight:700;letter-spacing:0.12em;
                        text-transform:uppercase;color:#f8fafc'>{region}</div>
            <div style='flex:1;height:1px;background:{bdr}'></div>
        </div>"""

        for i, (ticker, name) in enumerate(indices):
            d = data.get(ticker, {})
            price = d.get('price')
            price_str = f"{price:,.2f}" if price else '—'
            bg = bg2 if i % 2 == 0 else bg3
            html += _bar_row(name, price_str, d.get('day'), d.get('ytd'),
                             max_abs, pos_c, neg_c, bg, bdr)

    html += "</div>"
    return html


def _wrap(body, height):
    t = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bdr = t.get('border', '#1e293b')
    txt = t.get('text', '#e2e8f0')
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>"
        "<style>* { margin:0; padding:0; box-sizing:border-box; }"
        f"body {{ background:transparent; font-family:{FONTS}; color:{txt}; overflow:auto; }}"
        f"::-webkit-scrollbar {{ width:4px; }}"
        f"::-webkit-scrollbar-track {{ background:{bg2}; }}"
        f"::-webkit-scrollbar-thumb {{ background:{bdr}; border-radius:2px; }}"
        "</style></head><body>"
        f"{body}"
        "</body></html>"
    )


def render_worldindices_tab(is_mobile):
    t = get_theme()
    mut = t.get('muted', '#475569')
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).strftime('%d %b %Y %H:%M SGT')
    st.markdown(
        f"<div style='font-size:9px;color:{mut};font-family:{FONTS};"
        f"padding:0 0 6px 0'>Updated: {now_str}</div>",
        unsafe_allow_html=True
    )
    with st.spinner('Loading world indices...'):
        data = fetch_world_indices()
    height = 740
    st_html(_wrap(_build_panel(data), height), height=height)
