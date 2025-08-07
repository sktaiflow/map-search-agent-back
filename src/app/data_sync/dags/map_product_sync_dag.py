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

from airflow import DAG
from airflow.operators.papermill_operator import PapermillOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago


# DAG 기본 설정
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email': ['data-team@company.com']  # 실제 이메일로 변경 필요
}

# DAG 정의
dag = DAG(
    'map_product_sync',
    default_args=default_args,
    description='MAP Product Data Synchronization Pipeline',
    schedule_interval='0 2 * * *',  # 매일 오전 2시 실행
    max_active_runs=1,  # 동시 실행 방지
    catchup=False,
    tags=['map-api', 'data-sync', 'product-data'],
)

# 노트북 파일 경로 설정
NOTEBOOKS_DIR = Path(__file__).parent.parent / "notebooks"
DATALOAD_DIR = Path(__file__).parent.parent / "notebooks" / "dataload"

# DAG 실행 파라미터 준비 함수
def prepare_dag_params(**context):
    """DAG 실행에 필요한 공통 파라미터 준비"""
    execution_date = context['execution_date']
    version_date = execution_date.strftime("%Y%m%d")
    
    # 환경변수에서 제한값 읽기 (테스트용)
    import os
    limit = os.getenv("PRODUCT_LIMIT", None)
    if limit:
        limit = int(limit)
    
    params = {
        'version_date': version_date,
        'limit': limit,
        'execution_date': execution_date.isoformat()
    }
    
    # 다음 태스크들에서 사용할 수 있도록 XCom에 저장
    context['task_instance'].xcom_push(key='dag_params', value=params)
    
    return params

# 1. DAG 파라미터 준비
prepare_params_task = PythonOperator(
    task_id='prepare_parameters',
    python_callable=prepare_dag_params,
    dag=dag,
    doc_md="""
    ### DAG 파라미터 준비
    실행 날짜 기반으로 버전 날짜를 생성하고, 환경변수에서 제한값을 읽어옵니다.
    """
)

# 2. Product ID 수집
collect_product_ids = PapermillOperator(
    task_id='collect_product_ids',
    input_nb=str(NOTEBOOKS_DIR / "01_collect_product_ids.ipynb"),
    output_nb=f"/tmp/papermill/map_sync/{{{{ ds }}}}/01_collect_product_ids_{{{{ ts_nodash }}}}.ipynb",
    parameters={
        "limit": "{{ ti.xcom_pull(task_ids='prepare_parameters', key='dag_params')['limit'] }}",
        "version_date": "{{ ti.xcom_pull(task_ids='prepare_parameters', key='dag_params')['version_date'] }}"
    },
    dag=dag,
    doc_md="""
    ### Product ID 수집
    MAP API를 통해 활성화된 상품 ID 리스트를 수집합니다.
    - SQL 쿼리: `SELECT productCode FROM mc_intg_prod WHERE pmSyncYn='Y'`
    - 결과: collected_product_ids 변수에 저장
    """
)

# 3. 상세 정보 수집
collect_product_details = PapermillOperator(
    task_id='collect_product_details',
    input_nb=str(NOTEBOOKS_DIR / "02_collect_product_details.ipynb"),
    output_nb=f"/tmp/papermill/map_sync/{{{{ ds }}}}/02_collect_product_details_{{{{ ts_nodash }}}}.ipynb",
    parameters={
        "collected_product_ids": "{{ ti.xcom_pull(task_ids='collect_product_ids', key='collected_product_ids') or [] }}",
        "collection_summary": "{{ ti.xcom_pull(task_ids='collect_product_ids', key='collection_summary') or {} }}",
        "version_date": "{{ ti.xcom_pull(task_ids='prepare_parameters', key='dag_params')['version_date'] }}",
        "limit": "{{ ti.xcom_pull(task_ids='prepare_parameters', key='dag_params')['limit'] }}"
    },
    dag=dag,
    doc_md="""
    ### 상품 상세 정보 수집
    이전 단계에서 수집한 Product ID 리스트를 기반으로 각 상품의 상세 정보를 병렬로 수집합니다.
    - API 엔드포인트: `/product-meta/basic-plan_.../product-info`
    - 병렬 처리: ThreadPoolExecutor 사용
    - 결과 저장: `mobile_plan_info_YYYYMMDD.json`
    """
)

# 4. 변경사항 감지
detect_changes = PapermillOperator(
    task_id='detect_changes',
    input_nb=str(NOTEBOOKS_DIR / "03_detect_changes.ipynb"),
    output_nb=f"/tmp/papermill/map_sync/{{{{ ds }}}}/03_detect_changes_{{{{ ts_nodash }}}}.ipynb",
    parameters={
        "saved_file_path": "{{ ti.xcom_pull(task_ids='collect_product_details', key='saved_file_path') }}",
        "product_collection_result": "{{ ti.xcom_pull(task_ids='collect_product_details', key='product_collection_result') or {} }}",
        "total_products_collected": "{{ ti.xcom_pull(task_ids='collect_product_details', key='total_products_collected') or 0 }}",
        "version_date": "{{ ti.xcom_pull(task_ids='prepare_parameters', key='dag_params')['version_date'] }}"
    },
    dag=dag,
    doc_md="""
    ### 변경사항 감지
    새로 수집한 데이터와 이전 데이터를 비교하여 새로 추가된 필드만 감지합니다.
    - 비교 대상: 가장 최신 2개 파일 자동 선택
    - 감지 범위: 새로 추가된 필드만 (수정/삭제 제외)
    - 결과 저장: `field_changes_YYYYMMDD.json`, `field_changes_summary_YYYYMMDD.txt`
    """
)

# 5. 동료 작업 실행
colleague_task = PapermillOperator(
    task_id='execute_colleague_task',
    input_nb=str(NOTEBOOKS_DIR / "04_colleague_task.ipynb"),
    output_nb=f"/tmp/papermill/map_sync/{{{{ ds }}}}/04_colleague_task_{{{{ ts_nodash }}}}.ipynb",
    parameters={
        "change_detection_result": "{{ ti.xcom_pull(task_ids='detect_changes', key='change_detection_result') or {} }}",
        "saved_file_path": "{{ ti.xcom_pull(task_ids='collect_product_details', key='saved_file_path') }}",
        "version_date": "{{ ti.xcom_pull(task_ids='prepare_parameters', key='dag_params')['version_date'] }}",
        "colleague_notebook_path": "/path/to/colleague/neo4j_updater.ipynb"  # TODO: 실제 경로로 수정
    },
    dag=dag,
    doc_md="""
    ### 동료 작업 실행
    변경사항이 감지된 경우 동료의 후속 작업(Neo4j 업데이트 등)을 실행합니다.
    - 조건: 변경사항이 임계값 이상일 때만 실행
    - 전달 파라미터: 입력 파일 경로, 변경사항 요약, 버전 날짜 등
    - 실행 방식: Papermill을 통한 동료 노트북 실행
    """
)

# 6. 성공 알림 (선택사항)
def send_success_notification(**context):
    """파이프라인 성공 시 알림 전송"""
    version_date = context['ti'].xcom_pull(task_ids='prepare_parameters', key='dag_params')['version_date']
    
    # 최종 결과 수집
    final_result = context['ti'].xcom_pull(task_ids='execute_colleague_task', key='pipeline_final_result') or {}
    
    print(f"🎉 MAP Product Sync Pipeline 완료!")
    print(f"버전: {version_date}")
    print(f"전체 상태: {final_result.get('overall_status', 'unknown')}")
    
    # 실제 환경에서는 Slack, Email 등으로 알림 전송
    # slack_notification = SlackWebhookOperator(...)
    # email_notification = EmailOperator(...)
    
    return final_result

notify_success = PythonOperator(
    task_id='notify_success',
    python_callable=send_success_notification,
    dag=dag,
    doc_md="""
    ### 성공 알림
    파이프라인이 성공적으로 완료된 경우 팀에 알림을 전송합니다.
    """
)

# 태스크 의존성 설정
prepare_params_task >> collect_product_ids >> collect_product_details >> detect_changes >> colleague_task >> notify_success

# 실패 처리 함수 (선택사항)
def handle_failure(context):
    """DAG 실행 실패 시 처리"""
    task_instance = context['task_instance']
    dag_run = context['dag_run']
    
    print(f"❌ Task {task_instance.task_id} failed in DAG {dag_run.dag_id}")
    print(f"Execution date: {dag_run.execution_date}")
    
    # 실제 환경에서는 오류 상세 정보를 팀에 전송
    # error_notification = SlackWebhookOperator(...)

# 각 태스크에 실패 콜백 설정 (필요시)
for task in dag.tasks:
    if hasattr(task, 'on_failure_callback'):
        task.on_failure_callback = handle_failure