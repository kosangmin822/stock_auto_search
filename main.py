"""CLI entry point for stock search, extraction, and alert delivery."""

from __future__ import annotations

import argparse
import json
from typing import Optional

from config.config import Config
from modules.notifier import NotificationManager
from modules.order_manager import OrderManager
from modules.stock_reporter import StockReporter
from modules.stock_searcher import StockSearcher
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StockAutoSearch:
    """Application facade for non-trading and trading workflows."""

    def __init__(self):
        Config.validate_non_trading()
        self.stock_searcher = StockSearcher()
        self.reporter = StockReporter(self.stock_searcher)
        self.notifier = NotificationManager()
        self._order_manager: Optional[OrderManager] = None
        logger.info("StockAutoSearch initialized")

    def _get_order_manager(self) -> OrderManager:
        if self._order_manager is None:
            Config.validate_kis()
            self._order_manager = OrderManager()
        return self._order_manager

    def search_stock(
        self,
        keyword: str,
        limit: Optional[int] = None,
        markets: Optional[list[str]] = None,
    ):
        if keyword.isdigit() and len(keyword) == 6:
            result = self.stock_searcher.search_by_code(keyword, markets=markets)
            return [result] if result else []
        return self.stock_searcher.search_by_name(
            keyword,
            limit=limit or Config.DEFAULT_REPORT_LIMIT,
            markets=markets,
        )

    def get_price_history(
        self,
        stock_code: str,
        lookback_days: Optional[int] = None,
        period: str = "daily",
        minute_interval: int = 1,
    ):
        return self.stock_searcher.get_price_history(
            stock_code,
            period=period,
            lookback_days=lookback_days,
            minute_interval=minute_interval,
        )

    def get_ticker_master(self, markets: Optional[list[str]] = None):
        return self.stock_searcher.get_ticker_master(markets=markets)

    def get_top_gainers(self, limit: int = 10, market: Optional[str] = None, days: int = 1):
        return self.stock_searcher.get_top_gainers(limit=limit, market=market, days=days)

    def get_top_losers(self, limit: int = 10, market: Optional[str] = None, days: int = 1):
        return self.stock_searcher.get_top_losers(limit=limit, market=market, days=days)

    def build_search_report(
        self,
        keyword: str,
        limit: Optional[int] = None,
        lookback_days: Optional[int] = None,
        markets: Optional[list[str]] = None,
    ):
        return self.reporter.build_search_report(
            keyword,
            limit=limit,
            lookback_days=lookback_days,
            markets=markets,
        )

    def build_market_report(
        self,
        direction: str = "gainers",
        limit: Optional[int] = None,
        market: Optional[str] = None,
        days: int = 1,
    ):
        return self.reporter.build_market_report(
            direction=direction,
            limit=limit,
            market=market,
            days=days,
        )

    def save_report(self, report, prefix: Optional[str] = None) -> str:
        return self.reporter.save_report(report, prefix=prefix)

    def notify_report(self, report, title: Optional[str] = None):
        message = self.reporter.format_report_message(report)
        title = title or f"stock-auto-search:{report.get('type', 'report')}"
        return self.notifier.send(title, message)

    def buy_stock(self, stock_code, quantity, price=None):
        return self._get_order_manager().buy_stock(stock_code, quantity, price)

    def sell_stock(self, stock_code, quantity, price=None):
        return self._get_order_manager().sell_stock(stock_code, quantity, price)

    def get_account_info(self):
        return self._get_order_manager().kis_api.get_account_info()

    def get_balance(self):
        return self._get_order_manager().kis_api.get_balance()


def build_parser():
    parser = argparse.ArgumentParser(
        description="Search Korean stocks, extract report data, and send alerts.",
    )
    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser("search", help="Build a report for a keyword")
    search_parser.add_argument("keyword", help="Stock name or 6-digit ticker")
    search_parser.add_argument("--limit", type=int, default=Config.DEFAULT_REPORT_LIMIT)
    search_parser.add_argument(
        "--lookback-days",
        type=int,
        default=Config.DEFAULT_LOOKBACK_DAYS,
    )
    search_parser.add_argument("--notify", action="store_true")
    search_parser.add_argument("--save", action="store_true")

    movers_parser = subparsers.add_parser("movers", help="Build a market movers report")
    movers_parser.add_argument(
        "--direction",
        choices=["gainers", "losers"],
        default="gainers",
    )
    movers_parser.add_argument("--market", default=Config.DEFAULT_MARKET)
    movers_parser.add_argument("--limit", type=int, default=Config.DEFAULT_REPORT_LIMIT)
    movers_parser.add_argument("--days", type=int, default=1)
    movers_parser.add_argument("--notify", action="store_true")
    movers_parser.add_argument("--save", action="store_true")

    demo_parser = subparsers.add_parser("demo", help="Run a simple non-trading demo")
    demo_parser.add_argument("--keyword", default="삼성전자")
    demo_parser.add_argument("--notify", action="store_true")
    demo_parser.add_argument("--save", action="store_true")

    return parser


def run_search(system: StockAutoSearch, args):
    report = system.build_search_report(
        args.keyword,
        limit=args.limit,
        lookback_days=args.lookback_days,
    )
    print(system.reporter.format_report_message(report))
    if args.save:
        path = system.save_report(report, prefix="search_report")
        print(f"\nSaved report: {path}")
    if args.notify:
        results = system.notify_report(report, title=f"검색 리포트: {args.keyword}")
        print(f"\nNotification results: {json.dumps(results, ensure_ascii=False)}")


def run_movers(system: StockAutoSearch, args):
    report = system.build_market_report(
        direction=args.direction,
        limit=args.limit,
        market=args.market,
        days=args.days,
    )
    print(system.reporter.format_report_message(report))
    if args.save:
        path = system.save_report(report, prefix=f"{args.direction}_report")
        print(f"\nSaved report: {path}")
    if args.notify:
        title = f"시장 스캔: {args.market} {args.direction}"
        results = system.notify_report(report, title=title)
        print(f"\nNotification results: {json.dumps(results, ensure_ascii=False)}")


def run_demo(system: StockAutoSearch, args):
    report = system.build_search_report(args.keyword, limit=3)
    print(system.reporter.format_report_message(report))
    if args.save:
        path = system.save_report(report, prefix="demo_report")
        print(f"\nSaved report: {path}")
    if args.notify:
        results = system.notify_report(report, title=f"데모 리포트: {args.keyword}")
        print(f"\nNotification results: {json.dumps(results, ensure_ascii=False)}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    system = StockAutoSearch()

    if args.command == "search":
        run_search(system, args)
    elif args.command == "movers":
        run_movers(system, args)
    elif args.command == "demo":
        run_demo(system, args)


if __name__ == "__main__":
    main()
