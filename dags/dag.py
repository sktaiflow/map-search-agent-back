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
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.amazon.aws.transfers.gcs_to_s3 import GCSToS3Operator
from airflow.providers.sktvane.operators.nes import NesOperator
from airflow.utils.dates import days_ago
from google.cloud import storage
from hooks.slack import get_fail_alert, send_slack_message

# 환경별 설정
env = Variable.get("env", "stg")

if env == "stg":
    default_retries = 0
    branch = "develop"
    gcs_bucket_name = "air-airflow-stg"
    aws_bucket_name = "air-map-stg"
    api_base_url = "https://api.map-stg.sktelecom.com"
    schedule_time = "0 5 * * *"  # stg: 매일 오전 5시
else:  # prd
    default_retries = 2
    branch = "main"
    gcs_bucket_name = "air-airflow-prd"
    aws_bucket_name = "air-map-prd"
    api_base_url = "https://api.map.sktelecom.com"
    schedule_time = "0 2 * * *"  # prd: 매일 오전 2시


# DAG 기본 설정
default_args = {
    "owner": "hyejin_kim",
    "depends_on_past": False,
    "start_date": pendulum.datetime(2025, 8, 1, tz="Asia/Seoul"),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": default_retries,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": get_fail_alert(
        channel = "#air-map-datapipelines",
        email = ["hyejin_kim@sk.com", "victory56@sk.com", "jiwoon.ha@sk.com"]
    ),

}

# DAG 정의
dag = DAG(
    "map_product_sync",
    default_args=default_args,
    description="MAP Product Data Synchronization Pipeline",
    schedule_interval=schedule_time,
    max_active_runs=1, 
    catchup=False,
    tags=["map-api", "data-sync", "product-meta"],
)

# 노트북 실행 오퍼레이터 생성 함수
def get_nes_model_operator(task):
    operator = NesOperator(
        task_id=task,
        input_nb=f"https://github.com/sktaiflow/map-search-agent/tree/{branch}/src/app/dags/notebooks/{task}.ipynb",
        parameters={
            "env": env,
            "dt": "{{ ds }}",
            "version_date": "{{ ds_nodash }}",
            "map_api_key": Variable.get("MAP_API_KEY"),
            "map_api_base_url": api_base_url,
            "gcs_bucket_name": gcs_bucket_name,
        },
        dag=dag
    )
    return operator


def check_schema_changes(**context):
    """3번 노트북 결과를 확인해서 스키마 변경사항이 있으면 알림, 없으면 전처리 진행"""
    dt = context["ds"]
    version_date = context["ds_nodash"]
    
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(gcs_bucket_name)
    
    # field_changes_summary 파일 존재 확인
    summary_file_path = f"field_changes/{dt}/field_changes_summary_{version_date}.txt"
    blob = bucket.blob(summary_file_path)
    
    if blob.exists():
        print(f"Schema changes detected. Summary file exists: {summary_file_path}")
        return "send_schema_change_notification"
    else:
        print(f"No schema changes detected. Proceeding with preprocessing.")
        return "preprocessing_task"


def send_schema_change_notification(**context):
    """새로운 스키마 변경사항을 슬랙에 알림"""
    dt = context["ds"]
    version_date = context["ds_nodash"]
    
    try:
        # GCS에서 summary 파일 내용 읽기
        gcs_client = storage.Client()
        bucket = gcs_client.bucket(gcs_bucket_name)
        
        summary_file_path = f"field_changes/{dt}/field_changes_summary_{version_date}.txt"
        blob = bucket.blob(summary_file_path)
        summary_content = blob.download_as_text()
        
        message = f"""
🚨 **MAP API 스키마 변경 감지** 🚨

**날짜**: {dt}
**버전**: {version_date}

**변경 사항**:
```
{summary_content}
```

⚠️ **주의**: 새로운 필드가 감지되어 데이터 전처리가 중단되었습니다.
스키마 변경사항을 검토한 후 전처리 로직을 업데이트해주세요.

**관련 파일**:
- 상세 변경사항: `gs://{gcs_bucket_name}/field_changes/{dt}/field_changes_{version_date}.json`
- 요약: `gs://{gcs_bucket_name}/field_changes/{dt}/field_changes_summary_{version_date}.txt`
        """.strip()
        
        # 슬랙 알림 전송
        send_slack_message(
            channel="#air-map-datapipelines",
            message=message
        )
        
        print("Schema change notification sent successfully")
        
    except Exception as e:
        print(f"Error sending schema change notification: {e}")
        raise


# 노트북 태스크 생성
collect_product_ids = get_nes_model_operator("01_collect_product_ids")
collect_product_details = get_nes_model_operator("02_collect_product_details")
detect_changes = get_nes_model_operator("03_detect_changes")
preprocessing_task = get_nes_model_operator("04_preprocessing")

# 조건부 분기 태스크
check_changes = BranchPythonOperator(
    task_id="check_schema_changes",
    python_callable=check_schema_changes,
    dag=dag
)

# 스키마 변경 알림 태스크
send_notification = PythonOperator(
    task_id="send_schema_change_notification",
    python_callable=send_schema_change_notification,
    dag=dag
)

# 전처리 완료 후 진행할 태스크들을 위한 조건부 엔드
preprocessing_end = EmptyOperator(
    task_id="preprocessing_completed",
    dag=dag
)


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

# Task 관계 설정
start >> collect_product_ids >> collect_product_details >> detect_changes >> check_changes

# 분기 설정
check_changes >> [send_notification, preprocessing_task]

# 스키마 변경 감지 시: 알림만 보내고 종료
send_notification >> end

# 정상 처리 시: 전처리 → GCS to S3 → 종료  
preprocessing_task >> preprocessing_end >> gcs_to_s3 >> end