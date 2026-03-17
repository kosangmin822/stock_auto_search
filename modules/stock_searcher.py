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
    ):
        logger.info("Fetching price history for %s (%s)", code, period)
        period = (period or "daily").lower()
        lookback_days = lookback_days or Config.DEFAULT_LOOKBACK_DAYS

        if period == "minute":
            kis_api = self._get_kis_api()
            if kis_api is None:
                return None
            return kis_api.get_intraday_ohlcv(code, interval=minute_interval)

        daily = self.pykrx.get_daily_ohlcv(
            code,
            start_date=None
            if lookback_days is None
            else self.pykrx._days_ago(lookback_days),
        )
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
        return self.pykrx.get_stock_snapshot(code, lookback_days=lookback_days)
