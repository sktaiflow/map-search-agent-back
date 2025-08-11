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

### 4. **동료 작업 연동** (`04_colleague_task.ipynb`)
- 변경사항 있으면 동료 노트북 실행 (Neo4j 업데이트 등)
- Papermill로 파라미터 전달
- Mock/실제 실행 모드 지원

## 📅 Airflow 스케줄

- **실행 시간**: 매일 오전 2시
- **동시 실행**: 방지 (`max_active_runs=1`)
- **재시도**: 실패 시 5분 후 1회 재시도
- **알림**: 실패 시 이메일 알림

## 🛠️ 설정

### 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `MAP_API_BASE_URL` | MAP API 기본 URL | `https://api.map-stg.sktelecom.com` |
| `MAP_API_KEY` | MAP API 인증 키 | `vdFXmlw8DqSimAmysgojBVoXE34C3pDw` |
| `API_TIMEOUT` | API 타임아웃 (초) | `30` |
| `DATALOAD_DIR` | 데이터 저장 디렉토리 | `./notebooks/dataload/` |
| `MAX_WORKERS` | 병렬 처리 최대 워커 수 | `10` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |
| `PRODUCT_LIMIT` | 수집 제한 (테스트용) | `None` |
| `MIN_CHANGES_THRESHOLD` | 동료 작업 실행 최소 변경 임계값 | `1` |

### Airflow 변수

```bash
# 테스트 실행 시 상품 수 제한
airflow variables set PRODUCT_LIMIT 100

# 동료 노트북 경로 설정
airflow variables set COLLEAGUE_NOTEBOOK_PATH "/path/to/neo4j_updater.ipynb"
```

## 🚀 배포 및 실행

### 1. Airflow 환경에 배포

```bash
# DAG 파일 복사
cp dags/map_product_sync_dag.py $AIRFLOW_HOME/dags/

# 노트북 파일 복사 
cp -r notebooks/ $AIRFLOW_HOME/notebooks/

# 의존성 설치
pip install -r requirements.txt
```

### 2. DAG 활성화

```bash
# Airflow UI에서 활성화 또는
airflow dags unpause map_product_sync
```

### 3. 수동 실행 (테스트)

```bash
# 특정 날짜로 실행
airflow dags trigger map_product_sync --execution-date 2024-08-07
```

## 📊 모니터링

### Airflow UI
- **DAG Graph**: 각 단계별 실행 상태 확인
- **Logs**: 각 노트북 실행 로그 확인  
- **XCom**: 단계 간 전달 데이터 확인

### Papermill 결과
- 실행된 노트북: `/tmp/papermill/map_sync/YYYY-MM-DD/`
- 각 노트북에서 중간 결과물, 차트, 에러 메시지 시각적 확인

## 📁 출력 파일

### 수집 데이터
```
./notebooks/dataload/mobile_plan_info_20240807.json
```

### 변경사항 분석
```
./notebooks/dataload/field_changes_20240807.json
./notebooks/dataload/field_changes_summary_20240807.txt
```

## 🔧 개발 팁

### 로컬에서 노트북 테스트

```bash
# 개별 노트북 실행
papermill notebooks/01_collect_product_ids.ipynb output.ipynb \
  -p limit 10 \
  -p version_date 20240807

# 노트북 체인 실행
jupyter nbconvert --execute notebooks/01_collect_product_ids.ipynb
```

### 동료 노트북 연동
`04_colleague_task.ipynb`에서 `colleague_notebook_path` 변수를 실제 경로로 수정:

```python
colleague_notebook_path = "/path/to/colleague/neo4j_updater.ipynb"
```

## 🎯 장점

1. **시각적 디버깅**: 노트북으로 중간 과정 확인 가능
2. **모듈화**: 각 단계가 독립적인 노트북
3. **재사용성**: Papermill 파라미터로 유연한 실행
4. **확장성**: 새 노트북 추가로 파이프라인 확장 쉬움
5. **협업**: 동료 작업과 자연스러운 연동