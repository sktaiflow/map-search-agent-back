# src/app/data_sync/config.py

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DataSyncConfig:
    """Airflow DAG를 위한 Data sync configuration"""
    
    # MAP API 설정
    map_api_base_url: str = os.getenv("MAP_API_BASE_URL", "https://api.map-stg.sktelecom.com")
    map_api_key: Optional[str] = os.getenv("MAP_API_KEY", "vdFXmlw8DqSimAmysgojBVoXE34C3pDw")
    api_timeout: int = int(os.getenv("API_TIMEOUT", "30"))
    
    # 데이터 저장 경로 (Airflow 환경용)
    dataload_dir: str = os.getenv("DATALOAD_DIR", "./notebooks/dataload/")
    
    # 동시 실행 설정
    max_workers: int = int(os.getenv("MAX_WORKERS", "10"))
    
    # 로깅 설정
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


# 싱글톤 설정 인스턴스
config = DataSyncConfig()