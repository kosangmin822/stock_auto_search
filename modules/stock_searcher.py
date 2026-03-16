"""
주식 검색 모듈
주식 정보 검색 및 필터링 기능을 포함합니다.
"""

from modules.pykrx_wrapper import PyKRXWrapper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StockSearcher:
    """주식 검색 클래스"""
    
    def __init__(self):
        """초기화"""
        self.pykrx = PyKRXWrapper()
        logger.info("StockSearcher initialized")
    
    def search_by_name(self, keyword):
        """
        주식명으로 검색
        
        Args:
            keyword (str): 검색 키워드
        
        Returns:
            list: 검색 결과
        """
        logger.info(f"Searching stock by name: {keyword}")
        return self.pykrx.search_stock_by_name(keyword)
    
    def search_by_code(self, code):
        """
        종목 코드로 검색
        
        Args:
            code (str): 종목 코드
        
        Returns:
            dict: 주식 정보
        """
        logger.info(f"Searching stock by code: {code}")
        return self.pykrx.get_stock_info(code)
    
    def get_top_gainers(self, limit=10):
        """
        상승률 상위 주식 조회 (구현 필요)
        
        Args:
            limit (int): 조회할 종목 수
        
        Returns:
            list: 상위 주식 목록
        """
        logger.info(f"Fetching top {limit} gainers")
        # 실제 구현 필요
        return []
    
    def get_top_losers(self, limit=10):
        """
        하락률 상위 주식 조회 (구현 필요)
        
        Args:
            limit (int): 조회할 종목 수
        
        Returns:
            list: 하위 주식 목록
        """
        logger.info(f"Fetching top {limit} losers")
        # 실제 구현 필요
        return []
    
    def get_price_history(self, code, period="daily"):
        """
        가격 이력 조회
        
        Args:
            code (str): 종목 코드
            period (str): 기간 (daily, weekly, monthly)
        
        Returns:
            pd.DataFrame: 가격 데이터
        """
        logger.info(f"Fetching price history for {code} ({period})")
        
        if period == "daily":
            return self.pykrx.get_daily_ohlcv(code)
        else:
            logger.warning(f"Period {period} not implemented yet")
            return None
