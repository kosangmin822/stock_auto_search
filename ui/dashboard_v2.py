"""Streamlit dashboard for stock search, reports, and interactive charts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

from config.config import Config
from main import StockAutoSearch


RISE_COLOR = "#d92d20"
FALL_COLOR = "#175cd3"
FLAT_COLOR = "#101828"
LINE_COLOR = "#475467"
SEARCH_RESULT_LIMIT = 3
SEARCH_LOOKBACK_DAYS = 365
FULL_CHART_START_DATE = "19800104"
INITIAL_VISIBLE_CANDLES = 100


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
        .block-container { padding-top: 1.5rem; padding-bottom: 2.4rem; max-width: 1680px; }
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
        .panel-wrap { background: rgba(255,255,255,0.78); border: 1px solid rgba(19, 35, 28, 0.08); border-radius: 18px; padding: 0.9rem 1rem; margin-bottom: 0.85rem; }
        .panel-title { font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; color: #596761; margin-bottom: 0.7rem; font-weight: 700; }
        .panel-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.6rem; }
        .panel-card { border: 1px solid rgba(19, 35, 28, 0.08); border-radius: 14px; padding: 0.7rem 0.8rem; background: rgba(255,255,255,0.72); }
        .panel-label { color: #596761; font-size: 0.74rem; margin-bottom: 0.2rem; }
        .panel-label.accent { color: #d65a31; font-weight: 700; letter-spacing: 0.04em; }
        .panel-value { font-size: 1rem; font-weight: 700; font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif; }
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


def _panel_value(value, suffix: str = "") -> str:
    return _fmt_number(value, suffix=suffix) if value is not None else "-"


def _panel_decimal(value, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f}{suffix}"
    except Exception:
        return str(value)


def _panel_pct(value) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f}%"
    except Exception:
        return str(value)


def _fmt_large_krw(value) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except Exception:
        return str(value)
    if abs(number) >= 100_000_000:
        return f"{number / 100_000_000:,.0f} EOK"
    return f"{number:,.0f} KRW"


def _item_price_suffix(item: Dict[str, object]) -> str:
    return str(item.get("price_suffix", " KRW"))


def _item_price_digits(item: Dict[str, object]) -> int:
    try:
        return int(item.get("price_digits", 0) or 0)
    except Exception:
        return 0


def _fmt_item_price(item: Dict[str, object], value) -> str:
    return _fmt_number(value, digits=_item_price_digits(item), suffix=_item_price_suffix(item))


def _read_recent_reports(limit: int = 12) -> Iterable[Path]:
    report_dir = Path(Config.DATA_DIR) / "reports"
    if not report_dir.exists():
        return []
    return sorted(report_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def _load_report(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@st.cache_data(show_spinner=False)
def _get_chart_history(stock_code: str, lookback_days: int, chart_period: str, minute_interval: int, full_history: bool = False) -> pd.DataFrame:
    history = get_system().get_price_history(
        stock_code,
        lookback_days=lookback_days,
        period=chart_period,
        minute_interval=minute_interval,
        full_history=full_history,
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


@st.cache_data(show_spinner=False)
def _get_benchmark_chart_history(market: str, lookback_days: int, chart_period: str, full_history: bool = False) -> pd.DataFrame:
    history = get_system().get_market_benchmark_history(
        market,
        lookback_days=lookback_days,
        full_history=full_history,
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

    if chart_period == "weekly":
        frame = (
            frame.set_index("date")
            .resample("W")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )
    elif chart_period == "monthly":
        frame = (
            frame.set_index("date")
            .resample("ME")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )

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


def _render_candlestick_chart(
    chart: pd.DataFrame,
    overlay_fields: List[str],
    stock_code: str,
    chart_mode: str,
    show_volume: bool,
    show_rsi: bool,
    show_macd: bool,
    full_history: bool = False,
    sync_group: Optional[str] = None,
    chart_key_prefix: str = "chart",
    chart_label: Optional[str] = None,
) -> None:
    if chart.empty:
        st.info("No chart data available for this timeframe.")
        return

    source = chart.copy().sort_values("date").reset_index(drop=True)
    source["date"] = pd.to_datetime(source["date"], errors="coerce")
    source = source.dropna(subset=["date", "open", "high", "low", "close"])
    if source.empty:
        st.info("No chart data available for this timeframe.")
        return

    date_min = source["date"].min()
    date_max = source["date"].max()
    is_intraday = chart_mode == "minute"
    source["time_key"] = source["date"].dt.strftime("%Y-%m-%d %H:%M" if is_intraday else "%Y-%m-%d")
    if is_intraday:
        source["chart_time"] = (source["date"].astype("int64") // 10**9).astype(int)
    else:
        source["chart_time"] = source["date"].apply(
            lambda value: {
                "year": int(value.year),
                "month": int(value.month),
                "day": int(value.day),
            }
        )

    candles = [
        {
            "time": row.chart_time,
            "timeKey": row.time_key,
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
        }
        for row in source.itertuples(index=False)
    ]

    volume = []
    if show_volume and "volume" in source.columns:
        for row in source.itertuples(index=False):
            open_price = float(row.open)
            close_price = float(row.close)
            volume.append(
                {
                    "time": row.chart_time,
                    "timeKey": row.time_key,
                    "value": float(row.volume or 0),
                    "color": RISE_COLOR if close_price >= open_price else FALL_COLOR,
                }
            )

    overlay_data: Dict[str, List[Dict[str, float]]] = {}
    for field in overlay_fields:
        if field not in source.columns:
            continue
        data = source[["chart_time", "time_key", field]].dropna()
        if data.empty:
            continue
        overlay_data[field] = [
            {"time": row["chart_time"], "timeKey": row["time_key"], "value": float(row[field])}
            for _, row in data.iterrows()
        ]

    rsi_data: List[Dict[str, float]] = []
    if show_rsi and "RSI14" in source.columns:
        data = source[["chart_time", "time_key", "RSI14"]].dropna()
        rsi_data = [{"time": row.chart_time, "timeKey": row.time_key, "value": float(row.RSI14)} for row in data.itertuples(index=False)]

    macd_data: List[Dict[str, float]] = []
    macd_signal_data: List[Dict[str, float]] = []
    if show_macd and "MACD" in source.columns:
        data = source[["chart_time", "time_key", "MACD"]].dropna()
        macd_data = [{"time": row.chart_time, "timeKey": row.time_key, "value": float(row.MACD)} for row in data.itertuples(index=False)]
        if "MACD_SIGNAL" in source.columns:
            signal = source[["chart_time", "time_key", "MACD_SIGNAL"]].dropna()
            macd_signal_data = [
                {"time": row.chart_time, "timeKey": row.time_key, "value": float(row.MACD_SIGNAL)}
                for row in signal.itertuples(index=False)
            ]

    payload = {
        "candles": candles,
        "volume": volume,
        "overlays": overlay_data,
        "rsi": rsi_data,
        "macd": macd_data,
        "macdSignal": macd_signal_data,
        "isIntraday": is_intraday,
        "showVolume": bool(show_volume),
        "showRsi": bool(show_rsi),
        "showMacd": bool(show_macd),
        "initialVisible": int(min(len(source), INITIAL_VISIBLE_CANDLES)),
        "title": f"{chart_label or stock_code} {chart_mode.title()}" + (" - Full History" if full_history and chart_mode != "minute" else ""),
        "syncGroup": sync_group or "",
        "chartId": f"{chart_key_prefix}_{stock_code}_{chart_mode}",
    }

    pane_count = 1 + int(show_volume) + int(show_rsi) + int(show_macd)
    component_height = 420 + max(0, pane_count - 1) * 140
    html = f"""
    <div id="chart-root" style="width:100%;">
      <div style="font:600 14px Space Grotesk, sans-serif;color:#13231c;margin:0 0 8px 2px;">{{payload_title}}</div>
      <div id="price-wrap" style="position:relative;width:100%;height:360px;margin-bottom:10px;"> 
        <div id="price-pane" style="width:100%;height:360px;"></div>
        <div id="price-tooltip" style="position:absolute;left:12px;top:12px;z-index:20;min-width:220px;padding:10px 12px;border-radius:10px;background:rgba(255,255,255,0.94);border:1px solid #e4e7ec;box-shadow:0 8px 24px rgba(16,24,40,0.08);font:12px/1.45 Noto Sans KR,sans-serif;color:#101828;pointer-events:none;display:none;"></div>
      </div>
      <div id="volume-wrap" style="position:relative;width:100%;height:120px;margin-bottom:10px;display:none;"> 
        <div id="volume-pane" style="width:100%;height:120px;"></div>
        <div id="volume-tooltip" style="position:absolute;left:12px;top:10px;z-index:20;min-width:180px;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.94);border:1px solid #e4e7ec;box-shadow:0 8px 24px rgba(16,24,40,0.08);font:12px/1.45 Noto Sans KR,sans-serif;color:#101828;pointer-events:none;display:none;"></div>
      </div>
      <div id="rsi-wrap" style="position:relative;width:100%;height:120px;margin-bottom:10px;display:none;"> 
        <div id="rsi-pane" style="width:100%;height:120px;"></div>
        <div id="rsi-tooltip" style="position:absolute;left:12px;top:10px;z-index:20;min-width:180px;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.94);border:1px solid #e4e7ec;box-shadow:0 8px 24px rgba(16,24,40,0.08);font:12px/1.45 Noto Sans KR,sans-serif;color:#101828;pointer-events:none;display:none;"></div>
      </div>
      <div id="macd-wrap" style="position:relative;width:100%;height:120px;display:none;"> 
        <div id="macd-pane" style="width:100%;height:120px;"></div>
        <div id="macd-tooltip" style="position:absolute;left:12px;top:10px;z-index:20;min-width:180px;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.94);border:1px solid #e4e7ec;box-shadow:0 8px 24px rgba(16,24,40,0.08);font:12px/1.45 Noto Sans KR,sans-serif;color:#101828;pointer-events:none;display:none;"></div>
      </div>
    </div>
    <script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
    <script>
    const payload = __PAYLOAD__;
    const root = document.getElementById('chart-root');
    root.querySelector('div').textContent = payload.title;
    const priceTooltip = document.getElementById('price-tooltip');
    const volumeTooltip = document.getElementById('volume-tooltip');
    const rsiTooltip = document.getElementById('rsi-tooltip');
    const macdTooltip = document.getElementById('macd-tooltip');
    const syncChannel = (payload.syncGroup && typeof BroadcastChannel !== 'undefined') ? new BroadcastChannel('stock_auto_search_' + payload.syncGroup) : null;
    let syncing = false;
    let lastRangeKey = '';

    function paneStyle(height) {{
      return {{
        width: root.clientWidth || 820,
        height,
        layout: {{ background: {{ color: '#ffffff' }}, textColor: '#667085' }},
        grid: {{ vertLines: {{ color: '#f2f4f7' }}, horzLines: {{ color: '#f2f4f7' }} }},
        rightPriceScale: {{ borderColor: '#e4e7ec', autoScale: true }},
        timeScale: {{
          borderColor: '#e4e7ec',
          timeVisible: payload.isIntraday,
          secondsVisible: false,
          rightOffset: 0,
          barSpacing: 8,
          fixLeftEdge: false,
          fixRightEdge: true,
          rightBarStaysOnScroll: true,
          lockVisibleTimeRangeOnResize: true,
        }},
        crosshair: {{ mode: 0 }},
        handleScroll: {{ mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false }},
        handleScale: {{ mouseWheel: true, pinch: true, axisPressedMouseMove: {{ time: true, price: false }} }},
      }};
    }}

    const priceChart = LightweightCharts.createChart(document.getElementById('price-pane'), paneStyle(360));
    const charts = [priceChart];
    const candleSeries = priceChart.addCandlestickSeries({{
      upColor: '{RISE_COLOR}', downColor: '{FALL_COLOR}', borderVisible: false,
      wickUpColor: '{RISE_COLOR}', wickDownColor: '{FALL_COLOR}', priceLineVisible: false,
    }});
    candleSeries.setData(payload.candles);

    const overlaySeriesMap = {{}};
    const overlayColors = {{ MA5:'#f97316', MA20:'#0f766e', MA60:'#7c3aed', BB_UPPER:'#94a3b8', BB_MID:'#64748b', BB_LOWER:'#94a3b8' }};
    Object.entries(payload.overlays || {{}}).forEach(([name, data]) => {{
      const series = priceChart.addLineSeries({{ color: overlayColors[name] || '{LINE_COLOR}', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }});
      series.setData(data);
      overlaySeriesMap[name] = series;
    }});

    let volumeChart = null; let volumeSeries = null;
    if (payload.showVolume) {{
      document.getElementById('volume-wrap').style.display = 'block';
      volumeChart = LightweightCharts.createChart(document.getElementById('volume-pane'), paneStyle(120));
      charts.push(volumeChart);
      volumeSeries = volumeChart.addHistogramSeries({{ priceFormat: {{ type: 'volume' }}, priceLineVisible: false, lastValueVisible: false }});
      volumeSeries.setData(payload.volume);
    }}

    let rsiChart = null; let rsiSeries = null;
    if (payload.showRsi) {{
      document.getElementById('rsi-wrap').style.display = 'block';
      rsiChart = LightweightCharts.createChart(document.getElementById('rsi-pane'), paneStyle(120));
      charts.push(rsiChart);
      rsiSeries = rsiChart.addLineSeries({{ color: '#7c3aed', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }});
      rsiSeries.setData(payload.rsi);
      rsiSeries.createPriceLine({{ price: 70, color: '#d0d5dd', lineStyle: 2, lineWidth: 1, axisLabelVisible: false, title: '' }});
      rsiSeries.createPriceLine({{ price: 30, color: '#d0d5dd', lineStyle: 2, lineWidth: 1, axisLabelVisible: false, title: '' }});
    }}

    let macdChart = null; let macdSeries = null; let signalSeries = null;
    if (payload.showMacd) {{
      document.getElementById('macd-wrap').style.display = 'block';
      macdChart = LightweightCharts.createChart(document.getElementById('macd-pane'), paneStyle(120));
      charts.push(macdChart);
      macdSeries = macdChart.addLineSeries({{ color: '#0f766e', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }});
      macdSeries.setData(payload.macd);
      signalSeries = macdChart.addLineSeries({{ color: '#f97316', lineWidth: 2, priceLineVisible: false, lastValueVisible: false }});
      signalSeries.setData(payload.macdSignal);
      macdSeries.createPriceLine({{ price: 0, color: '#d0d5dd', lineStyle: 2, lineWidth: 1, axisLabelVisible: false, title: '' }});
    }}

    function buildTimeKey(value, explicitKey) {{
      if (explicitKey) return String(explicitKey);
      if (value === null || value === undefined) return '';
      if (typeof value === 'number') return String(value);
      if (typeof value === 'string') return value;
      if (typeof value === 'object' && value.year && value.month && value.day) {{
        return [value.year, String(value.month).padStart(2, '0'), String(value.day).padStart(2, '0')].join('-');
      }}
      return JSON.stringify(value);
    }}
    function buildTimeMap(rows) {{ const map = new Map(); (rows || []).forEach((row) => map.set(buildTimeKey(row.time, row.timeKey), row)); return map; }}
    const candleMap = buildTimeMap(payload.candles);
    const volumeMap = buildTimeMap(payload.volume);
    const overlayMaps = {{}}; Object.entries(payload.overlays || {{}}).forEach(([name, rows]) => {{ overlayMaps[name] = buildTimeMap(rows); }});
    const rsiMap = buildTimeMap(payload.rsi); const macdMap = buildTimeMap(payload.macd); const signalMap = buildTimeMap(payload.macdSignal);
    function hideTooltip(node) {{ if (node) node.style.display = 'none'; }}
    function hideAllTooltips() {{ hideTooltip(priceTooltip); hideTooltip(volumeTooltip); hideTooltip(rsiTooltip); hideTooltip(macdTooltip); }}
    function showTooltip(node, lines) {{ if (!node) return; node.innerHTML = lines.map((line) => '<div>' + line + '</div>').join(''); node.style.display = 'block'; }}
    function formatNumber(value, digits = 2) {{ if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'; return Number(value).toLocaleString('en-US', {{ minimumFractionDigits: digits, maximumFractionDigits: digits }}); }}
    function formatInteger(value) {{ if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'; return Number(value).toLocaleString('en-US', {{ maximumFractionDigits: 0 }}); }}
    function formatDateLabel(time) {{
      if (payload.isIntraday) {{
        const date = new Date(Number(time) * 1000);
        if (Number.isNaN(date.getTime())) return '';
        const yyyy = date.getFullYear(); const mm = String(date.getMonth()+1).padStart(2,'0'); const dd = String(date.getDate()).padStart(2,'0'); const hh = String(date.getHours()).padStart(2,'0'); const mi = String(date.getMinutes()).padStart(2,'0');
        return yyyy + '-' + mm + '-' + dd + ' ' + hh + ':' + mi;
      }}
      return buildTimeKey(time) || '';
    }}
    function renderAllTooltips(param) {{
      if (!param || !param.time || !param.point || param.point.x < 0 || param.point.y < 0) {{ hideAllTooltips(); return; }}
      const timeKey = buildTimeKey(param.time); const candle = candleMap.get(timeKey); if (!candle) {{ hideAllTooltips(); return; }}
      const priceLines = ['<div style="font-weight:700;margin-bottom:6px;">' + formatDateLabel(param.time) + '</div>', 'Open ' + formatInteger(candle.open) + ' | High ' + formatInteger(candle.high), 'Low ' + formatInteger(candle.low) + ' | Close ' + formatInteger(candle.close)];
      Object.entries(overlayMaps).forEach(([name, map]) => {{ const point = map.get(timeKey); if (point && point.value !== undefined) priceLines.push(name + ' ' + formatNumber(point.value)); }});
      showTooltip(priceTooltip, priceLines);
      const volumePoint = volumeMap.get(timeKey); if (volumePoint && volumePoint.value !== undefined) showTooltip(volumeTooltip, ['<div style="font-weight:700;margin-bottom:6px;">' + formatDateLabel(param.time) + '</div>', 'Volume ' + formatInteger(volumePoint.value)]); else hideTooltip(volumeTooltip);
      const rsiPoint = rsiMap.get(timeKey); if (rsiPoint && rsiPoint.value !== undefined) showTooltip(rsiTooltip, ['<div style="font-weight:700;margin-bottom:6px;">' + formatDateLabel(param.time) + '</div>', 'RSI14 ' + formatNumber(rsiPoint.value)]); else hideTooltip(rsiTooltip);
      const macdPoint = macdMap.get(timeKey); const signalPoint = signalMap.get(timeKey); if ((macdPoint && macdPoint.value !== undefined) || (signalPoint && signalPoint.value !== undefined)) {{ const macdLines = ['<div style="font-weight:700;margin-bottom:6px;">' + formatDateLabel(param.time) + '</div>']; if (macdPoint && macdPoint.value !== undefined) macdLines.push('MACD ' + formatNumber(macdPoint.value)); if (signalPoint && signalPoint.value !== undefined) macdLines.push('Signal ' + formatNumber(signalPoint.value)); showTooltip(macdTooltip, macdLines); }} else hideTooltip(macdTooltip);
    }}
    charts.forEach((chart) => chart.subscribeCrosshairMove(renderAllTooltips));

    function serializeTime(value) {{
      if (value === null || value === undefined) return '';
      if (typeof value === 'number') return String(value);
      if (typeof value === 'string') return value;
      if (typeof value === 'object' && value.year && value.month && value.day) {{
        return [value.year, String(value.month).padStart(2, '0'), String(value.day).padStart(2, '0')].join('-');
      }}
      return JSON.stringify(value);
    }}
    function rangeKey(range) {{ if (!range || !range.from || !range.to) return ''; return serializeTime(range.from) + ':' + serializeTime(range.to); }}
    function applyRange(range) {{ if (!range || !range.from || !range.to) return; syncing = true; lastRangeKey = rangeKey(range); charts.forEach((chart) => chart.timeScale().setVisibleRange(range)); syncing = false; }}
    priceChart.timeScale().subscribeVisibleTimeRangeChange((range) => {{
      if (syncing || !range || !range.from || !range.to) return;
      const key = rangeKey(range);
      if (!key || key === lastRangeKey) return;
      applyRange(range);
      if (syncChannel) syncChannel.postMessage({{ type: 'range', source: payload.chartId, range, key }});
    }});
    if (syncChannel) {{
      syncChannel.onmessage = (event) => {{
        const message = event.data || {{}};
        if (message.source === payload.chartId || message.type !== 'range' || !message.range) return;
        if (message.key && message.key === lastRangeKey) return;
        applyRange(message.range);
      }};
    }}
    const total = payload.candles.length; const visible = Math.max(1, payload.initialVisible || 100); const fromIndex = Math.max(0, total - visible); const toIndex = Math.max(total - 1, 0); applyRange({{ from: payload.candles[fromIndex].time, to: payload.candles[toIndex].time }});
    const resize = () => {{ const width = root.clientWidth || 820; charts.forEach((chart) => chart.applyOptions({{ width }})); }};
    new ResizeObserver(resize).observe(root); resize();
    </script>
    """
    html = html.replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False)).replace('{payload_title}', payload['title'])
    st.caption(
        f"Range: {date_min:%Y-%m-%d} to {date_max:%Y-%m-%d} | Initial view shows the most recent {min(len(source), INITIAL_VISIBLE_CANDLES)} candles. Horizontal zoom/pan is synchronized across panes" + (" and the paired benchmark chart." if sync_group else ".")
    )
    components.html(html, height=component_height, scrolling=False)

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


def _render_chart_panel(
    item: Dict[str, object],
    chart_options: Optional[Dict[str, object]] = None,
    chart_prefix: str = "chart",
    sync_group: Optional[str] = None,
) -> None:
    stock_code = str(item.get("code", ""))
    chart_label = str(item.get("name") or stock_code)
    lookback_days = SEARCH_LOOKBACK_DAYS
    with st.expander("Chart / Indicators", expanded=True):
        if chart_options is None:
            chart_pref_row = st.columns([1.2, 1.2, 1.4, 2.0])
            chart_mode = chart_pref_row[0].selectbox(
                "Timeframe",
                options=["minute", "daily", "weekly", "monthly"],
                index=1,
                format_func=lambda value: {"minute": "Minute", "daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}[value],
                key=f"chart_mode_{chart_prefix}_{stock_code}",
            )
            minute_interval = chart_pref_row[1].selectbox(
                "Minute",
                options=[1, 2, 3, 5, 10, 15, 30, 60],
                index=3,
                disabled=chart_mode != "minute",
                key=f"minute_interval_{chart_prefix}_{stock_code}",
            )
            full_history = chart_pref_row[2].checkbox(
                "Full History",
                value=True,
                disabled=chart_mode == "minute",
                key=f"full_history_{chart_prefix}_{stock_code}",
            )
            show_ma5 = st.checkbox("MA5", value=True, key=f"ma5_{chart_prefix}_{stock_code}")
            show_ma20 = st.checkbox("MA20", value=True, key=f"ma20_{chart_prefix}_{stock_code}")
            show_ma60 = st.checkbox("MA60", value=False, key=f"ma60_{chart_prefix}_{stock_code}")
            show_boll = st.checkbox("Bollinger", value=False, key=f"boll_{chart_prefix}_{stock_code}")
            show_volume = st.checkbox("Volume", value=True, key=f"volume_{chart_prefix}_{stock_code}")
            show_rsi = st.checkbox("RSI14", value=False, key=f"rsi_{chart_prefix}_{stock_code}")
            show_macd = st.checkbox("MACD", value=False, key=f"macd_{chart_prefix}_{stock_code}")
        else:
            chart_mode = str(chart_options.get("chart_mode", "daily"))
            minute_interval = int(chart_options.get("minute_interval", 5))
            full_history = bool(chart_options.get("full_history", True))
            show_ma5 = bool(chart_options.get("show_ma5", True))
            show_ma20 = bool(chart_options.get("show_ma20", True))
            show_ma60 = bool(chart_options.get("show_ma60", False))
            show_boll = bool(chart_options.get("show_boll", False))
            show_volume = bool(chart_options.get("show_volume", True))
            show_rsi = bool(chart_options.get("show_rsi", False))
            show_macd = bool(chart_options.get("show_macd", False))
            st.caption("Shared chart controls are applied to both panels.")

        if item.get("asset_type") == "index":
            history = _get_benchmark_chart_history(str(item.get("market", "")), lookback_days, chart_mode, full_history=bool(full_history))
        else:
            history = _get_chart_history(stock_code, lookback_days, chart_mode, int(minute_interval), full_history=bool(full_history))
        if history.empty:
            if chart_mode == "minute":
                st.warning("Minute data is unavailable. Current KIS authentication is failing with 403.")
            else:
                st.warning("No chart data was returned for this timeframe.")
            return

        chart = _build_indicator_frame(history)
        overlays: List[str] = []
        if show_ma5:
            overlays.append("MA5")
        if show_ma20:
            overlays.append("MA20")
        if show_ma60:
            overlays.append("MA60")
        if show_boll:
            overlays.extend(["BB_UPPER", "BB_MID", "BB_LOWER"])

        _render_candlestick_chart(
            chart,
            overlays,
            stock_code,
            chart_mode,
            show_volume=show_volume,
            show_rsi=show_rsi,
            show_macd=show_macd,
            full_history=bool(full_history),
            sync_group=sync_group,
            chart_key_prefix=chart_prefix,
            chart_label=chart_label,
        )


def _render_snapshot_card(
    item: Dict[str, object],
    chart_options: Optional[Dict[str, object]] = None,
    chart_prefix: str = "card",
    sync_group: Optional[str] = None,
) -> None:
    change_value = float(item.get("change", 0) or 0)
    tone_class = _tone_class(change_value)
    market_cap_eok = None
    if item.get("market_cap") is not None:
        try:
            market_cap_eok = float(item.get("market_cap")) / 100_000_000
        except Exception:
            market_cap_eok = None
    price_suffix = _item_price_suffix(item)

    st.markdown(
        f"""
        <div class="stock-card">
            <div class="stock-head">
                <div class="stock-name">{item.get('name', '-')} ({item.get('code', '-')})</div>
                <div class="chip">{item.get('market', 'UNKNOWN')}</div>
            </div>
            <div style="font-size:1.35rem;font-weight:700;">{_fmt_item_price(item, item.get('current_price'))}</div>
            <div class="{tone_class}" style="margin-top:0.2rem;font-size:1.02rem;font-weight:700;">{_fmt_signed_number(item.get('change'), suffix=price_suffix)} {_fmt_pct(item.get('change_rate'))}</div>
            <div class="muted" style="margin-top:0.35rem;">Volume {_fmt_number(item.get('volume'))} / Market Cap {_fmt_number(market_cap_eok)} EOK / As of {item.get('as_of', '-')}</div>
            <div class="detail-grid">
                <div class="detail-cell"><div class="detail-label">Prev Close</div><div class="detail-value">{_fmt_item_price(item, item.get('previous_close'))}</div></div>
                <div class="detail-cell"><div class="detail-label">Open</div><div class="detail-value" style="color:{_tone_color((item.get('open') or 0) - (item.get('previous_close') or 0))}">{_fmt_item_price(item, item.get('open'))}</div></div>
                <div class="detail-cell"><div class="detail-label">High</div><div class="detail-value rise">{_fmt_item_price(item, item.get('high'))}</div></div>
                <div class="detail-cell"><div class="detail-label">Low</div><div class="detail-value fall">{_fmt_item_price(item, item.get('low'))}</div></div>
                <div class="detail-cell"><div class="detail-label">Current</div><div class="detail-value {tone_class}">{_fmt_item_price(item, item.get('current_price'))}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stats_suffix = price_suffix
    market_stats_html = f"""
    <div class="panel-wrap">
        <div class="panel-title">Market Stats</div>
        <div class="panel-grid">
            <div class="panel-card"><div class="panel-label">52W High</div><div class="panel-value">{_fmt_number(item.get('high_52w'), digits=_item_price_digits(item), suffix=stats_suffix) if item.get('high_52w') is not None else '-'}</div></div>
            <div class="panel-card"><div class="panel-label">52W Low</div><div class="panel-value">{_fmt_number(item.get('low_52w'), digits=_item_price_digits(item), suffix=stats_suffix) if item.get('low_52w') is not None else '-'}</div></div>
            <div class="panel-card"><div class="panel-label">Trading Value</div><div class="panel-value">{_fmt_large_krw(item.get('trading_value'))}</div></div>
            <div class="panel-card"><div class="panel-label">Execution Strength</div><div class="panel-value">{_panel_pct(item.get('execution_strength'))}</div></div>
        </div>
    </div>
    """
    st.markdown(market_stats_html, unsafe_allow_html=True)

    fundamentals_html = f"""
    <div class="panel-wrap">
        <div class="panel-title">Fundamentals</div>
        <div class="panel-grid">
            <div class="panel-card"><div class="panel-label accent">PER</div><div class="panel-value">{_panel_decimal(item.get('per'))}</div></div>
            <div class="panel-card"><div class="panel-label accent">PBR</div><div class="panel-value">{_panel_decimal(item.get('pbr'))}</div></div>
            <div class="panel-card"><div class="panel-label accent">ROE</div><div class="panel-value">{_panel_pct(item.get('roe'))}</div></div>
            <div class="panel-card"><div class="panel-label accent">Dividend Yield</div><div class="panel-value">{_panel_pct(item.get('dividend_yield'))}</div></div>
            <div class="panel-card"><div class="panel-label accent">EPS</div><div class="panel-value">{_panel_decimal(item.get('eps'))}</div></div>
            <div class="panel-card"><div class="panel-label accent">BPS</div><div class="panel-value">{_panel_decimal(item.get('bps'))}</div></div>
            <div class="panel-card"><div class="panel-label accent">DPS</div><div class="panel-value">{_panel_decimal(item.get('dps'))}</div></div>
            <div class="panel-card"><div class="panel-label accent">Market Cap</div><div class="panel-value">{_fmt_large_krw(item.get('market_cap'))}</div></div>
        </div>
    </div>
    """
    st.markdown(fundamentals_html, unsafe_allow_html=True)

    moving_avg_metrics = pd.DataFrame([
        {
            "MA5": item.get("ma5"),
            "MA20": item.get("ma20"),
            "MA60": item.get("ma60"),
            "Avg Vol 20D": item.get("average_volume_20d"),
        }
    ])
    st.dataframe(moving_avg_metrics, width="stretch", hide_index=True)
    _render_chart_panel(item, chart_options=chart_options, chart_prefix=chart_prefix, sync_group=sync_group)
    recent = _normalize_recent_ohlcv(item.get("recent_ohlcv") or [])
    if not recent.empty:
        st.dataframe(recent, width="stretch", hide_index=True)


def _render_compare_controls(control_key: str) -> Dict[str, object]:
    st.markdown("### Shared Chart Controls")
    row1 = st.columns([1.1, 1.0, 1.1, 1.1])
    chart_mode = row1[0].selectbox(
        "Timeframe",
        options=["minute", "daily", "weekly", "monthly"],
        index=1,
        format_func=lambda value: {"minute": "Minute", "daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}[value],
        key=f"shared_chart_mode_{control_key}",
    )
    minute_interval = row1[1].selectbox(
        "Minute",
        options=[1, 2, 3, 5, 10, 15, 30, 60],
        index=3,
        disabled=chart_mode != "minute",
        key=f"shared_minute_interval_{control_key}",
    )
    full_history = row1[2].checkbox(
        "Full History",
        value=True,
        disabled=chart_mode == "minute",
        key=f"shared_full_history_{control_key}",
    )
    row1[3].caption("Both charts use the same timeframe and stay synchronized while panning or zooming.")

    row2 = st.columns(7)
    show_ma5 = row2[0].checkbox("MA5", value=True, key=f"shared_ma5_{control_key}")
    show_ma20 = row2[1].checkbox("MA20", value=True, key=f"shared_ma20_{control_key}")
    show_ma60 = row2[2].checkbox("MA60", value=False, key=f"shared_ma60_{control_key}")
    show_boll = row2[3].checkbox("Bollinger", value=False, key=f"shared_boll_{control_key}")
    show_volume = row2[4].checkbox("Volume", value=True, key=f"shared_volume_{control_key}")
    show_rsi = row2[5].checkbox("RSI14", value=False, key=f"shared_rsi_{control_key}")
    show_macd = row2[6].checkbox("MACD", value=False, key=f"shared_macd_{control_key}")

    return {
        "chart_mode": chart_mode,
        "minute_interval": int(minute_interval),
        "full_history": bool(full_history),
        "show_ma5": bool(show_ma5),
        "show_ma20": bool(show_ma20),
        "show_ma60": bool(show_ma60),
        "show_boll": bool(show_boll),
        "show_volume": bool(show_volume),
        "show_rsi": bool(show_rsi),
        "show_macd": bool(show_macd),
    }


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
    left, _ = st.columns([2.2, 1.8])
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
            report = system.build_search_report(
                final_keyword,
                limit=SEARCH_RESULT_LIMIT,
                lookback_days=SEARCH_LOOKBACK_DAYS,
                markets=selected_markets,
            )
        st.session_state["search_report"] = report
        st.session_state["last_report"] = report

    report = st.session_state.get("search_report")
    if not report:
        st.caption("Run a search to populate the comparison workspace.")
        return

    stocks = report.get("stocks", []) or []
    if not stocks:
        st.warning("No stock snapshots were returned.")
        return

    primary = stocks[0]
    if len(stocks) > 1:
        st.caption(f"Multiple matches were found. Showing the first result: {primary.get('name')} ({primary.get('code')}).")

    benchmark = system.get_market_benchmark_snapshot(str(primary.get("market", "")), lookback_days=SEARCH_LOOKBACK_DAYS)
    compare_controls = _render_compare_controls(str(primary.get("code", "stock")))
    sync_group = f"compare_{primary.get('code')}_{primary.get('market')}"

    left_col, right_col = st.columns(2, gap="large")
    with left_col:
        st.markdown("### Selected Stock")
        _render_snapshot_card(primary, chart_options=compare_controls, chart_prefix=f"stock_{primary.get('code')}", sync_group=sync_group)
    with right_col:
        st.markdown("### Market Benchmark")
        if benchmark:
            _render_snapshot_card(benchmark, chart_options=compare_controls, chart_prefix=f"benchmark_{benchmark.get('market')}", sync_group=sync_group)
        else:
            st.warning("Market benchmark data is not available for this market.")

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

    system = get_system()

    with st.sidebar:
        st.markdown("### Control Deck")
        st.caption("Run search and scan workflows from the browser.")
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
