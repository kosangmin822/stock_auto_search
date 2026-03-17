"""Streamlit dashboard for stock search, reports, and interactive charts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.config import Config
from main import StockAutoSearch


RISE_COLOR = "#d92d20"
FALL_COLOR = "#175cd3"
FLAT_COLOR = "#101828"
LINE_COLOR = "#475467"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap');
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(214, 90, 49, 0.16), transparent 24%),
                radial-gradient(circle at top right, rgba(31, 111, 120, 0.14), transparent 28%),
                linear-gradient(180deg, #f7f2ea 0%, #f4efe6 100%);
            color: #13231c;
            font-family: 'Noto Sans KR', sans-serif;
        }
        .block-container { padding-top: 1.5rem; padding-bottom: 2.4rem; max-width: 1180px; }
        h1, h2, h3 { font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif; letter-spacing: -0.03em; }
        .hero {
            padding: 1.35rem 1.5rem 1.2rem;
            background: linear-gradient(135deg, rgba(255,250,241,0.94), rgba(255,244,229,0.88));
            border: 1px solid rgba(19, 35, 28, 0.08);
            border-radius: 26px;
            box-shadow: 0 14px 36px rgba(29,33,31,0.08);
            margin-bottom: 1rem;
        }
        .hero-kicker { color: #d65a31; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
        .hero-title { font-size: 2.1rem; font-weight: 700; line-height: 1.05; margin-top: 0.35rem; margin-bottom: 0.45rem; }
        .hero-copy { color: #596761; max-width: 780px; font-size: 0.98rem; }
        .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.8rem; margin: 1rem 0 0.8rem; }
        .metric-card { background: rgba(255,255,255,0.68); border: 1px solid rgba(19, 35, 28, 0.08); border-radius: 18px; padding: 0.85rem 0.95rem; }
        .metric-label { color: #596761; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }
        .metric-value { margin-top: 0.35rem; font-size: 1.35rem; font-weight: 700; font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif; }
        .stock-card { background: rgba(255,255,255,0.78); border: 1px solid rgba(19, 35, 28, 0.08); border-radius: 22px; padding: 1rem 1rem 0.6rem; margin-bottom: 0.85rem; }
        .stock-head { display: flex; justify-content: space-between; gap: 0.8rem; align-items: baseline; margin-bottom: 0.35rem; }
        .stock-name { font-size: 1.1rem; font-weight: 700; font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif; }
        .chip { display: inline-block; font-size: 0.72rem; font-weight: 700; padding: 0.24rem 0.55rem; border-radius: 999px; background: rgba(214, 90, 49, 0.12); color: #d65a31; }
        .rise { color: #d92d20; }
        .fall { color: #175cd3; }
        .flat { color: #101828; }
        .muted { color: #596761; }
        .detail-grid { display:grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap:0.55rem; margin-top:0.8rem; margin-bottom:0.8rem; }
        .detail-cell { background: rgba(255,255,255,0.72); border:1px solid rgba(19, 35, 28, 0.08); border-radius:14px; padding:0.7rem 0.8rem; }
        .detail-label { color: #596761; font-size:0.74rem; margin-bottom:0.2rem; }
        .detail-value { font-size:1rem; font-weight:700; font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def get_system() -> StockAutoSearch:
    return StockAutoSearch()


@st.cache_data(show_spinner=False)
def _get_autocomplete_options(markets: Tuple[str, ...]) -> List[Tuple[str, str, str]]:
    master = get_system().get_ticker_master(markets=list(markets))
    return [
        (
            str(item.get("code", "")).zfill(6),
            str(item.get("name", "")).strip(),
            str(item.get("market", "UNKNOWN")).strip() or "UNKNOWN",
        )
        for item in master
        if item.get("code") and item.get("name")
    ]


def _format_candidate(option: Optional[Tuple[str, str, str]]) -> str:
    if option is None:
        return ""
    code, name, market = option
    return f"{name} ({code}) ? {market}"


def _fmt_number(value, digits: int = 0, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
        if digits == 0:
            return f"{int(round(number)):,}{suffix}"
        return f"{number:,.{digits}f}{suffix}"
    except Exception:
        return str(value)


def _fmt_signed_number(value, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
        sign = "+" if number > 0 else ""
        return f"{sign}{int(round(number)):,}{suffix}"
    except Exception:
        return str(value)


def _fmt_pct(value) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return str(value)


def _tone_class(value) -> str:
    try:
        number = float(value or 0)
    except Exception:
        return "flat"
    if number > 0:
        return "rise"
    if number < 0:
        return "fall"
    return "flat"


def _tone_color(value) -> str:
    tone = _tone_class(value)
    if tone == "rise":
        return RISE_COLOR
    if tone == "fall":
        return FALL_COLOR
    return FLAT_COLOR


def _read_recent_reports(limit: int = 12) -> Iterable[Path]:
    report_dir = Path(Config.DATA_DIR) / "reports"
    if not report_dir.exists():
        return []
    return sorted(report_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def _load_report(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@st.cache_data(show_spinner=False)
def _get_chart_history(stock_code: str, lookback_days: int, chart_period: str, minute_interval: int) -> pd.DataFrame:
    history = get_system().get_price_history(
        stock_code,
        lookback_days=lookback_days,
        period=chart_period,
        minute_interval=minute_interval,
    )
    if history is None or history.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    frame = history.reset_index().copy()
    columns = list(frame.columns)
    normalized_names = ["date", "open", "high", "low", "close", "volume"]
    rename_map = {}
    for index, normalized_name in enumerate(normalized_names):
        if index < len(columns):
            rename_map[columns[index]] = normalized_name
    frame = frame.rename(columns=rename_map)
    for column in ["open", "high", "low", "close", "volume"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date").reset_index(drop=True)


def _build_indicator_frame(history: pd.DataFrame) -> pd.DataFrame:
    chart = history.copy()
    close = chart["close"].astype(float)
    chart["MA5"] = close.rolling(5).mean()
    chart["MA20"] = close.rolling(20).mean()
    chart["MA60"] = close.rolling(60).mean()
    middle = close.rolling(20).mean()
    std = close.rolling(20).std()
    chart["BB_UPPER"] = middle + std * 2
    chart["BB_MID"] = middle
    chart["BB_LOWER"] = middle - std * 2
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean().replace(0, pd.NA)
    rs = avg_gain / avg_loss
    chart["RSI14"] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    chart["MACD"] = ema12 - ema26
    chart["MACD_SIGNAL"] = chart["MACD"].ewm(span=9, adjust=False).mean()
    return chart


def _render_candlestick_chart(chart: pd.DataFrame, overlay_fields: List[str], stock_code: str, chart_mode: str) -> None:
    if chart.empty:
        st.info("No chart data available for this timeframe.")
        return

    figure = go.Figure()
    figure.add_trace(
        go.Candlestick(
            x=chart["date"],
            open=chart["open"],
            high=chart["high"],
            low=chart["low"],
            close=chart["close"],
            increasing_line_color=RISE_COLOR,
            decreasing_line_color=FALL_COLOR,
            increasing_fillcolor=RISE_COLOR,
            decreasing_fillcolor=FALL_COLOR,
            name="Price",
        )
    )

    overlay_colors = {
        "MA5": "#f97316",
        "MA20": "#0f766e",
        "MA60": "#7c3aed",
        "BB_UPPER": "#94a3b8",
        "BB_MID": "#64748b",
        "BB_LOWER": "#94a3b8",
    }
    for field in overlay_fields:
        if field not in chart.columns:
            continue
        data = chart[["date", field]].dropna()
        if data.empty:
            continue
        figure.add_trace(
            go.Scatter(
                x=data["date"],
                y=data[field],
                mode="lines",
                line={"color": overlay_colors.get(field, LINE_COLOR), "width": 2},
                name=field,
            )
        )

    label_map = {"minute": "Minute", "daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}
    figure.update_layout(
        title=f"{stock_code} {label_map.get(chart_mode, chart_mode)}",
        height=460,
        margin={"l": 12, "r": 12, "t": 44, "b": 12},
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis={"showgrid": True, "gridcolor": "#f2f4f7", "rangeslider": {"visible": False}, "type": "date"},
        yaxis={"showgrid": True, "gridcolor": "#f2f4f7", "side": "right"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        dragmode="pan",
        hovermode="x unified",
    )
    st.caption("Mouse wheel zoom and drag pan are enabled.")
    st.plotly_chart(
        figure,
        width="stretch",
        config={"scrollZoom": True, "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
        key=f"candle_{stock_code}_{chart_mode}",
    )


def _normalize_recent_ohlcv(rows: List[Dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    columns = list(frame.columns)
    rename_map = {}
    labels = ["Date", "Open", "High", "Low", "Close", "Volume", "Change %"]
    for index, label in enumerate(labels):
        if index < len(columns):
            rename_map[columns[index]] = label
    return frame.rename(columns=rename_map)


def _build_search_preview(report: Dict[str, object]) -> str:
    lines = [f"[Search Report] {report.get('keyword', '')}", f"Generated: {report.get('generated_at', '')}"]
    stocks = report.get("stocks", []) or []
    if not stocks:
        lines.append("No stock data available.")
        return "\n".join(lines)
    for index, item in enumerate(stocks, start=1):
        lines.append(
            f"{index}. {item.get('name')}({item.get('code')}) "
            f"{_fmt_number(item.get('current_price'), suffix=' KRW')} {_fmt_pct(item.get('change_rate'))} "
            f"Vol {_fmt_number(item.get('volume'))}"
        )
    return "\n".join(lines)


def _render_report_actions(system: StockAutoSearch, report: Dict[str, object], title: str) -> None:
    preview = _build_search_preview(report) if report.get("type") == "search" else json.dumps(report, ensure_ascii=False, indent=2)
    col1, col2, col3 = st.columns([1, 1, 2.4])
    if col1.button("Save Report", key=f"save_{title}", width="stretch"):
        st.success(f"Saved: {system.save_report(report)}")
    if col2.button("Send Alert", key=f"notify_{title}", width="stretch"):
        result = system.notifier.send(title, preview)
        st.json(result)
    with col3:
        st.text_area("Alert Preview", value=preview, height=160, key=f"preview_{title}")


def _render_chart_panel(item: Dict[str, object]) -> None:
    stock_code = str(item.get("code", ""))
    lookback_days = int(st.session_state.get("search_lookback", Config.DEFAULT_LOOKBACK_DAYS))
    with st.expander("Chart / Indicators", expanded=True):
        row = st.columns([1.2, 1.2, 2.2])
        chart_mode = row[0].selectbox(
            "Timeframe",
            options=["minute", "daily", "weekly", "monthly"],
            format_func=lambda value: {"minute": "Minute", "daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}[value],
            key=f"chart_mode_{stock_code}",
        )
        minute_interval = row[1].selectbox(
            "Minute",
            options=[1, 2, 3, 5, 10, 15, 30, 60],
            index=3,
            disabled=chart_mode != "minute",
            key=f"minute_interval_{stock_code}",
        )
        if chart_mode == "minute":
            row[2].caption("Minute chart requires working KIS market-data authentication.")
        else:
            row[2].caption("Daily, weekly, and monthly charts use pykrx daily data.")

        history = _get_chart_history(stock_code, lookback_days, chart_mode, int(minute_interval))
        if history.empty:
            if chart_mode == "minute":
                st.warning("Minute data is unavailable. Current KIS authentication is failing with 403.")
            else:
                st.warning("No chart data was returned for this timeframe.")
            return

        chart = _build_indicator_frame(history)
        checkbox_row1 = st.columns(4)
        show_ma5 = checkbox_row1[0].checkbox("MA5", value=True, key=f"ma5_{stock_code}")
        show_ma20 = checkbox_row1[1].checkbox("MA20", value=True, key=f"ma20_{stock_code}")
        show_ma60 = checkbox_row1[2].checkbox("MA60", value=False, key=f"ma60_{stock_code}")
        show_boll = checkbox_row1[3].checkbox("Bollinger", value=False, key=f"boll_{stock_code}")
        checkbox_row2 = st.columns(3)
        show_volume = checkbox_row2[0].checkbox("Volume", value=True, key=f"volume_{stock_code}")
        show_rsi = checkbox_row2[1].checkbox("RSI14", value=False, key=f"rsi_{stock_code}")
        show_macd = checkbox_row2[2].checkbox("MACD", value=False, key=f"macd_{stock_code}")

        overlays: List[str] = []
        if show_ma5:
            overlays.append("MA5")
        if show_ma20:
            overlays.append("MA20")
        if show_ma60:
            overlays.append("MA60")
        if show_boll:
            overlays.extend(["BB_UPPER", "BB_MID", "BB_LOWER"])

        _render_candlestick_chart(chart, overlays, stock_code, chart_mode)
        chart_display = chart.set_index("date")
        if show_volume:
            st.bar_chart(chart_display[["volume"]].dropna(how="all"), width="stretch", height=180)
        if show_rsi:
            st.line_chart(chart_display[["RSI14"]].dropna(how="all"), width="stretch", height=180)
        if show_macd:
            st.line_chart(chart_display[["MACD", "MACD_SIGNAL"]].dropna(how="all"), width="stretch", height=180)


def _render_snapshot_card(item: Dict[str, object]) -> None:
    change_value = float(item.get("change", 0) or 0)
    tone_class = _tone_class(change_value)
    market_cap_eok = None
    if item.get("market_cap") is not None:
        try:
            market_cap_eok = float(item.get("market_cap")) / 100_000_000
        except Exception:
            market_cap_eok = None

    st.markdown(
        f"""
        <div class="stock-card">
            <div class="stock-head">
                <div class="stock-name">{item.get('name', '-')} ({item.get('code', '-')})</div>
                <div class="chip">{item.get('market', 'UNKNOWN')}</div>
            </div>
            <div style="font-size:1.35rem;font-weight:700;">{_fmt_number(item.get('current_price'), suffix=' KRW')}</div>
            <div class="{tone_class}" style="margin-top:0.2rem;font-size:1.02rem;font-weight:700;">{_fmt_signed_number(item.get('change'), suffix=' KRW')} {_fmt_pct(item.get('change_rate'))}</div>
            <div class="muted" style="margin-top:0.35rem;">Volume {_fmt_number(item.get('volume'))} / Market Cap {_fmt_number(market_cap_eok)} EOK / As of {item.get('as_of', '-')}</div>
            <div class="detail-grid">
                <div class="detail-cell"><div class="detail-label">Prev Close</div><div class="detail-value">{_fmt_number(item.get('previous_close'), suffix=' KRW')}</div></div>
                <div class="detail-cell"><div class="detail-label">Open</div><div class="detail-value" style="color:{_tone_color((item.get('open') or 0) - (item.get('previous_close') or 0))}">{_fmt_number(item.get('open'), suffix=' KRW')}</div></div>
                <div class="detail-cell"><div class="detail-label">High</div><div class="detail-value rise">{_fmt_number(item.get('high'), suffix=' KRW')}</div></div>
                <div class="detail-cell"><div class="detail-label">Low</div><div class="detail-value fall">{_fmt_number(item.get('low'), suffix=' KRW')}</div></div>
                <div class="detail-cell"><div class="detail-label">Current</div><div class="detail-value {tone_class}">{_fmt_number(item.get('current_price'), suffix=' KRW')}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = pd.DataFrame([
        {
            "MA5": item.get("ma5"),
            "MA20": item.get("ma20"),
            "MA60": item.get("ma60"),
            "PER": item.get("per"),
            "PBR": item.get("pbr"),
            "52W High": item.get("high_52w"),
            "52W Low": item.get("low_52w"),
            "Avg Vol 20D": item.get("average_volume_20d"),
        }
    ])
    st.dataframe(metrics, width="stretch", hide_index=True)
    _render_chart_panel(item)
    recent = _normalize_recent_ohlcv(item.get("recent_ohlcv") or [])
    if not recent.empty:
        st.dataframe(recent, width="stretch", hide_index=True)


def _render_search_tab(system: StockAutoSearch) -> None:
    st.subheader("Search Lab")
    market_col1, market_col2, _ = st.columns([1, 1, 3])
    include_kospi = market_col1.checkbox("KOSPI", value=True, key="search_include_kospi")
    include_kosdaq = market_col2.checkbox("KOSDAQ", value=True, key="search_include_kosdaq")
    selected_markets: List[str] = []
    if include_kospi:
        selected_markets.append("KOSPI")
    if include_kosdaq:
        selected_markets.append("KOSDAQ")

    options = _get_autocomplete_options(tuple(selected_markets)) if selected_markets else []
    left, middle, right = st.columns([2.2, 1, 1])
    selected_candidate = left.selectbox(
        "Autocomplete",
        options=options,
        index=None,
        placeholder="Select a stock name or 6-digit ticker",
        format_func=_format_candidate,
        key="search_selected_candidate",
    )
    keyword = left.text_input(
        "Direct Input",
        value="",
        placeholder="Type stock name or 6-digit ticker",
        key="search_direct_keyword",
    )
    limit = middle.number_input("Result Count", min_value=1, max_value=20, step=1, value=3, key="search_limit")
    lookback = right.number_input("Lookback Days", min_value=30, max_value=730, step=10, value=int(Config.DEFAULT_LOOKBACK_DAYS), key="search_lookback")
    submitted = st.button("Run Search", width="stretch", key="search_submit_button")

    if submitted:
        if not selected_markets:
            st.warning("Select at least one market.")
            return
        final_keyword = selected_candidate[0] if selected_candidate else keyword.strip()
        if not final_keyword:
            st.warning("Choose an autocomplete item or enter a ticker/name manually.")
            return
        with st.spinner("Building report..."):
            report = system.build_search_report(final_keyword, limit=int(limit), lookback_days=int(lookback), markets=selected_markets)
        st.session_state["search_report"] = report
        st.session_state["last_report"] = report

    report = st.session_state.get("search_report")
    if not report:
        st.caption("Run a search to populate the report and chart panel.")
        return

    st.write({
        "keyword": report.get("keyword"),
        "generated_at": report.get("generated_at"),
        "matches": report.get("match_count"),
        "snapshots": report.get("snapshot_count"),
    })
    stocks = report.get("stocks", []) or []
    if not stocks:
        st.warning("No stock snapshots were returned.")
    else:
        for item in stocks:
            _render_snapshot_card(item)
    _render_report_actions(system, report, f"search:{report.get('keyword', '')}")


def _render_market_tab(system: StockAutoSearch) -> None:
    st.subheader("Market Radar")
    with st.form("market_form", border=False):
        col1, col2, col3, col4 = st.columns(4)
        direction = col1.selectbox("Direction", ["gainers", "losers"], format_func=lambda value: "Top Gainers" if value == "gainers" else "Top Losers")
        market = col2.selectbox("Market", ["ALL", "KOSPI", "KOSDAQ", "KONEX"])
        limit = col3.number_input("Result Count", min_value=3, max_value=30, step=1, value=10)
        days = col4.number_input("Days", min_value=1, max_value=30, step=1, value=1)
        submitted = st.form_submit_button("Run Market Scan", width="stretch")

    if submitted:
        with st.spinner("Scanning market..."):
            report = system.build_market_report(direction=direction, limit=int(limit), market=market, days=int(days))
        st.session_state["market_report"] = report
        st.session_state["last_report"] = report

    report = st.session_state.get("market_report")
    if not report:
        st.caption("Run the market scan to see movers.")
        return

    st.write({
        "market": report.get("market"),
        "direction": report.get("direction"),
        "generated_at": report.get("generated_at"),
        "rows": report.get("count"),
    })
    stocks = report.get("stocks", []) or []
    if not stocks:
        st.warning("No market scan results are available.")
    else:
        st.dataframe(pd.DataFrame(stocks), width="stretch", hide_index=True)


def _render_report_vault() -> None:
    st.subheader("Report Vault")
    reports = list(_read_recent_reports())
    if not reports:
        st.info("No saved reports found.")
        return
    selected = st.selectbox("Report File", reports, format_func=lambda path: path.name)
    st.json(_load_report(selected), expanded=False)


def _render_alert_center(system: StockAutoSearch) -> None:
    st.subheader("Alert Center")
    st.write({
        "console": Config.ALERT_CONSOLE_ENABLED,
        "file": Config.ALERT_OUTPUT_FILE,
        "webhook_enabled": bool(Config.ALERT_WEBHOOK_URL),
    })
    last_report = st.session_state.get("last_report")
    if not last_report:
        st.info("Create a report first from Search Lab or Market Radar.")
        return
    preview = _build_search_preview(last_report) if last_report.get("type") == "search" else json.dumps(last_report, ensure_ascii=False, indent=2)
    st.text_area("Delivery Preview", value=preview, height=220)
    if st.button("Send Last Report", width="stretch"):
        st.json(system.notifier.send("stock-auto-search", preview))


def main() -> None:
    st.set_page_config(page_title="Stock Auto Search", page_icon=":bar_chart:", layout="wide", initial_sidebar_state="expanded")
    _inject_styles()
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Stock Intelligence Console</div>
            <div class="hero-title">Search, scan, save, notify.</div>
            <div class="hero-copy">Browser-first dashboard for stock search, report storage, alert delivery, and interactive charts.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    system = get_system()
    reports = list(_read_recent_reports())
    webhook_enabled = "ON" if Config.ALERT_WEBHOOK_URL else "OFF"
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card"><div class="metric-label">Default Market</div><div class="metric-value">{Config.DEFAULT_MARKET}</div></div>
            <div class="metric-card"><div class="metric-label">Lookback</div><div class="metric-value">{Config.DEFAULT_LOOKBACK_DAYS}d</div></div>
            <div class="metric-card"><div class="metric-label">Saved Reports</div><div class="metric-value">{len(reports)}</div></div>
            <div class="metric-card"><div class="metric-label">Webhook</div><div class="metric-value">{webhook_enabled}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Control Deck")
        st.caption("Run search and scan workflows from the browser.")
        st.write({"market": Config.DEFAULT_MARKET, "lookback": Config.DEFAULT_LOOKBACK_DAYS, "report_limit": Config.DEFAULT_REPORT_LIMIT})
        st.markdown("---")
        st.caption("Launch")
        st.code("streamlit run ui/dashboard.py", language="bash")

    search_tab, market_tab, vault_tab, alert_tab = st.tabs(["Search Lab", "Market Radar", "Report Vault", "Alert Center"])
    with search_tab:
        _render_search_tab(system)
    with market_tab:
        _render_market_tab(system)
    with vault_tab:
        _render_report_vault()
    with alert_tab:
        _render_alert_center(system)


if __name__ == "__main__":
    main()
