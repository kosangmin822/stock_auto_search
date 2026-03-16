"""
설정 관리 모듈
환경변수에서 KIS API 및 시스템 설정을 로드합니다.
"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """기본 설정"""
    # KIS API 설정
    KIS_API_KEY = os.getenv("KIS_API_KEY")
    KIS_SECRET_KEY = os.getenv("KIS_SECRET_KEY")
    KIS_ACCOUNT_NUMBER = os.getenv("KIS_ACCOUNT_NUMBER")
    KIS_ACCOUNT_TYPE = os.getenv("KIS_ACCOUNT_TYPE")
    KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapivts.koreainvestment.com:29443")
    
    # 로깅 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # 데이터 경로
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    @classmethod
    def validate(cls):
        """필수 설정값 검증"""
        required_fields = [
            "KIS_API_KEY",
            "KIS_SECRET_KEY",
            "KIS_ACCOUNT_NUMBER",
            "KIS_ACCOUNT_TYPE"
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required config fields: {', '.join(missing_fields)}")
        
        return True
