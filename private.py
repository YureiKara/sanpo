"""
SANPO — Private Companies tab
Matches Yahoo Finance private companies table exactly
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


# Static data from Yahoo Finance (valuation/funding doesn't change daily)
PRIVATE_COMPANIES = [
    # (ticker, company, valuation, total_funding, latest_date, latest_amount, round_class, sector)
    ('SPAX.PVT', 'SpaceX',           '1.427T',  '8.923B',  '2026-02-02', '250B',      'Corporate Round', 'Space'),
    ('OPAI.PVT', 'OpenAI',           '840B',    '166.07B', '2026-02-26', '110B',      'Series C',        'Artificial Intelligence'),
    ('ANTH.PVT', 'Anthropic',        '380.005B','53.15B',  '2026-02-11', '15.045B',   'Series G-1',      'Artificial Intelligence'),
    ('STRI.PVT', 'Stripe',           '184.401B','8.733B',  '2026-02-23', '--',        'Tender Offer 3',  'Financial Services'),
    ('DATB.PVT', 'Databricks',       '138.436B','20.551B', '2026-02-08', '5B',        'Series L',        'Data and Analytics'),
    ('ANIN.PVT', 'Anduril',          '84.495B', '6.955B',  '2026-01-13', '500M',      'Series G-1',      'Gov & Military'),
    ('RAMP.PVT', 'Ramp',             '32.722B', '2.191B',  '2025-11-16', '300M',      'Series E-3',      'Financial Services'),
    ('CESY.PVT', 'Cerebras',         '25.929B', '2.923B',  '2026-02-03', '1.014B',    'Series H',        'Hardware'),
    ('PEAI.PVT', 'Perplexity',       '20.391B', '2.254B',  '2025-09-25', '525M',      'Series E-6',      'Artificial Intelligence'),
    ('RIPP.PVT', 'Rippling',         '19.386B', '1.414B',  '2025-05-08', '460.183M',  'Series G',        'Admin Services'),
    ('EPGA.PVT', 'Epic Games',       '17.991B', '7.53B',   '2024-02-07', '1.5B',      'Corporate Round', 'Media & Entertainment'),
    ('RIPL.PVT', 'Ripple',           '17.71B',  '575.065M','2016-09-14', '44.477M',   'Series B',        'Blockchain & Crypto'),
    ('FANA.PVT', 'Fanatics',         '17.093B', '4.404B',  '2022-12-05', '700M',      'Private Equity 3','Commerce'),
    ('NEUR.PVT', 'Neuralink',        '14.865B', '1.337B',  '2025-06-01', '650M',      'Series E',        'Biotechnology'),
    ('CUES.PVT', 'Crusoe Energy',    '14.647B', '2.62B',   '2025-10-23', '1.375B',    'Series E',        'Energy'),
    ('SKIA.PVT', 'Skild AI',         '13.999B', '2.217B',  '2026-01-13', '694.067M',  'Series C',        'Hardware'),
    ('POLA.PVT', 'Polymarket',       '12.295B', '1.27B',   '2025-10-06', '1B',        'Series D',        'Blockchain & Crypto'),
    ('KLSH.PVT', 'Kalshi',           '11.115B', '1.531B',  '2025-11-19', '999.997M',  'Series E',        'Financial Services'),
    ('LAMD.PVT', 'Lambda',           '11.053B', '2.364B',  '2025-11-17', '410.284M',  'Series E-3',      'Data and Analytics'),
    ('KRAK.PVT', 'Kraken',           '10.581B', '965.021M','2025-11-17', '200M',      'Series D',        'Blockchain & Crypto'),
]


@st.cache_data(ttl=600, max_entries=3, show_spinner=False)
def fetch_private_companies():
    results = {}
    for row in PRIVATE_COMPANIES:
        ticker = row[0]
        try:
            fi = yf.Ticker(ticker).fast_info
            last_price  = fi.get('lastPrice')
            year_change = fi.get('yearChange')
            year_high   = fi.get('yearHigh')
            year_low    = fi.get('yearLow')
            ytd_chg = (year_change * 100) if year_change is not None else None
            results[ticker] = {
                'price': last_price,
                'ytd': ytd_chg,
                'high52': year_high,
                'low52': year_low,
            }
        except Exception as e:
            logger.warning(f"Error fetching {ticker}: {e}")
            results[ticker] = {'price': None, 'ytd': None, 'high52': None, 'low52': None}
    return results


def _fmt_pct(val):
    if val is None:
        return '—', '#475569'
    sign = '+' if val >= 0 else ''
    color = '#4ade80' if val >= 0 else '#f59e0b'
    return f"{sign}{val:.2f}%", color


def _build_table(data):
    t   = get_theme()
    bg2 = t.get('bg2', '#0a0f1a')
    bg3 = t.get('bg3', '#0f172a')
    bdr = t.get('border', '#1e293b')
    mut = t.get('muted', '#475569')
    acc = t.get('accent', '#4ade80')

    HDR = "font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f8fafc"

    html = f"""<div style='font-family:{FONTS}'>
        <div style='display:flex;align-items:center;padding:5px 12px;
                    border-bottom:1px solid {bdr};gap:8px;white-space:nowrap'>
            <div style='width:80px;flex-shrink:0;{HDR}'>SYMBOL</div>
            <div style='width:130px;flex-shrink:0;{HDR}'>COMPANY</div>
            <div style='width:65px;flex-shrink:0;{HDR};text-align:right'>PRICE</div>
            <div style='width:70px;flex-shrink:0;{HDR};text-align:right'>52W CHG%</div>
            <div style='width:80px;flex-shrink:0;{HDR};text-align:right'>VALUATION</div>
            <div style='width:80px;flex-shrink:0;{HDR};text-align:right'>TOTAL RAISED</div>
            <div style='width:90px;flex-shrink:0;{HDR};text-align:center'>LATEST DATE</div>
            <div style='width:80px;flex-shrink:0;{HDR};text-align:right'>LATEST AMT</div>
            <div style='width:110px;flex-shrink:0;{HDR}'>ROUND</div>
            <div style='flex:1;{HDR}'>SECTOR</div>
        </div>"""

    for i, row in enumerate(PRIVATE_COMPANIES):
        ticker, company, valuation, total_funding, latest_date, latest_amt, round_class, sector = row
        d = data.get(ticker, {})
        price   = d.get('price')
        ytd     = d.get('ytd')

        price_str = f"${price:,.2f}" if price else '—'
        ytd_str, ytd_c = _fmt_pct(ytd)
        row_bg = bg2 if i % 2 == 0 else bg3

        html += f"""
        <div style='display:flex;align-items:center;background:{row_bg};
                    padding:5px 12px;border-bottom:1px solid {bdr}12;
                    gap:8px;white-space:nowrap'>
            <div style='width:80px;flex-shrink:0;font-size:10px;
                        font-weight:600;color:{acc}'>{ticker}</div>
            <div style='width:130px;flex-shrink:0;font-size:11px;
                        font-weight:600;color:#f8fafc;overflow:hidden;
                        text-overflow:ellipsis'>{company}</div>
            <div style='width:65px;flex-shrink:0;font-size:10px;
                        font-weight:500;color:#ffffff;text-align:right;
                        font-variant-numeric:tabular-nums'>{price_str}</div>
            <div style='width:70px;flex-shrink:0;font-size:10px;
                        font-weight:700;color:{ytd_c};text-align:right;
                        font-variant-numeric:tabular-nums'>{ytd_str}</div>
            <div style='width:80px;flex-shrink:0;font-size:10px;
                        font-weight:600;color:{acc};text-align:right'>{valuation}</div>
            <div style='width:80px;flex-shrink:0;font-size:10px;
                        color:#94a3b8;text-align:right'>{total_funding}</div>
            <div style='width:90px;flex-shrink:0;font-size:10px;
                        color:#94a3b8;text-align:center'>{latest_date}</div>
            <div style='width:80px;flex-shrink:0;font-size:10px;
                        color:#94a3b8;text-align:right'>{latest_amt}</div>
            <div style='width:110px;flex-shrink:0;font-size:10px;
                        color:#94a3b8;overflow:hidden;text-overflow:ellipsis'>{round_class}</div>
            <div style='flex:1;font-size:10px;color:#475569;
                        overflow:hidden;text-overflow:ellipsis'>{sector}</div>
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
        f"body {{ background:transparent; font-family:{FONTS}; color:{txt}; overflow-x:auto; overflow-y:auto; }}"
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

    st.markdown(
        f"<div style='font-size:9px;color:#f8fafc;font-family:{FONTS};"
        f"padding:0 0 6px 0'>Updated: {now_str} · Valuation data: Yahoo Finance / Forge</div>",
        unsafe_allow_html=True
    )

    with st.spinner('Loading private companies...'):
        data = fetch_private_companies()

    height = 680
    st_html(_wrap(_build_table(data), height), height=height)
