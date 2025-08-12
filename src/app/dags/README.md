# MAP Product Data Sync - Airflow Edition

MAP API에서 상품 데이터를 수집하고, 이전 데이터와 비교하여 **새로 추가된 필드만** 감지하는 Airflow DAG 기반 파이프라인입니다.

## 🏗️ 구조

```
data_sync/
├── dags/
│   └── map_product_sync_dag.py     # Airflow DAG 정의
├── notebooks/
│   ├── 01_collect_product_ids.ipynb    # Product ID 수집
│   ├── 02_collect_product_details.ipynb # 상세 정보 수집  
│   ├── 03_detect_changes.ipynb         # 변경사항 감지
│   └── 04_colleague_task.ipynb         # 동료 작업 연동
├── config.py                       # 공통 설정
└── requirements.txt               # Airflow + Papermill 의존성
```

## 🚀 실행 플로우

### 1. **Product ID 수집** (`01_collect_product_ids.ipynb`)
```sql
SELECT productCode FROM mc_intg_prod WHERE pmSyncYn='Y'
```
- MAP API 쿼리 실행
- 활성화된 상품 ID 리스트 수집
- 다음 단계로 XCom 전달

### 2. **상세 정보 수집** (`02_collect_product_details.ipynb`)
- 각 Product ID에 대해 상세 정보 API 호출
- `ThreadPoolExecutor`로 병렬 처리 (최대 10개 동시)
- `mobile_plan_info_YYYYMMDD.json` 파일로 저장

### 3. **변경사항 감지** (`03_detect_changes.ipynb`)
- 자동으로 최신 2개 파일 비교
- **새로 추가된 필드만** 감지 (`change_type: "added"`)
- JSON + 텍스트 요약 결과 저장

### 4. **수집 데이터 전처리** (`04_colleague_task.ipynb`)
- 신규 스키마 추가 내용 없을시 실행 (Neo4j 업데이트 대상을 생성하기 위한 전처리 작업)

## 📅 Airflow 스케줄

- **실행 시간**: 매일 오전 2시
- **동시 실행**: 방지 (`max_active_runs=1`)
- **재시도**: 실패 시 5분 후 1회 재시도
- **알림**: 실패 시 이메일 알림

