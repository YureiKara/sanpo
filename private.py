"""
SANPO — Private Companies tab
Live price/52W% from yfinance, static funding data from Yahoo Finance
Sort by 52W%, Valuation, Total Raised
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


# (ticker, company, valuation_b, total_funding_b, latest_date, latest_amt, round_class, sector)
# valuation_b and total_funding_b are in billions for sorting
PRIVATE_COMPANIES = [
    ('SPAX.PVT', 'SpaceX',        1427.0,  8.923,   '2026-02-02', '250B',      'Corporate Round', 'Space'),
    ('OPAI.PVT', 'OpenAI',         840.0, 166.07,   '2026-02-26', '110B',      'Series C',        'AI'),
    ('ANTH.PVT', 'Anthropic',      380.0,  53.15,   '2026-02-11', '15.045B',   'Series G-1',      'AI'),
    ('STRI.PVT', 'Stripe',         184.4,   8.733,  '2026-02-23', '--',        'Tender Offer 3',  'Fintech'),
    ('DATB.PVT', 'Databricks',     138.4,  20.551,  '2026-02-08', '5B',        'Series L',        'Data & Analytics'),
    ('ANIN.PVT', 'Anduril',         84.5,   6.955,  '2026-01-13', '500M',      'Series G-1',      'Defense'),
    ('RAMP.PVT', 'Ramp',            32.7,   2.191,  '2025-11-16', '300M',      'Series E-3',      'Fintech'),
    ('CESY.PVT', 'Cerebras',        25.9,   2.923,  '2026-02-03', '1.014B',    'Series H',        'Hardware'),
    ('PEAI.PVT', 'Perplexity',      20.4,   2.254,  '2025-09-25', '525M',      'Series E-6',      'AI'),
    ('RIPP.PVT', 'Rippling',        19.4,   1.414,  '2025-05-08', '460M',      'Series G',        'HR/Admin'),
    ('EPGA.PVT', 'Epic Games',      18.0,   7.53,   '2024-02-07', '1.5B',      'Corporate Round', 'Gaming'),
    ('RIPL.PVT', 'Ripple',          17.7,   0.575,  '2016-09-14', '44.5M',     'Series B',        'Crypto'),
    ('FANA.PVT', 'Fanatics',        17.1,   4.404,  '2022-12-05', '700M',      'Private Equity',  'Commerce'),
    ('NEUR.PVT', 'Neuralink',       14.9,   1.337,  '2025-06-01', '650M',      'Series E',        'Biotech'),
    ('CUES.PVT', 'Crusoe Energy',   14.6,   2.62,   '2025-10-23', '1.375B',    'Series E',        'Energy'),
    ('SKIA.PVT', 'Skild AI',        14.0,   2.217,  '2026-01-13', '694M',      'Series C',        'Hardware'),
    ('POLA.PVT', 'Polymarket',      12.3,   1.27,   '2025-10-06', '1B',        'Series D',        'Crypto'),
    ('KLSH.PVT', 'Kalshi',          11.1,   1.531,  '2025-11-19', '1B',        'Series E',        'Fintech'),
    ('LAMD.PVT', 'Lambda',          11.1,   2.364,  '2025-11-17', '410M',      'Series E-3',      'Data & Analytics'),
    ('KRAK.PVT', 'Kraken',          10.6,   0.965,  '2025-11-17', '200M',      'Series D',        'Crypto'),
]


def _fmt_val(b):
    if b is None: return '—'
    if b >= 1000: return f"${b/1000:.3f}T"
    return f"${b:.3f}B"


def _fmt_raised(b):
    if b is None: return '—'
    if b >= 1: return f"${b:.3f}B"
    return f"${b*1000:.0f}M"


@st.cache_data(ttl=600, max_entries=3, show_spinner=False)
def fetch_prices():
    results = {}
    for row in PRIVATE_COMPANIES:
        ticker = row[0]
        try:
            fi = yf.Ticker(ticker).fast_info
            last_price  = fi.get('lastPrice')
            year_change = fi.get('yearChange')
            ytd_chg = (year_change * 100) if year_change is not None else None
            results[ticker] = {'price': last_price, 'ytd': ytd_chg}
        except Exception as e:
            logger.warning(f"Error {ticker}: {e}")
            results[ticker] = {'price': None, 'ytd': None}
    return results


def _fmt_pct(val):
    if val is None: return '—', '#475569'
    sign = '+' if val >= 0 else ''
    color = '#4ade80' if val >= 0 else '#f59e0b'
    return f"{sign}{val:.2f}%", color


def _build_table(data, sort_by):
    t   = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bg3 = t.get('bg3', '#0f172a')
    bdr = t.get('border', '#1e293b')
    mut = t.get('muted', '#475569')
    acc = t.get('accent', '#4ade80')
    blue = '#60a5fa'

    # Sort
    rows = list(PRIVATE_COMPANIES)
    if sort_by == '52W %':
        rows.sort(key=lambda x: data.get(x[0], {}).get('ytd') or -999, reverse=True)
    elif sort_by == 'Valuation':
        rows.sort(key=lambda x: x[2], reverse=True)
    elif sort_by == 'Total Raised':
        rows.sort(key=lambda x: x[3], reverse=True)

    HDR = "font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f8fafc"

    html = f"""<div style='font-family:{FONTS}'>
        <div style='display:flex;align-items:center;padding:5px 12px;
                    border-bottom:1px solid {bdr};gap:8px;white-space:nowrap'>
            <div style='width:80px;flex-shrink:0;{HDR}'>SYMBOL</div>
            <div style='width:130px;flex-shrink:0;{HDR}'>COMPANY</div>
            <div style='width:65px;flex-shrink:0;{HDR};text-align:right'>PRICE</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>52W %</div>
            <div style='width:90px;flex-shrink:0;{HDR};text-align:right'>LATEST DATE</div>
            <div style='width:75px;flex-shrink:0;{HDR};text-align:right'>LATEST AMT</div>
            <div style='width:110px;flex-shrink:0;{HDR}'>ROUND</div>
            <div style='flex:1;{HDR}'>SECTOR</div>
        </div>"""

    for i, row in enumerate(rows):
        ticker, company, val_b, raised_b, latest_date, latest_amt, round_class, sector = row
        d = data.get(ticker, {})
        price = d.get('price')
        ytd   = d.get('ytd')

        price_str     = f"${price:,.2f}" if price else '—'
        ytd_str, ytd_c = _fmt_pct(ytd)
        row_bg = bg2 if i % 2 == 0 else bg3

        html += f"""
        <div style='display:flex;align-items:center;background:{row_bg};
                    padding:5px 12px;border-bottom:1px solid {bdr}12;
                    gap:8px;white-space:nowrap'>
            <div style='width:80px;flex-shrink:0;font-size:10px;
                        font-weight:600;color:{acc}'>{ticker}</div>
            <div style='width:130px;flex-shrink:0;font-size:11px;
                        font-weight:600;color:#f8fafc'>{company}</div>
            <div style='width:65px;flex-shrink:0;font-size:10px;
                        color:#ffffff;text-align:right;
                        font-variant-numeric:tabular-nums'>{price_str}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;
                        font-weight:700;color:{ytd_c};text-align:right;
                        font-variant-numeric:tabular-nums'>{ytd_str}</div>
            <div style='width:90px;flex-shrink:0;font-size:10px;
                        color:#94a3b8;text-align:right'>{latest_date}</div>
            <div style='width:75px;flex-shrink:0;font-size:10px;
                        color:#94a3b8;text-align:right'>{latest_amt}</div>
            <div style='width:110px;flex-shrink:0;font-size:10px;
                        color:#94a3b8'>{round_class}</div>
            <div style='flex:1;font-size:10px;color:{mut}'>{sector}</div>
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
        f"::-webkit-scrollbar {{ width:4px; height:4px; }}"
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

    # Top row: timestamp left, sort right
    col_ts, col_spacer, col_sort = st.columns([2, 3, 1])
    with col_ts:
        st.markdown(
            f"<div style='font-size:9px;color:#f8fafc;font-family:{FONTS};"
            f"padding:28px 0 0 0'>Updated: {now_str}</div>",
            unsafe_allow_html=True
        )
    with col_sort:
        st.markdown(
            f"<div style='font-size:9px;font-weight:700;color:#e2e8f0;"
            f"font-family:{FONTS};text-transform:uppercase;"
            f"letter-spacing:0.08em;margin-bottom:-18px'>SORT BY</div>",
            unsafe_allow_html=True
        )
        sort_by = st.selectbox(
            'sort_private', ['Valuation', '52W %', 'Total Raised'],
            key='private_sort', label_visibility='collapsed'
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.spinner('Loading private companies...'):
        data = fetch_prices()

    height = 680
    st_html(_wrap(_build_table(data, sort_by), height), height=height)
