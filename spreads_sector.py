import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import logging

from config import FUTURES_GROUPS, THEMES, SYMBOL_NAMES, FONTS, clean_symbol
from spreads import (compute_sector_spreads, sort_spread_pairs,
                     render_spread_table, render_spread_charts)

logger = logging.getLogger(__name__)

# Intervals: yf fetch string, resample target (None = no resample), bars per trading day
INTERVAL_CONFIG = {
    '15m': {'yf': '15m', 'resample': None, 'bars_per_day': 26, 'max_cal_days': 59},
    '1d':  {'yf': '1d',  'resample': None, 'bars_per_day': 1,  'max_cal_days': None},
    '1wk': {'yf': '1wk', 'resample': None, 'bars_per_day': 0.2,'max_cal_days': None},
}

# Universal lookback list — label: trading days
LOOKBACK_OPTIONS = {
    'YTD':      0,
    '1 Day':    1,
    '2 Days':   2,
    '5 Days':   5,
    '10 Days':  10,
    '30 Days':  30,
    '60 Days':  60,
    '120 Days': 120,
    '240 Days': 240,
    '520 Days': 520,
}

# Ann factors per interval
ANN_FACTORS = {'15m': 26 * 252, '1d': 252, '1wk': 52}


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_interval_data(sector, interval_key, lookback_days):
    cfg = INTERVAL_CONFIG[interval_key]
    symbols = FUTURES_GROUPS.get(sector, [])
    if not symbols:
        return None

    # Convert trading days → calendar days to request
    if lookback_days == 0:  # YTD
        start = datetime.now().replace(month=1, day=1).strftime('%Y-%m-%d')
    else:
        cal_days = int(lookback_days * 1.6)
        if cfg['max_cal_days']:
            cal_days = min(cal_days, cfg['max_cal_days'])
        start = (datetime.now() - pd.Timedelta(days=max(cal_days, 2))).strftime('%Y-%m-%d')

    data = pd.DataFrame()
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(start=start, interval=cfg['yf'])
            if hist.empty:
                continue
            closes = hist['Close'].copy()
            if closes.index.tz is not None:
                closes.index = closes.index.tz_convert('UTC').tz_localize(None)
            if interval_key in ('1d', '1wk'):
                closes.index = closes.index.normalize()
                closes = closes.groupby(closes.index).last()
            data[sym] = closes
        except Exception as e:
            logger.debug(f"[{sym}] fetch error ({interval_key}): {e}")

    if data.empty or len(data.columns) < 2:
        return None
    data = data.ffill().dropna()

    # Trim to requested bars
    if lookback_days > 0:
        bars = int(lookback_days * cfg['bars_per_day'])
        if len(data) > bars:
            data = data.iloc[-bars:]

    if len(data) < 5:
        return None
    return 100 * (data / data.iloc[0])


def render_sector_tab(is_mobile):
    theme_name = st.session_state.get('theme', 'Dark')
    theme = THEMES.get(theme_name, THEMES['Dark'])
    pos_c = theme['pos']
    _lbl = f"color:#e2e8f0;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;font-family:{FONTS}"
    _bg3 = theme.get('bg3', '#0f172a'); _mut = theme.get('muted', '#475569'); _txt2 = theme.get('text2', '#94a3b8')
    ann_factor = 252

    # Controls
    if is_mobile:
        col_sec, col_iv = st.columns([1, 1])
        col_lb, col_sort = st.columns([1, 1])
    else:
        col_sec, col_iv, col_lb, col_sort, col_dir = st.columns([3, 2, 3, 2, 1])

    with col_sec:
        st.markdown(f"<div style='{_lbl}'>SECTOR</div>", unsafe_allow_html=True)
        sector_names = list(FUTURES_GROUPS.keys())
        spread_sector = st.selectbox("Sector", sector_names,
            index=sector_names.index(st.session_state.get('spread_sector', sector_names[0])),
            key='spread_sector_sel', label_visibility='collapsed')
        st.session_state.spread_sector = spread_sector

    with col_iv:
        st.markdown(f"<div style='{_lbl}'>INTERVAL</div>", unsafe_allow_html=True)
        iv_keys = list(INTERVAL_CONFIG.keys())
        interval_key = st.selectbox("Interval", iv_keys,
            index=iv_keys.index(st.session_state.get('spread_interval', '1d')),
            key='spread_interval_sel', label_visibility='collapsed')
        st.session_state.spread_interval = interval_key
        ann_factor = ANN_FACTORS[interval_key]

    with col_lb:
        st.markdown(f"<div style='{_lbl}'>LOOKBACK</div>", unsafe_allow_html=True)
        lb_keys = list(LOOKBACK_OPTIONS.keys())
        default_lb = st.session_state.get('spread_lookback', 'YTD')
        if default_lb not in lb_keys:
            default_lb = 'YTD'
        lookback_label = st.selectbox("Lookback", lb_keys,
            index=lb_keys.index(default_lb),
            key='spread_lookback_sel', label_visibility='collapsed')
        st.session_state.spread_lookback = lookback_label
        lookback_days = LOOKBACK_OPTIONS[lookback_label]

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
        data = _fetch_interval_data(spread_sector, interval_key, lookback_days)

    if data is None or len(data.columns) < 2:
        note = ' (15m limited to last 60 calendar days)' if interval_key == '15m' else ''
        st.markdown(f"<div style='padding:12px;color:{_mut};font-size:11px;font-family:{FONTS}'>Need at least 2 assets with data for spread analysis{note}</div>", unsafe_allow_html=True)
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
    fmt = '%d %b %H:%M' if interval_key == '15m' else '%d %b %Y'
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
