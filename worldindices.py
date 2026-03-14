"""
SANPO — World Indices tab
Centre-axis bars, auto label placement, clean header, blue separators
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


def _centre_bar(val, max_abs, pos_c, neg_c, bar_bg):
    """
    Centre-axis bar. Label auto-placed:
    - inside bar if bar >= 20% wide
    - outside bar if bar < 20%
    Always stays within the 50% half.
    """
    centre_line = (
        f"<div style='position:absolute;left:50%;top:0;width:1px;"
        f"height:100%;background:#2d3f55;z-index:2'></div>"
    )

    if val is None or max_abs == 0:
        return (
            f"<div style='flex:1;position:relative;height:20px;"
            f"background:{bar_bg};border-radius:2px;overflow:visible'>"
            f"{centre_line}</div>"
        )

    is_pos = val >= 0
    color  = pos_c if is_pos else neg_c
    # bar occupies up to 46% of total width (each side from centre = 46%)
    pct = min(abs(val) / max_abs * 46, 46)
    sign = '+' if is_pos else ''
    label = f"{sign}{val:.2f}%"

    # Label placement: inside if bar >= 18%, outside otherwise
    INSIDE_THRESH = 18
    if is_pos:
        bar_css  = f"left:50%;width:{pct:.1f}%;background:linear-gradient(90deg,{color}30,{color}65)"
        if pct >= INSIDE_THRESH:
            lbl_css = f"right:{50 - pct + 2:.1f}%;color:{color}"
        else:
            lbl_css = f"left:{50 + pct + 1:.1f}%;color:{color}"
    else:
        bar_css  = f"right:50%;width:{pct:.1f}%;background:linear-gradient(270deg,{color}30,{color}65)"
        if pct >= INSIDE_THRESH:
            lbl_css = f"left:{50 - pct + 2:.1f}%;color:{color}"
        else:
            lbl_css = f"right:{50 + pct + 1:.1f}%;color:{color}"

    return (
        f"<div style='flex:1;position:relative;height:20px;"
        f"background:{bar_bg};border-radius:2px;overflow:hidden'>"
        f"<div style='position:absolute;top:0;{bar_css};height:100%;border-radius:2px'></div>"
        f"{centre_line}"
        f"<span style='position:absolute;top:50%;transform:translateY(-50%);{lbl_css};"
        f"font-size:9.5px;font-weight:700;white-space:nowrap;"
        f"font-variant-numeric:tabular-nums;z-index:3'>{label}</span>"
        f"</div>"
    )


def _build_panel(data):
    t   = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bg3 = t.get('bg3', '#0f172a')
    bdr = t.get('border', '#1e293b')
    mut = t.get('muted', '#475569')
    pos_c = t.get('pos', '#4ade80')
    neg_c = t.get('neg', '#f59e0b')
    bar_bg = bg3
    blue   = '#60a5fa'   # lighter blue for region separator
    divider= '#2d3f55'   # subtle vertical divider between DAY/YTD

    # Global scaling
    all_day = [abs(data.get(s,{}).get('day') or 0)
               for r in WORLD_INDICES.values() for s,_ in r]
    all_ytd = [abs(data.get(s,{}).get('ytd') or 0)
               for r in WORLD_INDICES.values() for s,_ in r]
    max_day = max(all_day) if all_day else 1.0
    max_ytd = max(all_ytd) if all_ytd else 1.0

    HDR = "font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f8fafc"

    # Header row
    html = f"""<div style='font-family:{FONTS}'>
        <div style='display:flex;align-items:center;padding:5px 12px;gap:8px'>
            <div style='width:130px;flex-shrink:0;{HDR}'>INDEX</div>
            <div style='width:80px;flex-shrink:0;{HDR};text-align:right'>PRICE</div>
            <div style='flex:1;{HDR};text-align:center'>DAY %</div>
            <div style='width:1px;background:{divider};height:16px;flex-shrink:0'></div>
            <div style='flex:1;{HDR};text-align:center'>YTD %</div>
        </div>
        <div style='height:1px;background:{bdr};margin:0 12px 2px 12px'></div>"""

    first = True
    for region, indices in WORLD_INDICES.items():
        # Blue region separator (full width solid line)
        if not first:
            html += (
                f"<div style='height:1px;background:{blue};opacity:0.5;"
                f"margin:4px 0'></div>"
            )
        first = False

        # Region label
        html += (
            f"<div style='padding:4px 12px 2px 12px;"
            f"font-size:9px;font-weight:700;letter-spacing:0.12em;"
            f"text-transform:uppercase;color:{blue}'>{region}</div>"
        )

        # Sort by day% desc
        sorted_indices = sorted(
            indices,
            key=lambda x: data.get(x[0], {}).get('day') or -999,
            reverse=True
        )

        for i, (ticker, name) in enumerate(sorted_indices):
            d = data.get(ticker, {})
            price = d.get('price')
            price_str = f"{price:,.2f}" if price else '—'
            row_bg = bg2 if i % 2 == 0 else bg3

            day_bar = _centre_bar(d.get('day'), max_day, pos_c, neg_c, bar_bg)
            ytd_bar = _centre_bar(d.get('ytd'), max_ytd, pos_c, neg_c, bar_bg)

            html += (
                f"<div style='display:flex;align-items:center;background:{row_bg};"
                f"padding:3px 12px;border-bottom:1px solid {bdr}10;gap:8px'>"
                f"<div style='width:130px;font-size:11px;font-weight:600;"
                f"color:#f8fafc;flex-shrink:0;white-space:nowrap;"
                f"overflow:hidden;text-overflow:ellipsis'>{name}</div>"
                f"<div style='width:80px;font-size:10px;font-weight:500;"
                f"color:#ffffff;flex-shrink:0;text-align:right;"
                f"font-variant-numeric:tabular-nums'>{price_str}</div>"
                f"{day_bar}"
                f"<div style='width:1px;height:20px;background:{divider};flex-shrink:0'></div>"
                f"{ytd_bar}"
                f"</div>"
            )

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
    t   = get_theme()
    mut = t.get('muted', '#475569')
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).strftime('%d %b %Y %H:%M SGT')
    st.markdown(
        f"<div style='font-size:9px;color:{mut};font-family:{FONTS};"
        f"padding:0 0 4px 0'>Updated: {now_str}</div>",
        unsafe_allow_html=True
    )
    with st.spinner('Loading world indices...'):
        data = fetch_world_indices()
    height = 780
    st_html(_wrap(_build_panel(data), height), height=height)
