"""
테스트 스크립트
프로그램의 주요 기능을 테스트합니다.
"""

from main import StockAutoSearch
from modules.pykrx_wrapper import PyKRXWrapper


def test_stock_search():
    """주식 검색 테스트"""
    print("\n" + "="*60)
    print("[테스트 1] 주식 검색")
    print("="*60)
    
    system = StockAutoSearch()
    
    # 삼성전자 검색
    print("\n▶ 삼성전자 검색:")
    results = system.search_stock("삼성전자")
    for stock in results:
        print(f"  - {stock['code']}: {stock['name']}")
    
    # SK하이닉스 검색
    print("\n▶ SK하이닉스 검색:")
    results = system.search_stock("SK하이닉스")
    for stock in results:
        print(f"  - {stock['code']}: {stock['name']}")
    
    # 코드로 검색
    print("\n▶ 코드 검색 (005930):")
    result = system.search_stock("005930")
    print(f"  - {result}")


def test_price_history():
    """가격 이력 테스트"""
    print("\n" + "="*60)
    print("[테스트 2] 가격 이력 조회")
    print("="*60)
    
    system = StockAutoSearch()
    
    print("\n▶ 삼성전자(005930) 최근 5일 데이터:")
    history = system.get_price_history("005930")
    
    if history is not None:
        print(f"\n총 {len(history)}일 데이터:")
        print(history.head())
    else:
        print("데이터 없음")


def test_current_price():
    """현재가 조회 테스트"""
    print("\n" + "="*60)
    print("[테스트 3] 현재가 조회")
    print("="*60)
    
    pykrx = PyKRXWrapper()
    
    stocks = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("068270", "셀트리온"),
    ]
    
    for code, name in stocks:
        price = pykrx.get_current_price(code)
        if price is not None:
            print(f"\n▶ {name}({code}): {price:,.0f}원")
        else:
            print(f"\n▶ {name}({code}): 데이터 없음")


def test_stock_info():
    """주식 정보 테스트"""
    print("\n" + "="*60)
    print("[테스트 4] 주식 정보 조회")
    print("="*60)
    
    pykrx = PyKRXWrapper()
    
    codes = ["005930", "000660", "068270", "035720"]
    
    print("\n종목 정보:")
    for code in codes:
        info = pykrx.get_stock_info(code)
        if info:
            print(f"  - {code}: {info['name']}")


def test_account_info():
    """계좌 정보 테스트"""
    print("\n" + "="*60)
    print("[테스트 5] 계좌 정보 조회 (KIS API)")
    print("="*60)
    
    system = StockAutoSearch()
    
    print("\n▶ 계좌 정보:")
    account = system.get_account_info()
    print(f"  {account}")
    
    print("\n▶ 계좌 잔액:")
    balance = system.get_balance()
    print(f"  {balance}")
    
    print("\n📌 주의: KIS API 인증이 구현되지 않아 빈 값이 출력됩니다.")


def main():
    """메인 테스트 함수"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  주식 자동검색 시스템 - 테스트 스크립트".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        test_stock_search()
        test_price_history()
        test_current_price()
        test_stock_info()
        test_account_info()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
