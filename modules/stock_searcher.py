"""Search-oriented service layer built on top of pykrx."""

from __future__ import annotations

from typing import Dict, List, Optional

from config.config import Config
from modules.kis_api import KISAPIWrapper
from modules.pykrx_wrapper import PyKRXWrapper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StockSearcher:
    """Expose stock search and extraction helpers."""

    def __init__(self):
        self.pykrx = PyKRXWrapper()
        self._kis_api: Optional[KISAPIWrapper] = None
        self._snapshot_cache: Dict[tuple[str, Optional[int]], Dict[str, object]] = {}
        logger.info("StockSearcher initialized")

    def _get_kis_api(self) -> Optional[KISAPIWrapper]:
        if self._kis_api is not None:
            return self._kis_api
        try:
            Config.validate_kis()
        except Exception as exc:
            logger.warning("KIS config unavailable for chart data: %s", exc)
            return None
        self._kis_api = KISAPIWrapper()
        return self._kis_api

    @staticmethod
    def _resample_ohlcv(frame, rule: str):
        if frame is None or frame.empty:
            return frame
        return (
            frame.resample(rule)
            .agg(
                {
                    "시가": "first",
                    "고가": "max",
                    "저가": "min",
                    "종가": "last",
                    "거래량": "sum",
                }
            )
            .dropna(subset=["시가", "고가", "저가", "종가"])
        )

    def search_by_name(
        self,
        keyword: str,
        limit: int = 20,
        markets: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        logger.info("Searching stocks by name: %s", keyword)
        return self.pykrx.search_stock_by_name(keyword, limit=limit, markets=markets)

    def search_by_code(
        self,
        code: str,
        markets: Optional[List[str]] = None,
    ) -> Optional[Dict[str, str]]:
        logger.info("Searching stock by code: %s", code)
        stock = self.pykrx.get_stock_info(code)
        if not stock or not markets:
            return stock
        allowed = {market.upper() for market in markets}
        return stock if str(stock.get("market", "")).upper() in allowed else None

    def get_ticker_master(self, markets: Optional[List[str]] = None) -> List[Dict[str, str]]:
        logger.info("Loading ticker master for autocomplete")
        return self.pykrx.get_ticker_master(markets=markets)

    def get_market_benchmark_snapshot(
        self,
        market: str,
        lookback_days: Optional[int] = None,
    ) -> Optional[Dict[str, object]]:
        logger.info("Building market benchmark snapshot for %s", market)
        return self.pykrx.get_market_index_snapshot(market, lookback_days=lookback_days)

    def get_market_benchmark_history(
        self,
        market: str,
        lookback_days: Optional[int] = None,
        full_history: bool = False,
    ):
        logger.info("Fetching market benchmark history for %s", market)
        start_date = "19800104" if full_history else self.pykrx._days_ago(lookback_days or Config.DEFAULT_LOOKBACK_DAYS)
        return self.pykrx.get_market_index_ohlcv(market, start_date=start_date)

    def get_top_gainers(
        self,
        limit: int = 10,
        market: Optional[str] = None,
        days: int = 1,
    ) -> List[Dict[str, object]]:
        logger.info("Fetching top %s gainers", limit)
        return self.pykrx.get_market_movers(
            direction="gainers",
            market=market or Config.DEFAULT_MARKET,
            limit=limit,
            days=days,
        )

    def get_top_losers(
        self,
        limit: int = 10,
        market: Optional[str] = None,
        days: int = 1,
    ) -> List[Dict[str, object]]:
        logger.info("Fetching top %s losers", limit)
        return self.pykrx.get_market_movers(
            direction="losers",
            market=market or Config.DEFAULT_MARKET,
            limit=limit,
            days=days,
        )

    def get_price_history(
        self,
        code: str,
        period: str = "daily",
        lookback_days: Optional[int] = None,
        minute_interval: int = 1,
        full_history: bool = False,
    ):
        logger.info("Fetching price history for %s (%s)", code, period)
        period = (period or "daily").lower()

        if period == "minute":
            kis_api = self._get_kis_api()
            if kis_api is None:
                return None
            return kis_api.get_intraday_ohlcv(code, interval=minute_interval)

        start_date = "19800104" if full_history else self.pykrx._days_ago(lookback_days or Config.DEFAULT_LOOKBACK_DAYS)
        daily = self.pykrx.get_daily_ohlcv(code, start_date=start_date)
        if daily is None or daily.empty:
            return None
        if period == "weekly":
            return self._resample_ohlcv(daily, "W")
        if period == "monthly":
            return self._resample_ohlcv(daily, "ME")
        if period != "daily":
            logger.warning("Unsupported period requested: %s", period)
            return None
        return daily

    def get_stock_snapshot(
        self,
        code: str,
        lookback_days: Optional[int] = None,
    ) -> Optional[Dict[str, object]]:
        logger.info("Building stock snapshot for %s", code)
        cache_key = (str(code).zfill(6), lookback_days)
        cached = self._snapshot_cache.get(cache_key)
        if cached is not None:
            return dict(cached)

        snapshot = self.pykrx.get_stock_snapshot(code, lookback_days=lookback_days)
        if not snapshot:
            return None

        kis_api = self._get_kis_api()
        if kis_api is None:
            self._snapshot_cache[cache_key] = dict(snapshot)
            return dict(snapshot)

        try:
            quote = kis_api.get_current_quote(code)
        except Exception as exc:
            logger.warning("Failed to enrich snapshot with KIS quote for %s: %s", code, exc)
            quote = None

        if quote:
            for key, value in quote.items():
                if value is not None:
                    snapshot[key] = value
        self._snapshot_cache[cache_key] = dict(snapshot)
        return dict(snapshot)
