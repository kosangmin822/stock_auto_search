"""
KIS API 래퍼 모듈
한국 투자증권 API를 사용하여 주문 및 계좌 관련 기능을 포함합니다.
"""

import requests
import json
import hashlib
import hmac
import base64
from config.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KISAPIWrapper:
    """KIS API 래퍼 클래스"""
    
    def __init__(self):
        """초기화"""
        self.api_key = Config.KIS_API_KEY
        self.secret_key = Config.KIS_SECRET_KEY
        self.account_number = Config.KIS_ACCOUNT_NUMBER
        self.account_type = Config.KIS_ACCOUNT_TYPE
        self.base_url = Config.KIS_BASE_URL
        self.session = requests.Session()
        self.access_token = None
        self.token_type = None
        logger.info("KIS API Wrapper initialized")
    
    def _get_signature(self, path, nonce, timestamp, method="POST"):
        """
        KIS API 서명 생성 (HMAC-SHA256)
        
        Args:
            path (str): API 경로
            nonce (str): Nonce 값
            timestamp (str): 타임스탐프
            method (str): HTTP 메소드
        
        Returns:
            str: Base64 인코딩된 서명
        """
        message = f"{method} {path} {timestamp} {nonce}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()
    
    def authenticate(self):
        """
        KIS API 인증 (OAuth2 Token 획득)
        
        Returns:
            bool: 인증 성공 여부
        """
        try:
            logger.info("KIS API authentication started")
            
            # 인증 엔드포인트
            auth_path = "/oauth2/tokenP"
            auth_url = f"{self.base_url}{auth_path}"
            
            # 요청 헤더 구성
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            # 요청 본문 (Form data)
            # KIS API는 다양한 파라미터 조합을 지원합니다
            payload = f"grant_type=client_credentials&appkey={self.api_key}&appsecret={self.secret_key}"
            
            logger.debug(f"Auth URL: {auth_url}")
            logger.debug(f"Request payload length: {len(payload)}")
            
            # HTTPS 인증서 검증 비활성화 (VTS 환경)
            response = requests.post(
                auth_url,
                data=payload,
                headers=headers,
                verify=False,
                timeout=10
            )
            
            logger.debug(f"Auth response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    self.access_token = response_data.get("access_token")
                    self.token_type = response_data.get("token_type", "Bearer")
                    
                    if self.access_token:
                        logger.info("KIS API authentication successful")
                        logger.info(f"Token expires in: {response_data.get('expires_in', 'unknown')} seconds")
                        return True
                    else:
                        logger.error(f"No access token in response")
                        return False
                except ValueError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    logger.debug(f"Response text: {response.text}")
                    return False
            else:
                logger.error(f"Authentication failed: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error: {error_data}")
                except:
                    logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"KIS API authentication failed: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def get_account_info(self):
        """
        계좌 정보 조회
        
        Returns:
            dict: 계좌 정보
        """
        try:
            if not self.access_token:
                logger.warning("Not authenticated. Attempting authentication...")
                if not self.authenticate():
                    logger.error("Authentication required for account info")
                    return None
            
            logger.info("Fetching account info")
            
            # 계좌 정보 조회 엔드포인트
            api_path = "/uapi/domestic-stock/v1/trading/inquire-account"
            api_url = f"{self.base_url}{api_path}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{self.token_type} {self.access_token}",
                "appKey": self.api_key,
                "appSecret": self.secret_key,
                "User-Agent": "Mozilla/5.0"
            }
            
            params = {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "INQR_DVSN_CD": "02",
                "UNPR_DVSN": "01"
            }
            
            response = requests.get(
                api_url,
                headers=headers,
                params=params,
                verify=False,
                timeout=10
            )
            
            logger.debug(f"Account info response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":  # 성공
                    logger.info("Account info fetch successful")
                    return {
                        "total_assets": data.get("output")
                    }
                else:
                    logger.warning(f"API error: {data.get('msg1')}")
                    return data
            else:
                logger.error(f"Failed to get account info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return None
    
    def get_balance(self):
        """
        계좌 잔액 조회
        
        Returns:
            dict: 잔액 정보
        """
        try:
            if not self.access_token:
                logger.warning("Not authenticated. Attempting authentication...")
                if not self.authenticate():
                    logger.error("Authentication required for balance")
                    return None
            
            logger.info("Fetching account balance")
            
            # 잔액 조회 엔드포인트
            api_path = "/uapi/domestic-stock/v1/trading/inquire-balance"
            api_url = f"{self.base_url}{api_path}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{self.token_type} {self.access_token}",
                "appKey": self.api_key,
                "appSecret": self.secret_key,
                "User-Agent": "Mozilla/5.0"
            }
            
            params = {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "INQR_DVSN_CD": "02",
                "UNPR_DVSN": "01",
                "Fund_selstn": "00"
            }
            
            response = requests.get(
                api_url,
                headers=headers,
                params=params,
                verify=False,
                timeout=10
            )
            
            logger.debug(f"Balance response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":  # 성공
                    logger.info("Balance fetch successful")
                    output = data.get("output1", {})
                    return {
                        "total_amount": output.get("scts_balance"),
                        "available_amount": output.get("scts_buy_amt"),
                        "holdings": data.get("output2", [])
                    }
                else:
                    logger.warning(f"API error: {data.get('msg1')}")
                    return data
            else:
                logger.error(f"Failed to get balance: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            return None
    
    def place_order(self, stock_code, quantity, price, order_type="buy"):
        """
        주문 발주
        
        Args:
            stock_code (str): 종목 코드
            quantity (int): 주문 수량
            price (float): 주문 가격
            order_type (str): 주문 유형 (buy/sell)
        
        Returns:
            dict: 주문 결과
        """
        try:
            if not self.access_token:
                logger.warning("Not authenticated. Attempting authentication...")
                if not self.authenticate():
                    logger.error("Authentication required for placing order")
                    return {"success": False, "error": "Authentication failed"}
            
            logger.info(
                f"Placing {order_type} order - {stock_code}, "
                f"Qty: {quantity}, Price: {price}"
            )
            
            # 주문 엔드포인트
            api_path = "/uapi/domestic-stock/v1/trading/order-cash"
            api_url = f"{self.base_url}{api_path}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{self.token_type} {self.access_token}",
                "appKey": self.api_key,
                "appSecret": self.secret_key,
                "User-Agent": "Mozilla/5.0"
            }
            
            # 주문 유형 결정
            order_divisions = {
                "buy": "01",   # 지정가 매수
                "sell": "01"   # 지정가 매도
            }
            
            order_division = order_divisions.get(order_type.lower(), "01")
            
            # 주문 본문
            body = {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "PDNO": stock_code,
                "ORD_DVSN_CD": order_division,
                "ORD_QTY": str(quantity),
                "ORD_UNPR": str(int(price)),
                "SLL_TYPE": "00"
            }
            
            response = requests.post(
                api_url,
                json=body,
                headers=headers,
                verify=False,
                timeout=10
            )
            
            logger.debug(f"Order response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":  # 성공
                    order_id = data.get("output", {}).get("ODNO")
                    logger.info(f"Order placed successfully - Order ID: {order_id}")
                    return {
                        "success": True,
                        "order_id": order_id,
                        "message": data.get("msg1", "Order placed")
                    }
                else:
                    logger.warning(f"Order placement failed: {data.get('msg1')}")
                    return {
                        "success": False,
                        "error": data.get("msg1", "Unknown error")
                    }
            else:
                logger.error(f"Failed to place order: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def cancel_order(self, order_id):
        """
        주문 취소
        
        Args:
            order_id (str): 주문 번호
        
        Returns:
            dict: 취소 결과
        """
        try:
            if not self.access_token:
                logger.warning("Not authenticated. Attempting authentication...")
                if not self.authenticate():
                    logger.error("Authentication required for cancelling order")
                    return {"success": False, "error": "Authentication failed"}
            
            logger.info(f"Cancelling order - {order_id}")
            
            # 주문 취소 엔드포인트
            api_path = "/uapi/domestic-stock/v1/trading/order-cancel"
            api_url = f"{self.base_url}{api_path}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{self.token_type} {self.access_token}",
                "appKey": self.api_key,
                "appSecret": self.secret_key,
                "User-Agent": "Mozilla/5.0"
            }
            
            # 취소 요청 본문
            body = {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "ODNO": order_id,
                "ORD_DVSN_CD": "02"  # 취소
            }
            
            response = requests.post(
                api_url,
                json=body,
                headers=headers,
                verify=False,
                timeout=10
            )
            
            logger.debug(f"Cancel response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":  # 성공
                    logger.info(f"Order cancelled successfully - {order_id}")
                    return {
                        "success": True,
                        "message": data.get("msg1", "Order cancelled")
                    }
                else:
                    logger.warning(f"Order cancellation failed: {data.get('msg1')}")
                    return {
                        "success": False,
                        "error": data.get("msg1", "Unknown error")
                    }
            else:
                logger.error(f"Failed to cancel order: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_order_status(self, order_id):
        """
        주문 상태 조회
        
        Args:
            order_id (str): 주문 번호
        
        Returns:
            dict: 주문 상태
        """
        try:
            if not self.access_token:
                logger.warning("Not authenticated. Attempting authentication...")
                if not self.authenticate():
                    logger.error("Authentication required for order status")
                    return None
            
            logger.info(f"Getting order status - {order_id}")
            
            # 주문 상태 조회 엔드포인트
            api_path = "/uapi/domestic-stock/v1/trading/inquire-order"
            api_url = f"{self.base_url}{api_path}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{self.token_type} {self.access_token}",
                "appKey": self.api_key,
                "appSecret": self.secret_key,
                "User-Agent": "Mozilla/5.0"
            }
            
            params = {
                "CANO": self.account_number,
                "ACNT_PRDT_CD": self.account_type,
                "ODNO": order_id,
                "INQR_DVSN_CD": "00"
            }
            
            response = requests.get(
                api_url,
                headers=headers,
                params=params,
                verify=False,
                timeout=10
            )
            
            logger.debug(f"Order status response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("rt_cd") == "0":  # 성공
                    logger.info(f"Order status retrieved - {order_id}")
                    return {
                        "order_id": order_id,
                        "status": data.get("output", {})
                    }
                else:
                    logger.warning(f"Order status query failed: {data.get('msg1')}")
                    return None
            else:
                logger.error(f"Failed to get order status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get order status: {str(e)}")
            return None
