"""
테스트 스크립트
프로그램의 주요 기능을 테스트합니다.
"""

from main import StockAutoSearch
from modules.pykrx_wrapper import PyKRXWrapper
from modules.kis_api import KISAPIWrapper
from config.config import Config
import urllib3

# SSL 경고 제거 (VTS 환경용)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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


def test_kis_authentication():
    """KIS API 인증 테스트"""
    print("\n" + "="*60)
    print("[테스트 6] KIS API 인증")
    print("="*60)
    
    print("\n▶ 설정 검증:")
    try:
        Config.validate()
        print("  ✅ 필수 설정값 확인됨")
        print(f"    - API KEY: {Config.KIS_API_KEY[:10]}***")
        print(f"    - 계좌번호: {Config.KIS_ACCOUNT_NUMBER}")
        print(f"    - 계좌종류: {Config.KIS_ACCOUNT_TYPE}")
        print(f"    - Base URL: {Config.KIS_BASE_URL}")
    except ValueError as e:
        print(f"  ❌ 설정 오류: {str(e)}")
        return
    
    kis = KISAPIWrapper()
    
    print("\n▶ KIS API 인증 시도:")
    if kis.authenticate():
        print("  ✅ 인증 성공!")
        print(f"  - 토큰 타입: {kis.token_type}")
        print(f"  - 액세스 토큰: {kis.access_token[:20]}***")
        
        # 인증 후 계좌 정보 조회
        print("\n▶ 계좌 정보 조회:")
        account_info = kis.get_account_info()
        if account_info:
            print(f"  ✅ 계좌 정보: {account_info}")
        else:
            print("  ⚠️  계좌 정보 조회 실패")
        
        # 인증 후 잔액 조회
        print("\n▶ 계좌 잔액 조회:")
        balance = kis.get_balance()
        if balance:
            print(f"  ✅ 잔액 정보: {balance}")
        else:
            print("  ⚠️  잔액 조회 실패")
    else:
        print("  ❌ 인증 실패!")
        print("     - API 자격증명 확인")
        print("     - 네트워크 연결 확인")
        print("     - VTS 서버 접근 권한 확인")


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
        test_kis_authentication()  # KIS API 인증 테스트 추가
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
