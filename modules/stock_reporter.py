"""Build report payloads from stock search and market scan results."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from config.config import Config
from modules.stock_searcher import StockSearcher
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StockReporter:
    """Create, persist, and format non-trading stock reports."""

    def __init__(self, stock_searcher: Optional[StockSearcher] = None):
        self.stock_searcher = stock_searcher or StockSearcher()
        Config.ensure_runtime_dirs()

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def build_search_report(
        self,
        keyword: str,
        limit: Optional[int] = None,
        lookback_days: Optional[int] = None,
        markets: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """Build a report for a keyword or ticker search."""
        limit = limit or Config.DEFAULT_REPORT_LIMIT
        matches: List[Dict[str, object]]

        if keyword.isdigit() and len(keyword) == 6:
            stock = self.stock_searcher.search_by_code(keyword, markets=markets)
            matches = [stock] if stock else []
        else:
            matches = self.stock_searcher.search_by_name(
                keyword,
                limit=limit,
                markets=markets,
            )

        snapshots = []
        for match in matches[:limit]:
            try:
                snapshot = self.stock_searcher.get_stock_snapshot(
                    match["code"],
                    lookback_days=lookback_days,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to build snapshot for %s: %s",
                    match.get("code"),
                    exc,
                )
                snapshot = None

            if snapshot:
                snapshots.append(snapshot)

        report = {
            "type": "search",
            "keyword": keyword,
            "generated_at": self._now(),
            "requested_limit": limit,
            "markets": markets or ["KOSPI", "KOSDAQ"],
            "match_count": len(matches),
            "snapshot_count": len(snapshots),
            "stocks": snapshots,
        }
        logger.info(
            "Built search report for '%s' with %s snapshots",
            keyword,
            len(snapshots),
        )
        return report

    def build_market_report(
        self,
        direction: str = "gainers",
        limit: Optional[int] = None,
        market: Optional[str] = None,
        days: int = 1,
    ) -> Dict[str, object]:
        """Build a report for market movers."""
        limit = limit or Config.DEFAULT_REPORT_LIMIT
        if direction.lower() == "losers":
            movers = self.stock_searcher.get_top_losers(
                limit=limit,
                market=market,
                days=days,
            )
        else:
            movers = self.stock_searcher.get_top_gainers(
                limit=limit,
                market=market,
                days=days,
            )

        report = {
            "type": "market_scan",
            "direction": direction.lower(),
            "market": market or Config.DEFAULT_MARKET,
            "days": days,
            "generated_at": self._now(),
            "count": len(movers),
            "stocks": movers,
        }
        logger.info(
            "Built market report for %s with %s rows",
            direction,
            len(movers),
        )
        return report

    def save_report(self, report: Dict[str, object], prefix: Optional[str] = None) -> str:
        """Persist a report as JSON."""
        prefix = prefix or report.get("type", "report")
        file_name = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = os.path.join(Config.DATA_DIR, "reports", file_name)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        logger.info("Saved report to %s", output_path)
        return output_path

    def format_report_message(self, report: Dict[str, object]) -> str:
        """Create a plain-text summary suitable for alerts."""
        lines = []
        report_type = report.get("type")

        if report_type == "search":
            keyword = report.get("keyword")
            lines.append(f"[검색 리포트] {keyword}")
            lines.append(f"생성 시각: {report.get('generated_at')}")
            stocks = report.get("stocks", [])
            if not stocks:
                lines.append("수집 가능한 종목 데이터가 없습니다.")
                return "\n".join(lines)

            for index, item in enumerate(stocks, start=1):
                lines.append(
                    f"{index}. {item['name']}({item['code']}) "
                    f"{item['current_price']:,}원 "
                    f"{item['change_rate']:+.2f}% "
                    f"거래량 {item['volume']:,}"
                )
                if item.get("market_cap") is not None:
                    market_cap = int(item["market_cap"]) / 100_000_000
                    lines.append(
                        f"   시총 {market_cap:,.0f}억원 / PER {self._fmt_num(item.get('per'))} / PBR {self._fmt_num(item.get('pbr'))}"
                    )
                lines.append(
                    f"   MA5 {self._fmt_num(item.get('ma5'))} / MA20 {self._fmt_num(item.get('ma20'))} / 52주 {item['low_52w']:,}-{item['high_52w']:,}"
                )
        else:
            label = "상승률" if report.get("direction") != "losers" else "하락률"
            lines.append(
                f"[시장 스캔] {report.get('market')} {label} 상위 {report.get('count')}"
            )
            lines.append(f"생성 시각: {report.get('generated_at')}")
            stocks = report.get("stocks", [])
            if not stocks:
                lines.append("수집 가능한 시장 데이터가 없습니다.")
                return "\n".join(lines)

            for index, item in enumerate(stocks, start=1):
                close_value = item.get("close")
                close_text = f"{int(close_value):,}원" if close_value is not None else "-"
                lines.append(
                    f"{index}. {item['name']}({item['code']}) "
                    f"{close_text} {float(item['change_rate']):+.2f}% "
                    f"거래대금 {self._fmt_krw(item.get('trading_value'))}"
                )

        return "\n".join(lines)

    @staticmethod
    def _fmt_num(value) -> str:
        if value is None:
            return "-"
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return str(value)

    @staticmethod
    def _fmt_krw(value) -> str:
        if value is None:
            return "-"
        try:
            return f"{int(value):,}원"
        except Exception:
            return str(value)
