"""Utilities for stock search and market data extraction via pykrx."""

from __future__ import annotations

from datetime import datetime, timedelta
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests
from pykrx import stock

from config.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)

POPULAR_STOCKS = {
    "005930": "삼성전자",
    "005380": "현대차",
    "000660": "SK하이닉스",
    "068270": "셀트리온",
    "035720": "카카오",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "207940": "삼성바이오로직스",
    "035420": "NAVER",
    "028300": "HLB",
    "000100": "유한양행",
}

POPULAR_STOCK_MARKETS = {
    "005930": "KOSPI",
    "005380": "KOSPI",
    "000660": "KOSPI",
    "068270": "KOSPI",
    "035720": "KOSPI",
    "051910": "KOSPI",
    "006400": "KOSPI",
    "207940": "KOSPI",
    "035420": "KOSPI",
    "028300": "KOSDAQ",
    "000100": "KOSPI",
}

POPULAR_STOCK_ALIASES = {
    "현대차": "005380",
    "현대자동차": "005380",
    "삼성전자": "005930",
    "sk하이닉스": "000660",
}

MARKETS = ("KOSPI", "KOSDAQ", "KONEX")
KIND_MARKET_TYPES = {
    "KOSPI": "stockMkt",
    "KOSDAQ": "kosdaqMkt",
    "KONEX": "konexMkt",
}
OHLCV_COLUMNS = ("시가", "고가", "저가", "종가", "거래량")
MARKET_OHLCV_COLUMNS = ("시가", "고가", "저가", "종가", "거래량", "거래대금", "등락률")
MARKET_CAP_COLUMNS = ("종가", "시가총액", "거래량", "거래대금", "상장주식수")
FUNDAMENTAL_COLUMNS = ("BPS", "PER", "PBR", "EPS", "DIV", "DPS")
SECTOR_COLUMNS = ("종목명", "업종명", "종가", "대비", "등락률", "시가총액")


class PyKRXWrapper:
    """Thin wrapper around pykrx with defensive fallbacks."""

    def __init__(self):
        self._ticker_cache: Optional[pd.DataFrame] = None
        logger.info("PyKRX wrapper initialized")

    @staticmethod
    def _ticker_cache_path() -> Path:
        return Path(Config.DATA_DIR) / "cache" / "ticker_master.csv"

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y%m%d")

    @staticmethod
    def _shift_days(base_date: str, days: int) -> str:
        base = datetime.strptime(base_date, "%Y%m%d")
        return (base - timedelta(days=days)).strftime("%Y%m%d")

    def _candidate_dates(self, days_back: int = 14) -> List[str]:
        """Generate recent weekday candidates without relying on KRX date helpers."""
        today = datetime.now()
        dates = []
        for offset in range(days_back + 1):
            value = today - timedelta(days=offset)
            if value.weekday() < 5:
                dates.append(value.strftime("%Y%m%d"))
        return dates

    def _reference_date(self) -> str:
        return self._candidate_dates(7)[0]

    def _days_ago(self, days: int) -> str:
        return self._shift_days(self._reference_date(), days)

    @staticmethod
    def _search_popular(keyword: str) -> List[Dict[str, str]]:
        lowered = keyword.lower()
        alias_code = POPULAR_STOCK_ALIASES.get(lowered) or POPULAR_STOCK_ALIASES.get(keyword)
        if alias_code and alias_code in POPULAR_STOCKS:
            return [
                {
                    "code": alias_code,
                    "name": POPULAR_STOCKS[alias_code],
                    "market": POPULAR_STOCK_MARKETS.get(alias_code, "UNKNOWN"),
                }
            ]

        results = []
        for code, name in POPULAR_STOCKS.items():
            if lowered in name.lower() or keyword in code:
                results.append(
                    {
                        "code": code,
                        "name": name,
                        "market": POPULAR_STOCK_MARKETS.get(code, "UNKNOWN"),
                    }
                )
        return results

    @staticmethod
    def _to_native(value):
        if value is None or pd.isna(value):
            return None
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                return value
        return value

    @staticmethod
    def _empty_frame(columns: Iterable[str]) -> pd.DataFrame:
        return pd.DataFrame(columns=list(columns))

    @staticmethod
    def _ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
        for column in columns:
            if column not in df.columns:
                df[column] = None
        return df

    @staticmethod
    def _normalize_code_frame(df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """Normalize pykrx outputs to a dataframe with a `code` column."""
        if df is None or df.empty:
            return pd.DataFrame(columns=["code"])

        normalized = df.copy()
        if "code" in normalized.columns:
            normalized["code"] = normalized["code"].astype(str).str.zfill(6)
            return normalized

        normalized = normalized.reset_index()
        for column in ("티커", "종목코드", "code", "index"):
            if column in normalized.columns:
                normalized = normalized.rename(columns={column: "code"})
                normalized["code"] = normalized["code"].astype(str).str.zfill(6)
                return normalized

        if len(normalized.columns) > 0:
            first_column = normalized.columns[0]
            values = normalized[first_column].astype(str)
            if values.str.fullmatch(r"\d{6}").any():
                normalized = normalized.rename(columns={first_column: "code"})
                normalized["code"] = normalized["code"].astype(str).str.zfill(6)
                return normalized

        return pd.DataFrame(columns=["code"])

    def _load_cached_ticker_master(self) -> pd.DataFrame:
        path = self._ticker_cache_path()
        if not path.exists():
            return self._empty_frame(["code", "name", "market"])

        try:
            cached = pd.read_csv(path, dtype={"code": str})
        except Exception as exc:
            logger.warning("Failed to read cached ticker master: %s", exc)
            return self._empty_frame(["code", "name", "market"])

        if cached.empty:
            return self._empty_frame(["code", "name", "market"])

        cached = self._ensure_columns(cached, ("code", "name", "market"))
        cached["code"] = cached["code"].astype(str).str.extract(r"(\d+)")[0].str.zfill(6)
        cached = cached.dropna(subset=["code", "name"]).drop_duplicates(subset=["code"])
        logger.info("Loaded %s tickers from local cache", len(cached))
        return cached[["code", "name", "market"]]

    def _save_cached_ticker_master(self, df: pd.DataFrame) -> None:
        if df.empty:
            return

        path = self._ticker_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df[["code", "name", "market"]].drop_duplicates(subset=["code"]).to_csv(
                path,
                index=False,
                encoding="utf-8-sig",
            )
            logger.info("Saved %s tickers to local cache", len(df))
        except Exception as exc:
            logger.warning("Failed to save ticker master cache: %s", exc)

    @staticmethod
    def _extract_named_columns(df: pd.DataFrame, code_hint: str, name_hint: str) -> pd.DataFrame:
        code_col = next((col for col in df.columns if code_hint in str(col)), None)
        name_col = next((col for col in df.columns if name_hint in str(col)), None)
        if code_col is None or name_col is None:
            return pd.DataFrame(columns=["code", "name"])

        normalized = pd.DataFrame(
            {
                "code": df[code_col].astype(str).str.extract(r"(\d+)")[0].str.zfill(6),
                "name": df[name_col].astype(str).str.strip(),
            }
        )
        return normalized.dropna(subset=["code", "name"])

    @staticmethod
    def _extract_kind_table_html(html: str) -> pd.DataFrame:
        class KindTableParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_table = False
                self.in_row = False
                self.in_cell = False
                self.current_row: List[str] = []
                self.current_cell: List[str] = []
                self.rows: List[List[str]] = []

            def handle_starttag(self, tag, attrs):
                if tag == "table" and not self.in_table:
                    self.in_table = True
                    return
                if not self.in_table:
                    return
                if tag == "tr":
                    self.in_row = True
                    self.current_row = []
                elif tag in {"td", "th"} and self.in_row:
                    self.in_cell = True
                    self.current_cell = []

            def handle_data(self, data):
                if self.in_table and self.in_cell:
                    self.current_cell.append(data)

            def handle_endtag(self, tag):
                if not self.in_table:
                    return
                if tag in {"td", "th"} and self.in_cell:
                    self.in_cell = False
                    cell_text = "".join(self.current_cell).strip()
                    self.current_row.append(cell_text)
                elif tag == "tr" and self.in_row:
                    self.in_row = False
                    if any(cell.strip() for cell in self.current_row):
                        self.rows.append(self.current_row)
                elif tag == "table":
                    self.in_table = False

        parser = KindTableParser()
        parser.feed(html)

        if len(parser.rows) < 2:
            return pd.DataFrame()

        header = parser.rows[0]
        body = [row[: len(header)] for row in parser.rows[1:] if len(row) >= 2]
        if not body:
            return pd.DataFrame()

        return pd.DataFrame(body, columns=header)

    def _fetch_kind_ticker_master(self) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []
        url = "https://kind.krx.co.kr/corpgeneral/corpList.do"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        }

        for market, market_type in KIND_MARKET_TYPES.items():
            try:
                response = requests.get(
                    url,
                    params={
                        "method": "download",
                        "searchType": "13",
                        "marketType": market_type,
                    },
                    headers=headers,
                    timeout=12,
                )
                response.raise_for_status()
                try:
                    tables = pd.read_html(StringIO(response.text))
                    source_table = tables[0] if tables else pd.DataFrame()
                except Exception as exc:
                    logger.info("Falling back to built-in KIND HTML parser for %s: %s", market, exc)
                    source_table = self._extract_kind_table_html(response.text)

                if source_table.empty:
                    logger.warning("KIND returned no tables for %s", market)
                    continue

                frame = self._extract_named_columns(source_table, "종목코드", "회사명")
                if frame.empty:
                    logger.warning("KIND ticker master columns missing for %s", market)
                    continue

                frame["market"] = market
                frames.append(frame)
                logger.info("Loaded %s tickers from KIND %s", len(frame), market)
            except Exception as exc:
                logger.warning("Failed to load KIND ticker master for %s: %s", market, exc)

        if not frames:
            return self._empty_frame(["code", "name", "market"])

        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["code"])

    def _first_valid_table(
        self,
        fetcher,
        expected_columns: Iterable[str],
        candidate_dates: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        candidate_dates = candidate_dates or self._candidate_dates(14)
        for query_date in candidate_dates:
            try:
                table = fetcher(query_date)
            except Exception as exc:
                logger.debug("Failed to fetch table for %s: %s", query_date, exc)
                continue

            normalized = self._normalize_code_frame(table)
            if normalized.empty:
                continue

            normalized = self._ensure_columns(normalized, expected_columns)
            return normalized

        return self._empty_frame(["code", *expected_columns])

    def _get_ticker_cache(self) -> pd.DataFrame:
        if self._ticker_cache is not None:
            return self._ticker_cache

        rows: List[Dict[str, str]] = []
        for market in MARKETS:
            try:
                tickers = stock.get_market_ticker_list(market=market)
            except Exception as exc:
                logger.warning("Failed to load %s ticker list: %s", market, exc)
                tickers = []

            for code in tickers:
                try:
                    name = stock.get_market_ticker_name(code)
                except Exception:
                    name = POPULAR_STOCKS.get(code, code)
                rows.append({"code": code, "name": name, "market": market})

        if not rows:
            kind_master = self._fetch_kind_ticker_master()
            if not kind_master.empty:
                rows = kind_master.to_dict("records")

        if not rows:
            for market in ("KOSPI", "KOSDAQ"):
                sector_frame = self._first_valid_table(
                    fetcher=lambda date, market=market: stock.get_market_sector_classifications(
                        date=date,
                        market=market,
                    ),
                    expected_columns=SECTOR_COLUMNS,
                )
                if sector_frame.empty or "종목명" not in sector_frame.columns:
                    continue
                rows.extend(
                    {
                        "code": row["code"],
                        "name": row["종목명"],
                        "market": market,
                    }
                    for row in sector_frame.to_dict("records")
                )

        if rows:
            self._ticker_cache = pd.DataFrame(rows).drop_duplicates(subset=["code"])
            self._save_cached_ticker_master(self._ticker_cache)
            return self._ticker_cache

        cached = self._load_cached_ticker_master()
        if not cached.empty:
            self._ticker_cache = cached
            return self._ticker_cache

        rows = [
            {
                "code": code,
                "name": name,
                "market": POPULAR_STOCK_MARKETS.get(code, "UNKNOWN"),
            }
            for code, name in POPULAR_STOCKS.items()
        ]
        self._ticker_cache = pd.DataFrame(rows).drop_duplicates(subset=["code"])
        return self._ticker_cache

    def _market_dates(self, days: int = 1) -> tuple[str, str]:
        end_candidates = self._candidate_dates(14)
        end_date = end_candidates[0]
        start_anchor = self._shift_days(end_date, max(days, 1) + 7)
        start_candidates = [
            self._shift_days(start_anchor, offset)
            for offset in range(0, 10)
            if datetime.strptime(self._shift_days(start_anchor, offset), "%Y%m%d").weekday() < 5
        ]
        return end_date, start_candidates[0] if start_candidates else self._shift_days(end_date, max(days, 1) + 7)

    def get_stock_list(self, market: str = "ALL") -> List[str]:
        """Return ticker list for a market."""
        if market == "ALL":
            return self._get_ticker_cache()["code"].tolist()

        try:
            return stock.get_market_ticker_list(market=market)
        except Exception as exc:
            logger.error("Failed to fetch stock list for %s: %s", market, exc)
            cache = self._get_ticker_cache()
            return cache.loc[cache["market"] == market, "code"].tolist()

    def get_ticker_master(self, markets: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Return cached ticker metadata for UI autocomplete and search."""
        cache = self._get_ticker_cache().copy()
        if cache.empty:
            return []

        cache = self._ensure_columns(cache, ("code", "name", "market"))
        cache["code"] = cache["code"].astype(str).str.zfill(6)
        cache["name"] = cache["name"].astype(str)
        cache["market"] = cache["market"].fillna("UNKNOWN").astype(str)
        if markets:
            allowed = {market.upper() for market in markets}
            cache = cache.loc[cache["market"].str.upper().isin(allowed)]
        cache = cache.sort_values(by=["market", "name", "code"], ascending=[True, True, True])
        return cache[["code", "name", "market"]].to_dict("records")

    def detect_market(self, stock_code: str) -> str:
        """Best-effort market lookup for a ticker."""
        cache = self._get_ticker_cache()
        matched = cache.loc[cache["code"] == stock_code]
        if not matched.empty:
            return str(matched.iloc[0]["market"])
        return "UNKNOWN"

    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, str]]:
        """Return basic ticker metadata."""
        stock_code = str(stock_code).zfill(6)

        if stock_code in POPULAR_STOCKS:
            return {
                "code": stock_code,
                "name": POPULAR_STOCKS[stock_code],
                "market": POPULAR_STOCK_MARKETS.get(stock_code, "UNKNOWN"),
            }

        cache = self._get_ticker_cache()
        matched = cache.loc[cache["code"] == stock_code]
        if not matched.empty:
            row = matched.iloc[0]
            return {
                "code": row["code"],
                "name": row["name"],
                "market": row["market"],
            }

        try:
            return {
                "code": stock_code,
                "name": stock.get_market_ticker_name(stock_code),
                "market": self.detect_market(stock_code),
            }
        except Exception as exc:
            logger.warning("Stock info not found for %s: %s", stock_code, exc)
            return None

    def get_daily_ohlcv(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Return daily OHLCV data for a ticker."""
        end_date = end_date or self._reference_date()
        start_date = start_date or self._shift_days(end_date, Config.DEFAULT_LOOKBACK_DAYS)

        try:
            df = stock.get_market_ohlcv_by_date(
                fromdate=start_date,
                todate=end_date,
                ticker=str(stock_code).zfill(6),
            )
        except Exception as exc:
            logger.error("Failed to fetch OHLCV for %s: %s", stock_code, exc)
            return None

        if df is None or df.empty:
            return None
        if not all(column in df.columns for column in OHLCV_COLUMNS):
            logger.warning("Unexpected OHLCV columns for %s: %s", stock_code, list(df.columns))
            return None
        return df

    def get_current_price(self, stock_code: str) -> Optional[int]:
        """Return the latest close price available."""
        ohlcv = self.get_daily_ohlcv(stock_code, start_date=self._days_ago(14))
        if ohlcv is None or ohlcv.empty:
            return None
        return int(self._to_native(ohlcv.iloc[-1]["종가"]))

    def search_stock_by_name(
        self,
        keyword: str,
        limit: int = 20,
        markets: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Search tickers by name or code."""
        keyword = (keyword or "").strip()
        if not keyword:
            return []

        allowed = {market.upper() for market in markets} if markets else None

        popular_matches = self._search_popular(keyword)
        if allowed:
            popular_matches = [
                item for item in popular_matches if str(item.get("market", "")).upper() in allowed
            ]
        if popular_matches:
            return popular_matches[:limit]

        cache = self._get_ticker_cache()
        if allowed:
            cache = cache.loc[cache["market"].astype(str).str.upper().isin(allowed)].copy()
        lowered = keyword.lower()
        filtered = cache[
            cache["name"].str.lower().str.contains(lowered, na=False, regex=False)
            | cache["code"].str.contains(keyword, na=False, regex=False)
        ].copy()

        if filtered.empty:
            return []

        filtered["exact_name"] = filtered["name"].str.lower().eq(lowered)
        filtered["exact_code"] = filtered["code"].eq(keyword)
        filtered = filtered.sort_values(
            by=["exact_code", "exact_name", "market", "code"],
            ascending=[False, False, True, True],
        )

        return (
            filtered[["code", "name", "market"]]
            .drop_duplicates(subset=["code"])
            .head(limit)
            .to_dict("records")
        )

    def get_market_cap_snapshot(
        self,
        date: Optional[str] = None,
        market: str = "ALL",
    ) -> pd.DataFrame:
        """Return market cap table for a date."""
        if market == "ALL":
            frames = []
            for item_market in ("KOSPI", "KOSDAQ", "KONEX"):
                frame = self.get_market_cap_snapshot(date=date, market=item_market)
                if not frame.empty:
                    frames.append(frame)
            if not frames:
                return self._empty_frame(["code", *MARKET_CAP_COLUMNS, "market"])
            return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["code"])

        table = self._first_valid_table(
            fetcher=lambda query_date: stock.get_market_cap_by_ticker(
                date=query_date,
                market=market,
                alternative=False,
            ),
            expected_columns=MARKET_CAP_COLUMNS,
        )
        if not table.empty:
            table["market"] = market
        return table

    def get_fundamental_snapshot(
        self,
        date: Optional[str] = None,
        market: str = "ALL",
    ) -> pd.DataFrame:
        """Return market fundamentals table for a date."""
        if market == "ALL":
            frames = []
            for item_market in ("KOSPI", "KOSDAQ"):
                frame = self.get_fundamental_snapshot(date=date, market=item_market)
                if not frame.empty:
                    frames.append(frame)
            if not frames:
                return self._empty_frame(["code", *FUNDAMENTAL_COLUMNS, "market"])
            return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["code"])

        table = self._first_valid_table(
            fetcher=lambda query_date: stock.get_market_fundamental_by_ticker(
                date=query_date,
                market=market,
                alternative=False,
            ),
            expected_columns=FUNDAMENTAL_COLUMNS,
        )
        if not table.empty:
            table["market"] = market
        return table

    def _market_ohlcv_snapshot(self, market: str, query_date: str) -> pd.DataFrame:
        try:
            table = stock.get_market_ohlcv_by_ticker(
                date=query_date,
                market=market,
                alternative=False,
            )
        except Exception as exc:
            logger.debug("Failed market OHLCV for %s on %s: %s", market, query_date, exc)
            return self._empty_frame(["code", *MARKET_OHLCV_COLUMNS])

        normalized = self._normalize_code_frame(table)
        if normalized.empty:
            return normalized

        normalized = self._ensure_columns(normalized, MARKET_OHLCV_COLUMNS)
        normalized["market"] = market
        return normalized

    def get_market_movers(
        self,
        direction: str = "gainers",
        market: str = "ALL",
        limit: int = 10,
        days: int = 1,
    ) -> List[Dict[str, object]]:
        """Return top gainers or losers across a market."""
        target_markets = ("KOSPI", "KOSDAQ", "KONEX") if market == "ALL" else (market,)
        end_date = self._reference_date()
        start_date = self._shift_days(end_date, max(days, 1) + 7)

        frames = []
        for item_market in target_markets:
            current = self._first_valid_table(
                fetcher=lambda query_date, market=item_market: self._market_ohlcv_snapshot(
                    market,
                    query_date,
                ),
                expected_columns=MARKET_OHLCV_COLUMNS,
                candidate_dates=self._candidate_dates(10),
            )
            previous = self._first_valid_table(
                fetcher=lambda query_date, market=item_market: self._market_ohlcv_snapshot(
                    market,
                    query_date,
                ),
                expected_columns=MARKET_OHLCV_COLUMNS,
                candidate_dates=[
                    self._shift_days(start_date, offset)
                    for offset in range(0, 10)
                    if datetime.strptime(self._shift_days(start_date, offset), "%Y%m%d").weekday() < 5
                ],
            )

            if current.empty or previous.empty:
                continue

            merged = current.merge(
                previous[["code", "종가"]],
                on="code",
                how="left",
                suffixes=("", "_prev"),
            )
            merged = merged.rename(columns={"종가_prev": "기준종가"})
            merged = merged.dropna(subset=["기준종가"])
            if merged.empty:
                continue

            merged["변동폭"] = merged["종가"] - merged["기준종가"]
            merged["등락률"] = (
                merged["변동폭"] / merged["기준종가"] * 100
            ).replace([pd.NA, pd.NaT, float("inf"), float("-inf")], 0)
            merged["market"] = item_market
            frames.append(merged)

        if not frames:
            return []

        frame = pd.concat(frames, ignore_index=True)
        cache = self._get_ticker_cache().set_index("code")
        frame["name"] = frame["code"].map(cache["name"]).fillna(frame["code"])
        frame["market"] = frame["code"].map(cache["market"]).fillna(frame["market"])

        market_caps = self.get_market_cap_snapshot(market=market)
        if not market_caps.empty and "시가총액" in market_caps.columns:
            frame = frame.merge(
                market_caps[["code", "시가총액"]],
                on="code",
                how="left",
            )

        fundamentals = self.get_fundamental_snapshot(market=market)
        if not fundamentals.empty:
            available_columns = [
                column
                for column in ["code", "PER", "PBR", "DIV"]
                if column in fundamentals.columns
            ]
            if len(available_columns) > 1:
                frame = frame.merge(
                    fundamentals[available_columns],
                    on="code",
                    how="left",
                )

        ascending = direction.lower() == "losers"
        frame = frame.sort_values(
            by=["등락률", "거래대금"],
            ascending=[ascending, False],
        )

        results = []
        for row in frame.head(limit).to_dict("records"):
            results.append(
                {
                    "code": row["code"],
                    "name": row["name"],
                    "market": row.get("market"),
                    "close": self._to_native(row.get("종가")),
                    "change": self._to_native(row.get("변동폭")),
                    "change_rate": self._to_native(row.get("등락률")),
                    "volume": self._to_native(row.get("거래량")),
                    "trading_value": self._to_native(row.get("거래대금")),
                    "market_cap": self._to_native(row.get("시가총액")),
                    "per": self._to_native(row.get("PER")),
                    "pbr": self._to_native(row.get("PBR")),
                    "dividend_yield": self._to_native(row.get("DIV")),
                }
            )

        return results

    def get_stock_snapshot(
        self,
        stock_code: str,
        lookback_days: Optional[int] = None,
    ) -> Optional[Dict[str, object]]:
        """Build a summary snapshot for a ticker."""
        stock_code = str(stock_code).zfill(6)
        info = self.get_stock_info(stock_code)
        lookback_days = lookback_days or Config.DEFAULT_LOOKBACK_DAYS
        ohlcv = self.get_daily_ohlcv(
            stock_code,
            start_date=self._days_ago(max(lookback_days, 90)),
            end_date=self._reference_date(),
        )

        if info is None or ohlcv is None or ohlcv.empty:
            return None

        close_series = ohlcv["종가"]
        volume_series = ohlcv["거래량"]
        last_row = ohlcv.iloc[-1]
        previous_close = close_series.iloc[-2] if len(close_series) > 1 else close_series.iloc[-1]
        current_price = close_series.iloc[-1]
        change = current_price - previous_close
        change_rate = (change / previous_close * 100) if previous_close else 0.0

        market_cap_df = self.get_market_cap_snapshot(market="ALL")
        market_cap_row = (
            market_cap_df.loc[market_cap_df["code"] == stock_code]
            if "code" in market_cap_df.columns
            else self._empty_frame(["code"])
        )

        fundamentals_df = self.get_fundamental_snapshot(market="ALL")
        fundamentals_row = (
            fundamentals_df.loc[fundamentals_df["code"] == stock_code]
            if "code" in fundamentals_df.columns
            else self._empty_frame(["code"])
        )

        recent = ohlcv.tail(5).reset_index().copy()
        if "날짜" in recent.columns:
            recent["날짜"] = recent["날짜"].astype(str)

        return {
            "code": info["code"],
            "name": info["name"],
            "market": info.get("market"),
            "as_of": str(ohlcv.index[-1].date()),
            "previous_close": int(self._to_native(previous_close)),
            "current_price": int(self._to_native(current_price)),
            "change": int(self._to_native(change)),
            "change_rate": round(float(self._to_native(change_rate)), 2),
            "open": int(self._to_native(last_row["시가"])),
            "high": int(self._to_native(last_row["고가"])),
            "low": int(self._to_native(last_row["저가"])),
            "volume": int(self._to_native(last_row["거래량"])),
            "average_volume_20d": int(self._to_native(volume_series.tail(20).mean())),
            "high_52w": int(self._to_native(ohlcv["고가"].tail(252).max())),
            "low_52w": int(self._to_native(ohlcv["저가"].tail(252).min())),
            "ma5": round(float(self._to_native(close_series.tail(5).mean())), 2),
            "ma20": round(float(self._to_native(close_series.tail(20).mean())), 2),
            "ma60": round(float(self._to_native(close_series.tail(60).mean())), 2),
            "market_cap": self._to_native(
                market_cap_row.iloc[0]["시가총액"] if not market_cap_row.empty else None
            ),
            "shares_outstanding": self._to_native(
                market_cap_row.iloc[0]["상장주식수"] if not market_cap_row.empty else None
            ),
            "per": self._to_native(
                fundamentals_row.iloc[0]["PER"] if not fundamentals_row.empty else None
            ),
            "pbr": self._to_native(
                fundamentals_row.iloc[0]["PBR"] if not fundamentals_row.empty else None
            ),
            "dividend_yield": self._to_native(
                fundamentals_row.iloc[0]["DIV"] if not fundamentals_row.empty else None
            ),
            "recent_ohlcv": recent.to_dict("records"),
        }
