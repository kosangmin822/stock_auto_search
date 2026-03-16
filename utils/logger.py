"""
로깅 설정 모듈
"""

import logging
import os
from config.config import Config


def setup_logger(name, log_level=None):
    """
    로거 설정
    
    Args:
        name: 로거 이름
        log_level: 로그 레벨 (기본값: INFO)
    
    Returns:
        logger: 설정된 로거 인스턴스
    """
    if log_level is None:
        log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 파일 핸들러
    log_dir = os.path.join(Config.DATA_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, f"{name}.log"), encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    
    # 포매터
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 핸들러 추가
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger
