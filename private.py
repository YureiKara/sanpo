"""
SANPO — Private Companies tab
Pulls data via yfinance fast_info for .PVT tickers
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


PRIVATE_COMPANIES = [
    ('SPAX.PVT', 'SpaceX',              'Space'),
    ('OPAI.PVT', 'OpenAI',              'AI'),
    ('ANTH.PVT', 'Anthropic',           'AI'),
    ('STRI.PVT', 'Stripe',              'Fintech'),
    ('DATB.PVT', 'Databricks',          'Data & Analytics'),
    ('ANIN.PVT', 'Anduril',             'Defense'),
    ('RAMP.PVT', 'Ramp',                'Fintech'),
    ('CESY.PVT', 'Cerebras',            'Hardware'),
    ('PEAI.PVT', 'Perplexity',          'AI'),
    ('RIPP.PVT', 'Rippling',            'HR/Admin'),
    ('EPGA.PVT', 'Epic Games',          'Gaming'),
    ('RIPL.PVT', 'Ripple',              'Crypto'),
    ('FANA.PVT', 'Fanatics',            'Commerce'),
    ('NEUR.PVT', 'Neuralink',           'Biotech'),
    ('CUES.PVT', 'Crusoe Energy',       'Energy'),
    ('SKIA.PVT', 'Skild AI',            'Hardware'),
    ('POLA.PVT', 'Polymarket',          'Crypto'),
    ('KLSH.PVT', 'Kalshi',              'Fintech'),
    ('LAMD.PVT', 'Lambda',              'Data & Analytics'),
    ('KRAK.PVT', 'Kraken',              'Crypto'),
]


@st.cache_data(ttl=600, max_entries=3, show_spinner=False)
def fetch_private_companies():
    results = {}
    for ticker, name, sector in PRIVATE_COMPANIES:
        try:
            fi = yf.Ticker(ticker).fast_info
            last_price    = fi.get('lastPrice')
            prev_close    = fi.get('previousClose') or fi.get('regularMarketPreviousClose')
            year_change   = fi.get('yearChange')
            market_cap    = fi.get('marketCap')
            year_high     = fi.get('yearHigh')
            year_low      = fi.get('yearLow')

            day_chg = None
            if last_price and prev_close and prev_close > 0:
                day_chg = (last_price - prev_close) / prev_close * 100

            ytd_chg = None
            if year_change is not None:
                ytd_chg = year_change * 100

            results[ticker] = {
                'name': name,
                'sector': sector,
                'price': last_price,
                'day': day_chg,
                'ytd': ytd_chg,
                'mktcap': market_cap,
                'high52': year_high,
                'low52': year_low,
            }
        except Exception as e:
            logger.warning(f"Error fetching {ticker}: {e}")
            results[ticker] = {
                'name': name, 'sector': sector,
                'price': None, 'day': None, 'ytd': None,
                'mktcap': None, 'high52': None, 'low52': None,
            }
    return results


def _fmt_pct(val):
    if val is None:
        return '—', '#475569'
    sign = '+' if val >= 0 else ''
    color = '#4ade80' if val >= 0 else '#f59e0b'
    return f"{sign}{val:.2f}%", color


def _fmt_val(val):
    if val is None:
        return '—'
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


def _build_table(data):
    t   = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bg3 = t.get('bg3', '#0f172a')
    bdr = t.get('border', '#1e293b')
    mut = t.get('muted', '#475569')
    txt = t.get('text', '#e2e8f0')
    acc = t.get('accent', '#4ade80')

    HDR = f"font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f8fafc"

    html = f"""<div style='font-family:{FONTS}'>
        <div style='display:flex;align-items:center;padding:5px 12px;
                    border-bottom:1px solid {bdr};gap:8px'>
            <div style='width:140px;flex-shrink:0;{HDR}'>COMPANY</div>
            <div style='width:90px;flex-shrink:0;{HDR}'>SECTOR</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>PRICE</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>DAY %</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>52W %</div>
            <div style='width:80px;flex-shrink:0;{HDR};text-align:right'>VALUATION</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>52W HIGH</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>52W LOW</div>
        </div>"""

    for i, (ticker, name, sector) in enumerate(PRIVATE_COMPANIES):
        d = data.get(ticker, {})
        price   = d.get('price')
        day     = d.get('day')
        ytd     = d.get('ytd')
        mktcap  = d.get('mktcap')
        high52  = d.get('high52')
        low52   = d.get('low52')

        price_str  = f"${price:,.2f}" if price else '—'
        high_str   = f"${high52:,.2f}" if high52 else '—'
        low_str    = f"${low52:,.2f}" if low52 else '—'
        val_str    = _fmt_val(mktcap)

        day_str, day_c   = _fmt_pct(day)
        ytd_str, ytd_c   = _fmt_pct(ytd)

        row_bg = bg2 if i % 2 == 0 else bg3

        html += f"""
        <div style='display:flex;align-items:center;background:{row_bg};
                    padding:5px 12px;border-bottom:1px solid {bdr}12;gap:8px'>
            <div style='width:140px;flex-shrink:0;font-size:11px;
                        font-weight:600;color:#f8fafc;white-space:nowrap;
                        overflow:hidden;text-overflow:ellipsis'>{name}</div>
            <div style='width:90px;flex-shrink:0;font-size:9px;
                        color:{mut};white-space:nowrap;
                        overflow:hidden;text-overflow:ellipsis'>{sector}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;
                        font-weight:500;color:#ffffff;text-align:right;
                        font-variant-numeric:tabular-nums'>{price_str}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;
                        font-weight:700;color:{day_c};text-align:right;
                        font-variant-numeric:tabular-nums'>{day_str}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;
                        font-weight:700;color:{ytd_c};text-align:right;
                        font-variant-numeric:tabular-nums'>{ytd_str}</div>
            <div style='width:80px;flex-shrink:0;font-size:10px;
                        font-weight:600;color:{acc};text-align:right;
                        font-variant-numeric:tabular-nums'>{val_str}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;
                        color:{txt};text-align:right;
                        font-variant-numeric:tabular-nums'>{high_str}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;
                        color:{txt};text-align:right;
                        font-variant-numeric:tabular-nums'>{low_str}</div>
        </div>"""

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


def render_private_tab(is_mobile):
    t   = get_theme()
    mut = t.get('muted', '#475569')
    sgt = pytz.timezone('Asia/Singapore')
    now_str = datetime.now(sgt).strftime('%d %b %Y %H:%M SGT')

    st.markdown(
        f"<div style='font-size:9px;color:#f8fafc;font-family:{FONTS};"
        f"padding:0 0 6px 0'>Updated: {now_str} · Data via Yahoo Finance / Forge</div>",
        unsafe_allow_html=True
    )

    with st.spinner('Loading private companies...'):
        data = fetch_private_companies()

    height = 680
    st_html(_wrap(_build_table(data), height), height=height)
