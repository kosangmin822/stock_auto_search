"""Streamlit dashboard for stock search, market scans, and report delivery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
import streamlit as st

from config.config import Config
from main import StockAutoSearch


def _inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap');

        :root {
            --bg: #f4efe6;
            --paper: rgba(255, 250, 241, 0.82);
            --ink: #11211c;
            --muted: #54625d;
            --line: rgba(17, 33, 28, 0.08);
            --accent: #d65a31;
            --accent-soft: rgba(214, 90, 49, 0.12);
            --secondary: #1f6f78;
            --good: #0c7c59;
            --bad: #ba3b46;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(214, 90, 49, 0.18), transparent 24%),
                radial-gradient(circle at top right, rgba(31, 111, 120, 0.14), transparent 28%),
                linear-gradient(180deg, #f7f2ea 0%, var(--bg) 100%);
            color: var(--ink);
            font-family: 'Noto Sans KR', sans-serif;
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2.4rem;
            max-width: 1180px;
        }

        h1, h2, h3 {
            font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif;
            letter-spacing: -0.03em;
            color: var(--ink);
        }

        .hero {
            padding: 1.35rem 1.5rem 1.2rem;
            background: linear-gradient(135deg, rgba(255,250,241,0.94), rgba(255,244,229,0.88));
            border: 1px solid var(--line);
            border-radius: 26px;
            box-shadow: 0 14px 36px rgba(29, 33, 31, 0.08);
            margin-bottom: 1rem;
        }

        .hero-kicker {
            color: var(--accent);
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .hero-title {
            font-size: 2.1rem;
            font-weight: 700;
            line-height: 1.05;
            margin-bottom: 0.45rem;
        }

        .hero-copy {
            color: var(--muted);
            max-width: 760px;
            font-size: 0.98rem;
        }

        .panel {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1rem 1.1rem;
            box-shadow: 0 12px 30px rgba(17, 33, 28, 0.05);
        }

        .metric-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 1rem 0 0.8rem;
        }

        .metric-card {
            background: rgba(255,255,255,0.64);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.85rem 0.95rem;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .metric-value {
            margin-top: 0.35rem;
            font-size: 1.35rem;
            font-weight: 700;
            font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif;
        }

        .stock-card {
            background: rgba(255,255,255,0.78);
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1rem 1rem 0.5rem;
            margin-bottom: 0.85rem;
        }

        .stock-title {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            align-items: baseline;
            margin-bottom: 0.35rem;
        }

        .stock-name {
            font-size: 1.1rem;
            font-weight: 700;
            font-family: 'Space Grotesk', 'Noto Sans KR', sans-serif;
        }

        .stock-chip {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.24rem 0.55rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent);
        }

        .muted {
            color: var(--muted);
        }

        .good { color: var(--good); }
        .bad { color: var(--bad); }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.58);
            border-radius: 999px;
            border: 1px solid var(--line);
            padding: 0.5rem 0.9rem;
        }

        .stTabs [aria-selected="true"] {
            background: var(--ink);
            color: #fff;
        }

        .vault-item {
            padding: 0.7rem 0.8rem;
            border-radius: 14px;
            background: rgba(255,255,255,0.72);
            border: 1px solid var(--line);
            margin-bottom: 0.45rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_system() -> StockAutoSearch:
    return StockAutoSearch()


@st.cache_resource(show_spinner=False)
def get_system() -> StockAutoSearch:
    return _build_system()


def _fmt_number(value, digits: int = 0) -> str:
    if value is None:
        return "-"
    try:
        if digits == 0:
            return f"{int(round(float(value))):,}"
        return f"{float(value):,.{digits}f}"
    except Exception:
        return str(value)


def _fmt_pct(value) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):+.2f}%"
    except Exception:
        return str(value)


def _read_recent_reports(limit: int = 12) -> Iterable[Path]:
    report_dir = Path(Config.DATA_DIR) / "reports"
    if not report_dir.exists():
        return []
    return sorted(report_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def _load_report(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Stock Intelligence Console</div>
            <div class="hero-title">Search, scan, save, notify.</div>
            <div class="hero-copy">
                실거래는 제외하고 종목 검색, 시장 스캔, 리포트 저장, 알림 전송까지 한 화면에서 다루는 운영 대시보드입니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_overview(system: StockAutoSearch):
    reports = list(_read_recent_reports())
    webhook_enabled = "ON" if Config.ALERT_WEBHOOK_URL else "OFF"
    st.markdown(
        f"""
        <div class="metric-strip">
            <div class="metric-card">
                <div class="metric-label">Default Market</div>
                <div class="metric-value">{Config.DEFAULT_MARKET}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Lookback</div>
                <div class="metric-value">{Config.DEFAULT_LOOKBACK_DAYS}d</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Saved Reports</div>
                <div class="metric-value">{len(reports)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Webhook</div>
                <div class="metric-value">{webhook_enabled}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("런타임 정보", expanded=False):
        st.write(
            {
                "data_dir": Config.DATA_DIR,
                "alert_output_file": Config.ALERT_OUTPUT_FILE,
                "console_alert": Config.ALERT_CONSOLE_ENABLED,
                "webhook_enabled": bool(Config.ALERT_WEBHOOK_URL),
                "reports_available": len(reports),
            }
        )


def _render_snapshot_card(item: Dict[str, object]):
    change_rate = float(item.get("change_rate", 0))
    direction_class = "good" if change_rate >= 0 else "bad"
    st.markdown(
        f"""
        <div class="stock-card">
            <div class="stock-title">
                <div class="stock-name">{item.get('name', '-')} ({item.get('code', '-')})</div>
                <div class="stock-chip">{item.get('market', 'UNKNOWN')}</div>
            </div>
            <div class="{direction_class}" style="font-size:1.3rem;font-weight:700;">
                {_fmt_number(item.get('current_price'))}원 {_fmt_pct(item.get('change_rate'))}
            </div>
            <div class="muted" style="margin-top:0.35rem;">
                거래량 {_fmt_number(item.get('volume'))} / 시가총액 {_fmt_number((item.get('market_cap') or 0) / 100000000)}억원
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = pd.DataFrame(
        [
            {
                "Open": item.get("open"),
                "High": item.get("high"),
                "Low": item.get("low"),
                "MA5": item.get("ma5"),
                "MA20": item.get("ma20"),
                "MA60": item.get("ma60"),
                "PER": item.get("per"),
                "PBR": item.get("pbr"),
            }
        ]
    )
    st.dataframe(metrics, use_container_width=True, hide_index=True)

    recent_rows = item.get("recent_ohlcv") or []
    if recent_rows:
        recent_df = pd.DataFrame(recent_rows)
        if "날짜" in recent_df.columns and "종가" in recent_df.columns:
            close_chart = recent_df[["날짜", "종가"]].copy().set_index("날짜")
            st.line_chart(close_chart, use_container_width=True, height=220)
        st.dataframe(recent_df, use_container_width=True, hide_index=True)


def _render_search_tab(system: StockAutoSearch):
    st.subheader("Search Lab")
    with st.form("search_form", border=False):
        left, middle, right = st.columns([2.3, 1, 1])
        keyword = left.text_input("종목명 또는 6자리 종목코드", value="삼성전자")
        limit = middle.number_input("결과 수", min_value=1, max_value=20, value=3, step=1)
        lookback_days = right.number_input("조회 일수", min_value=30, max_value=730, value=365, step=10)
        action_col1, action_col2, action_col3 = st.columns(3)
        save_report = action_col1.checkbox("리포트 저장", value=True)
        notify = action_col2.checkbox("알림 전송", value=False)
        submit = action_col3.form_submit_button("검색 실행", use_container_width=True)

    if not submit:
        st.caption("키워드로 종목 스냅샷 리포트를 생성합니다.")
        return

    with st.spinner("리포트를 생성하는 중입니다..."):
        report = system.build_search_report(
            keyword=keyword.strip(),
            limit=int(limit),
            lookback_days=int(lookback_days),
        )

    st.session_state["last_report"] = report
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.write(
        {
            "keyword": report.get("keyword"),
            "generated_at": report.get("generated_at"),
            "matches": report.get("match_count"),
            "snapshots": report.get("snapshot_count"),
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)

    stocks = report.get("stocks", [])
    if not stocks:
        st.warning("데이터 수집 결과가 비어 있습니다. 네트워크 또는 외부 시세 접근 상태를 확인해야 합니다.")
    else:
        for item in stocks:
            _render_snapshot_card(item)

    _report_actions(system, report, save_report, notify, f"검색 리포트: {keyword}")


def _render_market_table(stocks: list[Dict[str, object]]):
    if not stocks:
        st.warning("시장 스캔 결과가 없습니다.")
        return

    frame = pd.DataFrame(stocks)
    rename_map = {
        "code": "종목코드",
        "name": "종목명",
        "market": "시장",
        "close": "종가",
        "change_rate": "등락률",
        "volume": "거래량",
        "trading_value": "거래대금",
        "market_cap": "시가총액",
        "per": "PER",
        "pbr": "PBR",
        "dividend_yield": "DIV",
    }
    frame = frame.rename(columns=rename_map)
    st.dataframe(frame, use_container_width=True, hide_index=True)


def _render_market_tab(system: StockAutoSearch):
    st.subheader("Market Radar")
    with st.form("market_form", border=False):
        col1, col2, col3, col4 = st.columns(4)
        direction = col1.selectbox("방향", ["gainers", "losers"], format_func=lambda x: "상승률 상위" if x == "gainers" else "하락률 상위")
        market = col2.selectbox("시장", ["ALL", "KOSPI", "KOSDAQ"])
        limit = col3.number_input("종목 수", min_value=3, max_value=30, value=10, step=1)
        days = col4.number_input("기간(일)", min_value=1, max_value=30, value=1, step=1)
        action_col1, action_col2, action_col3 = st.columns(3)
        save_report = action_col1.checkbox("리포트 저장", value=True, key="market_save")
        notify = action_col2.checkbox("알림 전송", value=False, key="market_notify")
        submit = action_col3.form_submit_button("시장 스캔", use_container_width=True)

    if not submit:
        st.caption("시장별 상승/하락 상위 종목을 요약합니다.")
        return

    with st.spinner("시장 데이터를 스캔하는 중입니다..."):
        report = system.build_market_report(
            direction=direction,
            limit=int(limit),
            market=market,
            days=int(days),
        )

    st.session_state["last_report"] = report
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.write(
        {
            "market": report.get("market"),
            "direction": report.get("direction"),
            "generated_at": report.get("generated_at"),
            "rows": report.get("count"),
        }
    )
    st.markdown("</div>", unsafe_allow_html=True)
    _render_market_table(report.get("stocks", []))
    _report_actions(system, report, save_report, notify, f"시장 스캔: {market} {direction}")


def _report_actions(
    system: StockAutoSearch,
    report: Dict[str, object],
    save_enabled: bool,
    notify_enabled: bool,
    title: str,
):
    action_row = st.columns([1, 1, 2.4])
    if save_enabled and action_row[0].button("지금 저장", use_container_width=True, key=f"save_{title}"):
        saved_path = system.save_report(report)
        st.success(f"리포트를 저장했습니다: {saved_path}")

    if notify_enabled and action_row[1].button("지금 알림", use_container_width=True, key=f"notify_{title}"):
        results = system.notify_report(report, title=title)
        st.success("알림 전송을 시도했습니다.")
        st.json(results)

    with action_row[2]:
        st.text_area(
            "알림 미리보기",
            value=system.reporter.format_report_message(report),
            height=220,
        )


def _render_report_vault():
    st.subheader("Report Vault")
    reports = list(_read_recent_reports())
    if not reports:
        st.info("저장된 리포트가 아직 없습니다.")
        return

    selected = st.selectbox(
        "리포트 선택",
        reports,
        format_func=lambda path: path.name,
    )
    for path in reports[:6]:
        st.markdown(
            f'<div class="vault-item"><strong>{path.name}</strong><br><span class="muted">{path}</span></div>',
            unsafe_allow_html=True,
        )

    report = _load_report(selected)
    st.json(report, expanded=False)


def _render_alert_center(system: StockAutoSearch):
    st.subheader("Alert Center")
    st.write(
        {
            "console": Config.ALERT_CONSOLE_ENABLED,
            "file": Config.ALERT_OUTPUT_FILE,
            "webhook_enabled": bool(Config.ALERT_WEBHOOK_URL),
        }
    )

    last_report = st.session_state.get("last_report")
    if last_report:
        st.caption("마지막으로 생성한 리포트를 다시 전송할 수 있습니다.")
        if st.button("마지막 리포트 재전송", use_container_width=True):
            results = system.notify_report(last_report)
            st.json(results)
    else:
        st.info("먼저 Search Lab 또는 Market Radar에서 리포트를 생성해야 합니다.")

    alert_file = Path(Config.ALERT_OUTPUT_FILE)
    if alert_file.exists():
        st.text_area(
            "최근 파일 알림 로그",
            value=alert_file.read_text(encoding="utf-8")[-4000:],
            height=260,
        )


def main():
    st.set_page_config(
        page_title="Stock Auto Search",
        page_icon="SA",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()
    _render_hero()

    system = get_system()

    with st.sidebar:
        st.markdown("### Control Deck")
        st.caption("기본 동작은 비거래 모드입니다.")
        st.write(
            {
                "market": Config.DEFAULT_MARKET,
                "lookback": Config.DEFAULT_LOOKBACK_DAYS,
                "report_limit": Config.DEFAULT_REPORT_LIMIT,
            }
        )
        st.markdown("---")
        st.caption("실행 명령")
        st.code("streamlit run ui/streamlit_app.py", language="bash")

    _render_overview(system)

    search_tab, market_tab, vault_tab, alert_tab = st.tabs(
        ["Search Lab", "Market Radar", "Report Vault", "Alert Center"]
    )

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
