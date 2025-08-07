"""
MAP Product Data Synchronization DAG

이 DAG는 다음 단계들을 순차적으로 실행합니다:
1. Product ID 수집 (MAP API)
2. 상세 정보 수집 (병렬 처리)
3. 변경사항 감지 (새로 추가된 필드만)
4. 동료 작업 실행 (Neo4j 업데이트 등)

각 단계는 Papermill을 사용하여 Jupyter 노트북으로 실행되며,
실행 결과를 시각적으로 확인할 수 있습니다.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.transfers.gcs_to_s3 import GCSToS3Operator
from airflow.providers.sktvane.operators.nes import NesOperator
from airflow.utils.dates import days_ago

# 환경별 설정
env = Variable.get("env", "stg")

if env == "stg":
    default_retries = 0
    branch = 'develop'
    gcs_bucket_name = "air-airflow-stg"
    aws_bucket_name = "air-map-stg"
    api_base_url = "https://api.map-stg.sktelecom.com"
else:  # prd
    default_retries = 2
    branch = 'main'
    gcs_bucket_name = "air-airflow-prd"
    aws_bucket_name = "air-map-prd"
    api_base_url = "https://api.map.sktelecom.com"

# 기본 설정값들 (Airflow Variables가 없을 때 사용)
DEFAULT_CONFIG = {
    "MAP_API_BASE_URL": api_base_url
}


# DAG 기본 설정
default_args = {
    'owner': 'hyejin_kim',
    'depends_on_past': False,
    'start_date': pendulum.datetime(2025, 8, 1, tz="Asia/Seoul"),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': default_retries,
    'retry_delay': timedelta(minutes=5),
    'email': ['hyejin_kim@sk.com']  # 실제 이메일로 변경 필요
}

# DAG 정의
dag = DAG(
    'map_product_sync',
    default_args=default_args,
    description='MAP Product Data Synchronization Pipeline',
    schedule_interval='0 2 * * *',  # 매일 오전 2시 실행
    max_active_runs=1,  # 동시 실행 방지
    catchup=False,
    tags=['map-api', 'data-sync', 'product-meta'],
)

# 노트북 실행 오퍼레이터 생성 함수
def get_nes_model_operator(task):
    """NES 오퍼레이터 생성"""
    operator = NesOperator(
        task_id=task,
        input_nb=f'https://github.com/sktaiflow/map-search-agent/tree/{branch}/src/app/data_sync/notebooks/{task}.ipynb',
        parameters={
            'env': env,
            'dt': '{{ ds }}',
            'version_date': '{{ ds_nodash }}',
            'map_api_key': Variable.get("MAP_API_KEY"),
            'map_api_base_url': Variable.get("MAP_API_BASE_URL", DEFAULT_CONFIG["MAP_API_BASE_URL"])
        },
        dag=dag
    )
    return operator

# 노트북 태스크 생성
collect_product_ids = get_nes_model_operator('01_collect_product_ids')
collect_product_details = get_nes_model_operator('02_collect_product_details')
detect_changes = get_nes_model_operator('03_detect_changes')
colleague_task = get_nes_model_operator('04_colleague_task')


gcs_to_s3 = GCSToS3Operator(
    task_id="gcs_to_s3",
    gcs_bucket=gcs_bucket_name,
    prefix=f"product_meta_raw/{{{{ ds }}}}",
    match_glob="**/*.json",
    dest_s3_key=f"s3://{aws_bucket_name}",
    keep_directory_structure=True,
    replace=True,
)

start = EmptyOperator(task_id="start_dag", dag=dag)
end = EmptyOperator(task_id="end_dag", dag=dag)

start >> collect_product_ids >> collect_product_details >> detect_changes >> colleague_task >> gcs_to_s3 >> end