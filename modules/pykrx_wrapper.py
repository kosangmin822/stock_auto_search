"""
pykrx 래퍼 모듈
pykrx를 사용하여 주식 데이터 조회 기능을 포함합니다.
"""

import pandas as pd
from pykrx import stock
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PyKRXWrapper:
    """pykrx 래퍼 클래스"""
    
    def __init__(self):
        """초기화"""
        logger.info("PyKRX Wrapper initialized")
    
    def get_stock_list(self):
        """
        전체 상장 주식 목록 조회
        
        Returns:
            pd.DataFrame: 주식 목록
        """
        try:
            logger.info("Fetching entire stock list")
            stock_list = stock.get_market_ticker_list(market="ALL")
            return stock_list
        except Exception as e:
            logger.error(f"Failed to get stock list: {str(e)}")
            return None
    
    def get_stock_info(self, stock_code):
        """
        개별 주식 정보 조회
        
        Args:
            stock_code (str): 종목 코드 (예: "005930")
        
        Returns:
            dict: 주식 정보
        """
        try:
            logger.info(f"Fetching stock info - {stock_code}")
            name = stock.get_market_ticker_name(stock_code)
            return {"code": stock_code, "name": name}
        except Exception as e:
            logger.error(f"Failed to get stock info: {str(e)}")
            return None
    
    def get_daily_ohlcv(self, stock_code, start_date=None, end_date=None):
        """
        일봉 OHLCV 데이터 조회
        
        Args:
            stock_code (str): 종목 코드
            start_date (str): 시작 날짜 (YYYYMMDD 형식, 기본값: 1년 전)
            end_date (str): 종료 날짜 (YYYYMMDD 형식, 기본값: 오늘)
        
        Returns:
            pd.DataFrame: OHLCV 데이터
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            
            logger.info(
                f"Fetching daily OHLCV - {stock_code}, "
                f"Period: {start_date} to {end_date}"
            )
            
            ohlcv = stock.get_market_ohlcv(
                fromdate=start_date,
                todate=end_date,
                ticker=stock_code
            )
            return ohlcv
        except Exception as e:
            logger.error(f"Failed to get daily OHLCV: {str(e)}")
            return None
    
    def get_current_price(self, stock_code):
        """
        현재가 조회
        
        Args:
            stock_code (str): 종목 코드
        
        Returns:
            float: 현재가
        """
        try:
            logger.info(f"Fetching current price - {stock_code}")
            price = stock.get_current_price(stock_code)
            return price
        except Exception as e:
            logger.error(f"Failed to get current price: {str(e)}")
            return None
    
    def search_stock_by_name(self, keyword):
        """
        주식명으로 검색
        
        Args:
            keyword (str): 검색 키워드
        
        Returns:
            list: 검색 결과 (종목 코드)
        """
        try:
            logger.info(f"Searching stock by name - {keyword}")
            stock_list = stock.get_market_ticker_list(market="ALL")
            results = []
            
            for code in stock_list:
                try:
                    name = stock.get_market_ticker_name(code)
                    if keyword.upper() in name.upper() or keyword in code:
                        results.append({"code": code, "name": name})
                except:
                    continue
            
            return results
        except Exception as e:
            logger.error(f"Failed to search stock: {str(e)}")
            return None
    
    def get_market_cap(self, stock_code):
        """
        시가총액 조회
        
        Args:
            stock_code (str): 종목 코드
        
        Returns:
            float: 시가총액
        """
        try:
            logger.info(f"Fetching market cap - {stock_code}")
            # pykrx에서 직접 제공하지 않으므로 별도 처리 필요
            return None
        except Exception as e:
            logger.error(f"Failed to get market cap: {str(e)}")
            return None
