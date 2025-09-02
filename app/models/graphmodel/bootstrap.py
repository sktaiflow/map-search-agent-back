"""
Neo4j schema bootstrap utilities.

해당 파일은 아래의 기능을 수행하기 위해 제작

# TODO : 현재는 기본 필수 체크 부분만 구현 필요시 나머지 넣는 작업 필요

실행 시점: app.container.init_resources() #/app/container/db.py 참고

Neo4j 스키마 초기화: 앱 시작 시 Neo4j DB 스키마 설정
연결 검증: Neo4j 드라이버 연결 상태 확인 (RETURN 1 AS ok)
스키마 요소 생성:
    제약조건 (Constraints): 데이터 무결성 보장
    인덱스 (Indexes): 쿼리 성능 최적화
    전문검색 (Fulltext): 텍스트 검색 기능
    벡터 인덱스 (Vector): 임베딩 검색용
"""

from neo4j import AsyncDriver
from app import logger
from typing import Any, Mapping, Sequence


CONSTRAINTS: Sequence[str] = ()
INDEXES: Sequence[str] = ()
FULLTEXT: Sequence[str] = ()
VECTOR: Sequence[tuple[str, Mapping[str, Any]]] = ()


async def _run_stmt(
    driver: AsyncDriver,
    cypher: str,
    params: Mapping[str, Any] | None = None,
    *,
    timeout: float = 3.0,
):
    async with driver.session() as s:
        res = await s.run(cypher, params or {}, timeout=timeout)
        await res.consume()


async def bootstrap_schema(driver: AsyncDriver) -> None:
    logger.info("Bootstrapping Neo4j schema...")

    # 0) ping [필수 체크]
    await _run_stmt(driver, "RETURN 1 AS ok")

    if CONSTRAINTS:
        for c in CONSTRAINTS:
            try:
                await _run_stmt(driver, c)
            except Exception as e:
                logger.error(message="Constraint error: %s (%s)", exec_info=e)

    if INDEXES:
        for i in INDEXES:
            try:
                await _run_stmt(driver, i)
            except Exception as e:
                logger.error(message="Index error: %s (%s)", exec_info=e)

    if FULLTEXT:
        for f in FULLTEXT:
            try:
                await _run_stmt(driver, f)
            except Exception as e:
                logger.error(message="Fulltext index error: %s (%s)", exec_info=e)

    logger.info("Neo4j schema bootstrap completed.")
