"""
주문 관리 모듈
주문 발주, 취소, 상태 조회 등의 기능을 포함합니다.
"""

from modules.kis_api import KISAPIWrapper
from utils.logger import setup_logger

logger = setup_logger(__name__)


class OrderManager:
    """주문 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        self.kis_api = KISAPIWrapper()
        self.active_orders = {}
        logger.info("OrderManager initialized")
    
    def buy_stock(self, stock_code, quantity, price=None):
        """
        주식 매수
        
        Args:
            stock_code (str): 종목 코드
            quantity (int): 수량
            price (float): 가격 (None이면 시장가)
        
        Returns:
            dict: 주문 결과
        """
        logger.info(f"Buying stock - {stock_code}, Qty: {quantity}, Price: {price}")
        
        result = self.kis_api.place_order(
            stock_code=stock_code,
            quantity=quantity,
            price=price,
            order_type="buy"
        )
        
        if result["success"]:
            order_id = result.get("order_id")
            self.active_orders[order_id] = {
                "type": "buy",
                "code": stock_code,
                "quantity": quantity,
                "price": price
            }
            logger.info(f"Buy order placed successfully - Order ID: {order_id}")
        
        return result
    
    def sell_stock(self, stock_code, quantity, price=None):
        """
        주식 매도
        
        Args:
            stock_code (str): 종목 코드
            quantity (int): 수량
            price (float): 가격 (None이면 시장가)
        
        Returns:
            dict: 주문 결과
        """
        logger.info(f"Selling stock - {stock_code}, Qty: {quantity}, Price: {price}")
        
        result = self.kis_api.place_order(
            stock_code=stock_code,
            quantity=quantity,
            price=price,
            order_type="sell"
        )
        
        if result["success"]:
            order_id = result.get("order_id")
            self.active_orders[order_id] = {
                "type": "sell",
                "code": stock_code,
                "quantity": quantity,
                "price": price
            }
            logger.info(f"Sell order placed successfully - Order ID: {order_id}")
        
        return result
    
    def cancel_order(self, order_id):
        """
        주문 취소
        
        Args:
            order_id (str): 주문 번호
        
        Returns:
            dict: 취소 결과
        """
        logger.info(f"Cancelling order - {order_id}")
        
        result = self.kis_api.cancel_order(order_id)
        
        if result["success"]:
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            logger.info(f"Order cancelled successfully - {order_id}")
        
        return result
    
    def get_order_status(self, order_id):
        """
        주문 상태 조회
        
        Args:
            order_id (str): 주문 번호
        
        Returns:
            dict: 주문 상태
        """
        logger.info(f"Getting order status - {order_id}")
        return self.kis_api.get_order_status(order_id)
    
    def get_active_orders(self):
        """
        활성 주문 목록 조회
        
        Returns:
            dict: 활성 주문 목록
        """
        logger.info("Fetching active orders")
        return self.active_orders
