"""
SANPO — World Indices tab
Two panels: Left = Day Change%, Right = YTD%
Regions: Asia, Europe, Americas
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, date
import pytz
import logging
from streamlit.components.v1 import html as st_html

from config import THEMES, FONTS

logger = logging.getLogger(__name__)


def get_theme():
    tn = st.session_state.get('theme', 'Dark')
    return THEMES.get(tn, THEMES['Dark'])


# =============================================================================
# INDEX DEFINITIONS
# =============================================================================

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


# =============================================================================
# DATA FETCH
# =============================================================================

@st.cache_data(ttl=300, max_entries=5, show_spinner=False)
def fetch_world_indices():
    """Fetch day change% and YTD% for all world indices."""
    results = {}
    try:
        raw = yf.download(
            ALL_TICKERS,
            period='1y',
            interval='1d',
            auto_adjust=True,
            progress=False,
            threads=True,
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

                # YTD: find first trading day of current year
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


# =============================================================================
# HTML RENDERING
# =============================================================================

def _fmt(val, decimals=2):
    if val is None:
        return '—', '#475569'
    sign = '+' if val >= 0 else ''
    color = '#4ade80' if val >= 0 else '#f59e0b'
    return f"{sign}{val:.{decimals}f}%", color


def _build_panel(data, label, key):
    """Build HTML for one panel (day or ytd)."""
    t = get_theme()
    bg  = t.get('bg',  '#0f1117')
    bg2 = t.get('bg2', '#0a0f1a')
    bg3 = t.get('bg3', '#0f172a')
    bdr = t.get('border', '#1e293b')
    txt = t.get('text', '#e2e8f0')
    txt2 = t.get('text2', '#94a3b8')
    mut = t.get('muted', '#475569')
    acc = t.get('accent', '#4ade80')

    region_icons = {'Asia': '🌏', 'Europe': '🌍', 'Americas': '🌎'}

    html = f"""
    <div style='font-family:{FONTS};padding:4px'>
        <div style='font-size:10px;font-weight:700;letter-spacing:0.12em;
                    text-transform:uppercase;color:{acc};padding:0 0 10px 4px'>
            {label}
        </div>
    """

    for region, indices in WORLD_INDICES.items():
        icon = region_icons.get(region, '')
        html += f"""
        <div style='margin-bottom:14px'>
            <div style='font-size:9px;font-weight:700;letter-spacing:0.1em;
                        text-transform:uppercase;color:{mut};
                        padding:4px 8px;background:{bg3};
                        border-left:3px solid {acc};margin-bottom:2px'>
                {icon} {region}
            </div>
            <table style='width:100%;border-collapse:collapse'>
        """

        for i, (ticker, name) in enumerate(indices):
            d = data.get(ticker, {})
            val = d.get(key)
            fmt_val, color = _fmt(val)
            price = d.get('price')
            price_str = f"{price:,.2f}" if price else '—'
            row_bg = bg2 if i % 2 == 0 else bg3

            html += f"""
            <tr style='background:{row_bg}'>
                <td style='padding:5px 8px;font-size:11px;
                           font-weight:600;color:{txt};width:45%'>{name}</td>
                <td style='padding:5px 8px;font-size:10px;
                           color:{txt2};width:30%;text-align:right'>{price_str}</td>
                <td style='padding:5px 8px;font-size:11px;font-weight:700;
                           color:{color};width:25%;text-align:right'>{fmt_val}</td>
            </tr>
            """

        html += "</table></div>"

    html += "</div>"
    return html


def _wrap_panel(body, height):
    t = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bdr = t.get('border', '#1e293b')
    txt = t.get('text', '#e2e8f0')

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>"
        "<style>"
        "* { margin:0; padding:0; box-sizing:border-box; }"
        f"body {{ background:transparent; font-family:{FONTS}; color:{txt}; overflow:auto; }}"
        f"::-webkit-scrollbar {{ width:4px; }}"
        f"::-webkit-scrollbar-track {{ background:{bg2}; }}"
        f"::-webkit-scrollbar-thumb {{ background:{bdr}; border-radius:2px; }}"
        "</style></head><body>"
        f"{body}"
        "</body></html>"
    )


# =============================================================================
# MAIN RENDER
# =============================================================================

def render_worldindices_tab(is_mobile):
    t = get_theme()
    mut = t.get('muted', '#475569')

    with st.spinner('Loading world indices...'):
        data = fetch_world_indices()

    # Last updated timestamp
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).strftime('%d %b %Y %H:%M SGT')
    st.markdown(
        f"<div style='font-size:9px;color:{mut};font-family:{FONTS};"
        f"padding:0 0 8px 0'>Updated: {now_str}</div>",
        unsafe_allow_html=True
    )

    # Two columns
    col_left, col_right = st.columns(2)
    height = 620

    with col_left:
        body = _build_panel(data, 'Day Change %', 'day')
        st_html(_wrap_panel(body, height), height=height)

    with col_right:
        body = _build_panel(data, 'Year to Date %', 'ytd')
        st_html(_wrap_panel(body, height), height=height)
