# KIS API 인증 구현 완료

## 📋 완료된 구현

### 1. **인증 (Authentication)**
✅ `authenticate()` - OAuth2 토큰 획득
- 엔드포인트: `/oauth2/tokenP`
- 메서드: POST (form data)
- 파라미터: grant_type, appkey, appsecret

### 2. **계좌 조회 (Account Queries)**
✅ `get_account_info()` - 계좌 정보 조회
- 엔드포인트: `/uapi/domestic-stock/v1/trading/inquire-account`
- 메서드: GET
- 토큰 필수

✅ `get_balance()` - 잔액 정보 조회
- 엔드포인트: `/uapi/domestic-stock/v1/trading/inquire-balance`
- 메서드: GET
- 토큰 필수

### 3. **주문 관리 (Order Management)**
✅ `place_order()` - 주문 발주
- 지정가 매수/매도 지원
- 엔드포인트: `/uapi/domestic-stock/v1/trading/order-cash`
- 메서드: POST
- 반환: 주문 번호

✅ `cancel_order()` - 주문 취소
- 엔드포인트: `/uapi/domestic-stock/v1/trading/order-cancel`
- 메서드: POST
- 반환: 취소 결과

✅ `get_order_status()` - 주문 상태 조회
- 엔드포인트: `/uapi/domestic-stock/v1/trading/inquire-order`
- 메서드: GET
- 반환: 주문 상태 정보

## 🔧 기능 특징

1. **자동 인증**: 토큰이 없으면 자동으로 인증 시도
2. **포괄적 에러 처리**: 모든 메서드에서 예외 처리 및 로깅
3. **SSL 인증서 검증 비활성화**: VTS 환경에 맞춤
4. **상세 로깅**: 디버깅을 위한 충분한 로그 정보 제공

## 🚀 사용 예시

```python
from modules.kis_api import KISAPIWrapper

# KIS API 인스턴스 생성
kis = KISAPIWrapper()

# 1. 인증
if kis.authenticate():
    print("인증 성공!")
    
    # 2. 계좌 정보 조회
    account_info = kis.get_account_info()
    
    # 3. 잔액 조회
    balance = kis.get_balance()
    
    # 4. 주문 발주
    order_result = kis.place_order(
        stock_code="005930",  # 삼성전자
        quantity=10,
        price=70000,
        order_type="buy"
    )
    
    # 5. 주문 상태 조회
    if order_result.get("success"):
        status = kis.get_order_status(order_result["order_id"])
else:
    print("인증 실패!")
```

## ⚠️ 현재 상태

**에러 발생**: EGW00002 (Server Error)

### 원인 분석
1. VTS 서버의 일시적 장애 가능성
2. API 자격증명의 유효성 확인 필요
3. IP 백리스트/접근 제한 확인 필요
4. 인증서 관련 설정 필요

### 해결 방법

#### Step 1: API 자격증명 확인
```bash
# .env 파일 검증
cat .env | grep KIS
```

필수 항목:
- KIS_API_KEY: 유효한 API 키
- KIS_SECRET_KEY: 유효한 시크릿 키
- KIS_ACCOUNT_NUMBER: 계좌번호
- KIS_ACCOUNT_TYPE: 계좌종류 (01: 위탁)

#### Step 2: VTS 서버 상태 확인
```bash
# Ping 테스트
ping openapivts.koreainvestment.com

# HTTPS 연결 테스트
curl -k https://openapivts.koreainvestment.com:29443
```

#### Step 3: KIS 고객 지원 확인
- 한국 투자증권 개발팀에 문의
- API 활성화 상태 확인
- VTS 환경 접근 권한 확인
- 인증서 설치 필요 여부 확인

## 📊 테스트 결과

### 전체 테스트 상태
```
[테스트 1] 주식 검색        ✅ 완료 (pykrx 활용)
[테스트 2] 가격 이력 조회   ✅ 완료 (pykrx 활용)
[테스트 3] 현재가 조회      ⚠️ 장시간 데이터 (pykrx)
[테스트 4] 주식 정보 조회   ✅ 완료 (pykrx 활용)
[테스트 6] KIS API 인증     ❌ 진행중 (EGW00002)
[테스트 5] 계좌 정보 조회   ⏳ 인증 필수
```

## 🔄 다음 단계

1. **인증 문제 해결**
   - KIS 고객 지원 연락
   - API 자격증명 재검증
   - 대체 인증 방식 연구

2. **실제 주문 테스트** (인증 후)
   - 데모 계정으로 테스트 주문
   - 주문 취소 테스트
   - 잔액 조회 확인

3. **통합 테스트**
   - 주식 검색 → 주문 → 상태 조회 전체 흐름

4. **자동화 기능 개발**
   - 스케줄 주문
   - 손절매/익절 로직
   - 포트폴리오 모니터링

## 📝 코드 참고

### kis_api.py 주요 메서드
- `authenticate()`: OAuth2 토큰 획득
- `get_account_info()`: 계좌 정보
- `get_balance()`: 계좌 잔액
- `place_order()`: 주문 발주
- `cancel_order()`: 주문 취소
- `get_order_status()`: 주문 상태

모든 메서드는 다음의 특징을 가집니다:
- 자동 인증 시도
- 포괄적 에러 처리
- 상세한 로깅
- JSON 응답 파싱

## 🎯 성공 확인 방법

인증이 성공하면 다음과 같이 출력됩니다:

```
2026-03-17 07:46:01,756 - modules.kis_api - INFO - KIS API authentication started
2026-03-17 07:46:01,933 - modules.kis_api - INFO - KIS API authentication successful
토큰 타입: Bearer
액세스 토큰: eyJhbGc... (실제 토큰)
```

---

**마지막 업데이트**: 2026-03-17  
**상태**: 인증 구현 완료, VTS 서버 에러 조사 중
