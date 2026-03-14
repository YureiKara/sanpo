"""
SANPO — World Indices tab
Single panel, bar format like PULSE gainers/losers
Regions: Asia, Europe, Americas with white headers and separator lines
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
                logger.warning(f"Error processing {ticker}: {e}")
                results[ticker] = {'day': None, 'ytd': None, 'price': None}
    except Exception as e:
        logger.warning(f"World indices fetch error: {e}")
        for ticker in ALL_TICKERS:
            results[ticker] = {'day': None, 'ytd': None, 'price': None}
    return results


def _fmt(val):
    if val is None:
        return '—', '#475569'
    sign = '+' if val >= 0 else ''
    color = '#4ade80' if val >= 0 else '#f59e0b'
    return f"{sign}{val:.2f}%", color


def _build_panel(data):
    t = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bg3 = t.get('bg3', '#0f172a')
    bdr = t.get('border', '#1e293b')
    mut = t.get('muted', '#475569')
    acc = t.get('accent', '#4ade80')
    pos_c = t.get('pos', '#4ade80')
    neg_c = t.get('neg', '#f59e0b')

    # Find max abs day change for bar scaling
    all_days = [abs(data.get(sym, {}).get('day') or 0)
                for region in WORLD_INDICES.values()
                for sym, _ in region]
    max_day = max(all_days) if all_days else 1.0
    max_day = max(max_day, 0.01)

    # Column headers
    html = f"""<div style='font-family:{FONTS}'>
        <div style='display:flex;align-items:center;padding:6px 12px 8px 12px;
                    border-bottom:1px solid {bdr}'>
            <div style='width:140px;font-size:8.5px;font-weight:700;
                        letter-spacing:0.1em;text-transform:uppercase;color:{mut}'>Index</div>
            <div style='flex:1'></div>
            <div style='width:56px;font-size:8.5px;font-weight:700;
                        letter-spacing:0.1em;text-transform:uppercase;
                        color:{mut};text-align:right'>Day</div>
            <div style='width:64px;font-size:8.5px;font-weight:700;
                        letter-spacing:0.1em;text-transform:uppercase;
                        color:{mut};text-align:right'>YTD</div>
        </div>"""

    first_region = True
    for region, indices in WORLD_INDICES.items():
        # Region separator + header
        sep = '' if first_region else f"border-top:2px solid {bdr};"
        first_region = False
        html += f"""
        <div style='display:flex;align-items:center;padding:7px 12px 5px 12px;{sep}'>
            <div style='font-size:9px;font-weight:700;letter-spacing:0.12em;
                        text-transform:uppercase;color:#f8fafc'>{region}</div>
            <div style='flex:1;height:1px;background:{bdr};margin-left:10px'></div>
        </div>"""

        for i, (ticker, name) in enumerate(indices):
            d = data.get(ticker, {})
            day = d.get('day')
            ytd = d.get('ytd')
            price = d.get('price')

            day_str, day_c = _fmt(day)
            ytd_str, ytd_c = _fmt(ytd)
            price_str = f"{price:,.2f}" if price else '—'

            # Bar width (max 55% of flex area)
            bar_pct = (abs(day) / max_day * 55) if day is not None else 0
            bar_color = pos_c if (day or 0) >= 0 else neg_c
            row_bg = bg2 if i % 2 == 0 else bg3

            html += f"""
            <div style='display:flex;align-items:center;
                        background:{row_bg};padding:5px 12px;
                        border-bottom:1px solid {bdr}10'>
                <div style='width:140px;font-size:11px;font-weight:600;
                            color:#f8fafc;white-space:nowrap'>{name}</div>
                <div style='flex:1;position:relative;height:18px;
                            display:flex;align-items:center'>
                    <div style='position:absolute;left:0;top:50%;transform:translateY(-50%);
                                height:10px;width:{bar_pct:.1f}%;
                                background:{bar_color}22;
                                border-radius:2px;
                                border-left:2px solid {bar_color}'></div>
                    <span style='position:absolute;right:4px;font-size:9px;
                                 color:#ffffff66;font-variant-numeric:tabular-nums'>{price_str}</span>
                </div>
                <div style='width:56px;font-size:11px;font-weight:700;
                            color:{day_c};text-align:right;
                            font-variant-numeric:tabular-nums'>{day_str}</div>
                <div style='width:64px;font-size:11px;font-weight:700;
                            color:{ytd_c};text-align:right;
                            font-variant-numeric:tabular-nums'>{ytd_str}</div>
            </div>"""

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
    bdr = t.get('border', '#1e293b')
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).strftime('%d %b %Y %H:%M SGT')

    st.markdown(
        f"<div style='font-size:9px;color:{mut};font-family:{FONTS};"
        f"padding:0 0 8px 0'>Updated: {now_str}</div>",
        unsafe_allow_html=True
    )

    with st.spinner('Loading world indices...'):
        data = fetch_world_indices()

    height = 720
    body = _build_panel(data)
    st_html(_wrap(body, height), height=height)
