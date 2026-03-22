import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import logging

from config import FUTURES_GROUPS, THEMES, SYMBOL_NAMES, FONTS, clean_symbol
from spreads import (compute_sector_spreads, sort_spread_pairs,
                     render_spread_table, render_spread_charts)

logger = logging.getLogger(__name__)

INTERVAL_CONFIG = {
    '1h':  {'yf': '1h',  'resample': None, 'ann_factor': 1764, 'max_days': 729,
            'lookbacks': {'3 Days': 21, '7 Days': 49, '14 Days': 98, '30 Days': 210}},
    '4h':  {'yf': '1h',  'resample': '4h', 'ann_factor': 504,  'max_days': 729,
            'lookbacks': {'7 Days': 14, '14 Days': 28, '30 Days': 60, '60 Days': 120}},
    '1d':  {'yf': '1d',  'resample': None, 'ann_factor': 252,  'max_days': None,
            'lookbacks': {'30 Days': 30, '60 Days': 60, '120 Days': 120, '240 Days': 240}},
    '1wk': {'yf': '1wk', 'resample': None, 'ann_factor': 52,   'max_days': None,
            'lookbacks': {'26 Weeks': 26, '52 Weeks': 52, '2 Years': 104, '3 Years': 156}},
}

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_interval_data(sector, interval_key, lookback_bars):
    cfg = INTERVAL_CONFIG[interval_key]
    symbols = FUTURES_GROUPS.get(sector, [])
    if not symbols:
        return None
    bars_per_day = {'1h': 7, '4h': 2, '1d': 1, '1wk': 0.2}
    cal_days = int(lookback_bars / bars_per_day.get(interval_key, 1) * 1.6)
    if cfg['max_days']:
        cal_days = min(cal_days, cfg['max_days'])
    start = (datetime.now() - pd.Timedelta(days=max(cal_days, 5))).strftime('%Y-%m-%d')
    data = pd.DataFrame()
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(start=start, interval=cfg['yf'])
            if hist.empty:
                continue
            closes = hist['Close'].copy()
            if closes.index.tz is not None:
                closes.index = closes.index.tz_convert('UTC').tz_localize(None)
            if cfg['resample']:
                closes = closes.resample(cfg['resample']).last().dropna()
            if interval_key in ('1d', '1wk'):
                closes.index = closes.index.normalize()
                closes = closes.groupby(closes.index).last()
            data[sym] = closes
        except Exception as e:
            logger.debug(f"[{sym}] fetch error ({interval_key}): {e}")
    if data.empty or len(data.columns) < 2:
        return None
    data = data.ffill().dropna()
    if len(data) > lookback_bars:
        data = data.iloc[-lookback_bars:]
    if len(data) < 5:
        return None
    return 100 * (data / data.iloc[0])


def render_sector_tab(is_mobile):
    theme_name = st.session_state.get('theme', 'Dark')
    theme = THEMES.get(theme_name, THEMES['Dark'])
    pos_c = theme['pos']
    _lbl = f"color:#e2e8f0;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;font-family:{FONTS}"
    _bg3 = theme.get('bg3', '#0f172a'); _mut = theme.get('muted', '#475569'); _txt2 = theme.get('text2', '#94a3b8')
    # Controls
    if is_mobile:
        col_sec, col_iv = st.columns([1, 1])
        col_lb, col_sort = st.columns([1, 1])
    else:
        col_sec, col_iv, col_lb, col_sort, col_dir = st.columns([3, 2, 2, 2, 1])

    with col_sec:
        st.markdown(f"<div style='{_lbl}'>SECTOR</div>", unsafe_allow_html=True)
        sector_names = list(FUTURES_GROUPS.keys())
        default_sec = st.session_state.get('spread_sector', sector_names[0])
        if default_sec not in sector_names:
            default_sec = sector_names[0]
        spread_sector = st.selectbox("Sector", sector_names,
            index=sector_names.index(default_sec),
            key='spread_sector_sel', label_visibility='collapsed')
        st.session_state.spread_sector = spread_sector

    with col_iv:
        st.markdown(f"<div style='{_lbl}'>INTERVAL</div>", unsafe_allow_html=True)
        interval_key = st.selectbox("Interval", list(INTERVAL_CONFIG.keys()),
            index=list(INTERVAL_CONFIG.keys()).index(
                st.session_state.get('spread_interval', '1d')),
            key='spread_interval_sel', label_visibility='collapsed')
        st.session_state.spread_interval = interval_key

    cfg = INTERVAL_CONFIG[interval_key]
    ann_factor = cfg['ann_factor']

    with col_lb:
        st.markdown(f"<div style='{_lbl}'>LOOKBACK</div>", unsafe_allow_html=True)
        lb_keys = list(cfg['lookbacks'].keys())
        lookback_label = st.selectbox("Lookback", lb_keys, index=0,
            key='spread_lookback_sel', label_visibility='collapsed')
        lookback_bars = cfg['lookbacks'][lookback_label]
    with col_sort:
        st.markdown(f"<div style='{_lbl}'>SORT BY</div>", unsafe_allow_html=True)
        sort_options = ['Composite', 'Sharpe', 'Sortino', 'MAR', 'R²', 'Total', 'Win Rate']
        sort_key = st.selectbox("Sort", sort_options, index=0,
            key='spread_sort_sel', label_visibility='collapsed')
    if not is_mobile:
        with col_dir:
            st.markdown(f"<div style='{_lbl}'>ORDER</div>", unsafe_allow_html=True)
            sort_dir = st.selectbox("Dir", ['Desc', 'Asc'], index=0,
                key='spread_dir_sel', label_visibility='collapsed')
            ascending = sort_dir == 'Asc'
    else:
        ascending = False

    # Fetch and compute
    with st.spinner(f'Computing {spread_sector} spreads ({interval_key} · {lookback_label})...'):
        data = _fetch_interval_data(spread_sector, interval_key, lookback_bars)

    if data is None or len(data.columns) < 2:
        st.markdown(f"<div style='padding:12px;color:{_mut};font-size:11px;font-family:{FONTS}'>Need at least 2 assets with data for spread analysis</div>", unsafe_allow_html=True)
        return

    pairs = compute_sector_spreads(data, ann_factor)
    if not pairs:
        st.markdown(f"<div style='padding:12px;color:{_mut};font-size:11px;font-family:{FONTS}'>No spreads computed</div>", unsafe_allow_html=True)
        return

    sorted_pairs = sort_spread_pairs(pairs, sort_key, ascending)

    # Info bar
    best_long_sym = pairs[0].get('best_long_sym', '')
    best_long_sharpe = pairs[0].get('best_long_sharpe', 0)
    best_long_name = SYMBOL_NAMES.get(best_long_sym, clean_symbol(best_long_sym))
    n_combos = len(pairs)
    n_beats = sum(1 for p in pairs if p['beats_long'])
    fmt = '%d %b %H:%M' if interval_key in ('1h', '4h') else '%d %b %Y'
    start_date = data.index[0].strftime(fmt)
    end_date = data.index[-1].strftime(fmt)

    beats_c = pos_c if n_beats > 0 else _mut
    st.markdown(f"""
        <div style='padding:5px 10px;background-color:{_bg3};font-family:{FONTS};display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px;border-radius:4px'>
            <span style='color:{_mut};font-size:10px'>{n_combos} pairs · {start_date} → {end_date} · {interval_key}</span>
            <span style='color:{_txt2};font-size:10px'>
                Best long: <span style='color:{pos_c};font-weight:600'>{best_long_name}</span>
                <span style='color:{_mut}'>Sharpe {best_long_sharpe:.2f}</span>
                &nbsp;·&nbsp;
                <span style='color:{beats_c}'>{n_beats} spread{"s" if n_beats != 1 else ""} beat{"s" if n_beats == 1 else ""} it</span>
            </span>
        </div>""", unsafe_allow_html=True)

    # Charts (top 6)
    render_spread_charts(sorted_pairs, data, theme, mobile=is_mobile)

    # Table (top 10)
    render_spread_table(sorted_pairs, theme, top_n=10)
