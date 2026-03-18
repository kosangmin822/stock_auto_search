"""KIS API wrapper for account, order, and market-data requests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import requests

from config.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KISAPIWrapper:
    """Thin wrapper around Korea Investment & Securities Open API."""

    def __init__(self):
        self.api_key = Config.KIS_API_KEY
        self.secret_key = Config.KIS_SECRET_KEY
        self.account_number = Config.KIS_ACCOUNT_NUMBER
        self.account_type = Config.KIS_ACCOUNT_TYPE
        self.base_url = Config.KIS_BASE_URL
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        self.token_type: str = "Bearer"
        self._auth_failed_until: Optional[datetime] = None
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        logger.info("KIS API Wrapper initialized")

    def authenticate(self) -> bool:
        try:
            logger.info("KIS API authentication started")
            auth_url = f"{self.base_url}/oauth2/tokenP"
            response = requests.post(
                auth_url,
                data={
                    "grant_type": "client_credentials",
                    "appkey": self.api_key,
                    "appsecret": self.secret_key,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                    "User-Agent": "Mozilla/5.0",
                },
                verify=False,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            self.access_token = payload.get("access_token")
            self.token_type = payload.get("token_type", "Bearer")
            if not self.access_token:
                logger.error("No access token in KIS response")
                return False
            logger.info("KIS API authentication successful")
            return True
        except Exception as exc:
            self._auth_failed_until = datetime.now() + timedelta(minutes=3)
            logger.error("KIS API authentication failed: %s", exc)
            return False

    def _ensure_authenticated(self) -> bool:
        if self.access_token:
            return True
        if self._auth_failed_until and datetime.now() < self._auth_failed_until:
            logger.info("Skipping KIS authentication retry until cooldown expires")
            return False
        logger.warning("Not authenticated. Attempting authentication...")
        return self.authenticate()

    def _build_headers(self, tr_id: str) -> Dict[str, str]:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"{self.token_type} {self.access_token}",
            "appKey": self.api_key or "",
            "appSecret": self.secret_key or "",
            "tr_id": tr_id,
            "custtype": "P",
            "User-Agent": "Mozilla/5.0",
        }

    def _get(self, path: str, tr_id: str, params: Dict[str, Any], timeout: int = 10) -> Optional[Dict[str, Any]]:
        if not self._ensure_authenticated():
            return None
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                headers=self._build_headers(tr_id),
                params=params,
                verify=False,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("KIS GET failed for %s: %s", path, exc)
            return None

    def _post(self, path: str, tr_id: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._ensure_authenticated():
            return None
        try:
            response = self.session.post(
                f"{self.base_url}{path}",
                headers=self._build_headers(tr_id),
                json=body,
                verify=False,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("KIS POST failed for %s: %s", path, exc)
            return None

    def get_intraday_ohlcv(self, stock_code: str, interval: int = 1) -> Optional[pd.DataFrame]:
        payload = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
            "FHKST03010200",
            {
                "FID_ETC_CLS_CODE": "",
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": str(stock_code).zfill(6),
                "FID_INPUT_HOUR_1": datetime.now().strftime("%H%M%S"),
                "FID_PW_DATA_INCU_YN": "Y",
            },
        )
        if not payload:
            return None

        rows = payload.get("output2") or payload.get("output1") or []
        if not rows:
            logger.warning("No intraday OHLCV rows returned for %s", stock_code)
            return None

        frame = pd.DataFrame(rows)
        if frame.empty:
            return None

        date_col = next((col for col in frame.columns if "date" in col.lower()), "stck_bsop_date")
        time_col = next((col for col in frame.columns if "hour" in col.lower() or "time" in col.lower()), "stck_cntg_hour")
        frame = frame.rename(
            columns={
                "stck_oprc": "open",
                "stck_hgpr": "high",
                "stck_lwpr": "low",
                "stck_prpr": "close",
                "cntg_vol": "volume",
                "acml_vol": "volume",
            }
        )
        if date_col not in frame.columns or time_col not in frame.columns:
            logger.warning("Unexpected intraday columns: %s", list(frame.columns))
            return None

        frame["date"] = pd.to_datetime(
            frame[date_col].astype(str) + frame[time_col].astype(str).str.zfill(6),
            format="%Y%m%d%H%M%S",
            errors="coerce",
        )
        for column in ["open", "high", "low", "close", "volume"]:
            frame[column] = pd.to_numeric(frame.get(column), errors="coerce")

        frame = frame.dropna(subset=["date", "close"]).sort_values("date")
        if frame.empty:
            return None

        base = frame[["date", "open", "high", "low", "close", "volume"]]
        if int(interval) <= 1:
            return base.reset_index(drop=True)

        aggregated = (
            base.set_index("date")
            .resample(f"{int(interval)}min")
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )
        return aggregated

    @staticmethod
    def _to_number(value):
        if value in (None, "", "-"):
            return None
        try:
            numeric = float(value)
        except Exception:
            return value
        if numeric.is_integer():
            return int(numeric)
        return numeric

    def get_current_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        stock_code = str(stock_code).zfill(6)
        cached = self._quote_cache.get(stock_code)
        if cached:
            return dict(cached)

        payload = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": stock_code,
            },
            timeout=3,
        )
        if not payload:
            return None

        output = payload.get("output") or {}
        if not output:
            logger.warning("No current quote payload returned for %s", stock_code)
            return None

        execution_strength = None
        for key in ("tday_rltv", "cttr", "cpfn", "ccld_dvsn"):
            if key in output and output.get(key) not in (None, ""):
                execution_strength = self._to_number(output.get(key))
                break

        result = {
            "trading_value": self._to_number(output.get("acml_tr_pbmn")),
            "execution_strength": execution_strength,
            "high_52w": self._to_number(output.get("w52_hgpr")),
            "low_52w": self._to_number(output.get("w52_lwpr")),
            "per": self._to_number(output.get("per")),
            "pbr": self._to_number(output.get("pbr")),
        }
        self._quote_cache[stock_code] = dict(result)
        return result

    def get_account_info(self):
        payload = self._get(
            "/uapi/domestic-stock/v1/trading/inquire-account",
            "VTTC8434R",
            {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "INQR_DVSN_CD": "02",
                "UNPR_DVSN": "01",
            },
        )
        if not payload:
            return None
        if payload.get("rt_cd") == "0":
            return {"total_assets": payload.get("output")}
        return payload

    def get_balance(self):
        payload = self._get(
            "/uapi/domestic-stock/v1/trading/inquire-balance",
            "VTTC8434R",
            {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "INQR_DVSN_CD": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "00",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
        )
        if not payload:
            return None
        if payload.get("rt_cd") == "0":
            return {
                "total_amount": (payload.get("output2") or [{}])[0].get("tot_evlu_amt"),
                "available_amount": (payload.get("output2") or [{}])[0].get("dnca_tot_amt"),
                "holdings": payload.get("output1", []),
            }
        return payload

    def place_order(self, stock_code, quantity, price, order_type="buy"):
        tr_id = "VTTC0802U" if order_type.lower() == "buy" else "VTTC0801U"
        payload = self._post(
            "/uapi/domestic-stock/v1/trading/order-cash",
            tr_id,
            {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "PDNO": str(stock_code).zfill(6),
                "ORD_DVSN": "01" if price is not None else "01",
                "ORD_QTY": str(quantity),
                "ORD_UNPR": str(int(price or 0)),
            },
        )
        if not payload:
            return {"success": False, "error": "request failed"}
        if payload.get("rt_cd") == "0":
            return {
                "success": True,
                "order_id": (payload.get("output") or {}).get("ODNO"),
                "message": payload.get("msg1", "Order placed"),
            }
        return {"success": False, "error": payload.get("msg1", "Unknown error")}

    def cancel_order(self, order_id):
        payload = self._post(
            "/uapi/domestic-stock/v1/trading/order-rvsecncl",
            "VTTC0803U",
            {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "KRX_FWDG_ORD_ORGNO": "",
                "ORGN_ODNO": str(order_id),
                "ORD_DVSN": "00",
                "RVSE_CNCL_DVSN_CD": "02",
                "ORD_QTY": "0",
                "ORD_UNPR": "0",
                "QTY_ALL_ORD_YN": "Y",
            },
        )
        if not payload:
            return {"success": False, "error": "request failed"}
        if payload.get("rt_cd") == "0":
            return {"success": True, "message": payload.get("msg1", "Order cancelled")}
        return {"success": False, "error": payload.get("msg1", "Unknown error")}

    def get_order_status(self, order_id):
        payload = self._get(
            "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
            "VTTC8001R",
            {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "INQR_STRT_DT": datetime.now().strftime("%Y%m%d"),
                "INQR_END_DT": datetime.now().strftime("%Y%m%d"),
                "SLL_BUY_DVSN_CD": "00",
                "INQR_DVSN": "00",
                "PDNO": "",
                "CCLD_DVSN": "00",
                "ORD_GNO_BRNO": "",
                "ODNO": str(order_id),
                "INQR_DVSN_3": "00",
                "INQR_DVSN_1": "",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
        )
        if not payload:
            return None
        if payload.get("rt_cd") == "0":
            return {"order_id": order_id, "status": payload.get("output1", [])}
        return None
