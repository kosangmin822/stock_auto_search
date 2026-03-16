"""
메인 프로그램
KIS API와 pykrx를 조합한 주식 검색 및 주문 프로그램
"""

import sys
import os
from config.config import Config
from modules.stock_searcher import StockSearcher
from modules.order_manager import OrderManager
from utils.logger import setup_logger

logger = setup_logger(__name__)


class StockAutoSearch:
    """주식 자동검색 및 주문 시스템"""
    
    def __init__(self):
        """초기화"""
        try:
            Config.validate()
            self.stock_searcher = StockSearcher()
            self.order_manager = OrderManager()
            logger.info("StockAutoSearch system initialized successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            print(f"Error: {str(e)}")
            print("Please check your .env file and ensure all required fields are set.")
            sys.exit(1)
    
    def search_stock(self, keyword):
        """
        주식 검색
        
        Args:
            keyword (str): 검색 키워드 (이름 또는 코드)
        
        Returns:
            list: 검색 결과
        """
        logger.info(f"Searching stock with keyword: {keyword}")
        
        # 코드로만 검색 시도
        if len(keyword) == 6 and keyword.isdigit():
            result = self.stock_searcher.search_by_code(keyword)
            return [result] if result else []
        
        # 이름으로 검색
        return self.stock_searcher.search_by_name(keyword)
    
    def get_price_history(self, stock_code):
        """
        가격 이력 조회
        
        Args:
            stock_code (str): 종목 코드
        
        Returns:
            pd.DataFrame: 가격 데이터
        """
        logger.info(f"Fetching price history for {stock_code}")
        return self.stock_searcher.get_price_history(stock_code)
    
    def buy_stock(self, stock_code, quantity, price=None):
        """
        주식 매수
        
        Args:
            stock_code (str): 종목 코드
            quantity (int): 수량
            price (float): 가격
        
        Returns:
            dict: 주문 결과
        """
        return self.order_manager.buy_stock(stock_code, quantity, price)
    
    def sell_stock(self, stock_code, quantity, price=None):
        """
        주식 매도
        
        Args:
            stock_code (str): 종목 코드
            quantity (int): 수량
            price (float): 가격
        
        Returns:
            dict: 주문 결과
        """
        return self.order_manager.sell_stock(stock_code, quantity, price)
    
    def get_account_info(self):
        """
        계좌 정보 조회
        
        Returns:
            dict: 계좌 정보
        """
        return self.order_manager.kis_api.get_account_info()
    
    def get_balance(self):
        """
        계좌 잔액 조회
        
        Returns:
            dict: 잔액 정보
        """
        return self.order_manager.kis_api.get_balance()


def main():
    """메인 함수"""
    print("=" * 60)
    print("주식 자동검색 및 주문 시스템")
    print("=" * 60)
    print()
    
    # 시스템 초기화
    system = StockAutoSearch()
    
    # 예제: 삼성전자 검색
    print("[1] 주식 검색 예제")
    search_result = system.search_stock("삼성전자")
    if search_result:
        print(f"검색 결과: {search_result}")
    print()
    
    # 예제: 가격 이력 조회
    print("[2] 가격 이력 조회 예제")
    if search_result:
        stock_code = search_result[0]["code"]
        price_history = system.get_price_history(stock_code)
        if price_history is not None:
            print(f"최근 {len(price_history)}일 데이터:")
            print(price_history.head())
    print()
    
    # 예제: 계좌 정보 조회
    print("[3] 계좌 정보 조회 예제")
    account_info = system.get_account_info()
    print(f"계좌 정보: {account_info}")
    print()
    
    print("[시스템 준비 완료]")
    print("각 기능을 활용하여 프로그램을 개발하세요.")
    print()
    print("[주요 기능 예시]")
    print("- system.search_stock('삼성전자'): 주식 검색")
    print("- system.get_price_history('005930'): 가격 이력 조회")
    print("- system.buy_stock('005930', 10, 70000): 매수 주문")
    print("- system.sell_stock('005930', 10, 75000): 매도 주문")


if __name__ == "__main__":
    main()
