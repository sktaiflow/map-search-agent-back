"""
Neo4j 통합 검색 툴

자연어 쿼리를 받아서 임베딩 → Few-shot 검색 → Cypher 생성 → Neo4j 실행까지
전체 파이프라인을 하나의 고수준 툴로 제공
"""

import json
import re
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app import logger
from app.core.prompts import CYPHER_GENERATION_PROMPT
from app.core.tools.base import StandardizedTool
from app.database.neo4j import Neo4jDatabase
from app.database.postgresql import PostgreSQLDatabase
from app.llms.embedding_llm_http import OpenAIEmbeddingModel
from app.llms.llm_http import OpenAIChatLLM
from app.models.graphmodel.graph import AsyncGraphModel
from app.models.vectorstore.semantic_retrieval import SemanticSearchModel
from app.schemas.cypher import CypherResponse, Neo4jSearchRequest
from configs.default import BaseConfig
from neo4j.graph import Node, Relationship


class CypherDecomposer:
    """Cypher 쿼리 분해 클래스 - case2용 조건 완화 검색"""

    def __init__(self, llm: OpenAIChatLLM, cfg: BaseConfig):
        self.llm = llm
        self.cfg = cfg

    def _match_to_where(self, cypher: str):
        """MATCH 절의 속성값 조건을 WHERE 절로 옮기기"""
        conds = []

        # MATCH 절에서 조건 추출
        for alias, props in re.findall(r"\((\w+)[^{}]*\{([^}]+)\}\)", cypher):
            for part in props.split(","):
                if ":" in part:
                    key, val = part.split(":", 1)
                    conds.append(f"{alias}.{key.strip()} = {val.strip()}")

        # {...} 부분 제거
        cypher = re.sub(r"\s*\{[^}]*\}", "", cypher)

        # WHERE 절 추가
        if conds:
            where_clause = "WHERE " + " AND ".join(conds)
            if "WHERE" in cypher.upper():
                cypher = re.sub(
                    r"(?i)\bWHERE\b", where_clause + " AND ", cypher, count=1
                )
            else:
                # RETURN 앞에 WHERE 삽입
                cypher = re.sub(
                    r"(?i)\b(RETURN|ORDER)\b", where_clause + r" \1", cypher, count=1
                )

        return cypher

    async def decompose(self, original_question: str, base_cypher: str) -> List[str]:
        """원본 Cypher 쿼리를 분해하여 조건을 하나씩 제거한 서브쿼리들 생성"""
        # 전처리 (MATCH 절의 속성 필터를 WHERE 절로 이동)
        refined_cypher = self._match_to_where(base_cypher.strip())

        # 프롬프트 구성
        system_message = (
            "You are an expert Cypher generator. "
            "Given an original question and a Cypher query that found no results, "
            "generate valid Cypher sub-queries by removing exactly one filtering condition in each. "
            "IMPORTANT RULES:\n"
            "- Keep the exact same MATCH pattern structure\n"
            "- Only remove conditions from WHERE clause, never modify MATCH clause\n"
            "- When removing a condition about node property (e.g. p.`상품명`), keep it as p.`상품명`\n"
            "- When removing a condition about different node property (e.g. h.`혜택명`), keep it as h.`혜택명`\n"
            "- Do NOT change node aliases or property references\n"
            "- Do NOT move properties between different nodes\n"
            "- Change the number in 'LIMIT' clause to the MAX(10, original_limit_number * 2)\n"
            "Return ONLY a JSON array of the Cypher strings."
            "{'queries': [<cypher1>, <cypher2>, ...]}"
        )

        user_message = (
            f"Original question: {original_question}\n"
            f"Failed Cypher: {refined_cypher}"
            # "Generate sub-queries by removing one condition each time."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        try:
            # LLM 호출
            llm_response = await self.llm.agenerate_response(
                messages=messages,
                model=self.cfg.llm_model,
                temperature=0.0,
                max_tokens=1000,
                response_format={"type": "json_object"},
                seed=0,
            )

            # JSON 파싱
            content = (llm_response.message or "").strip()
            sub_queries = json.loads(content).get("queries", [])
            return sub_queries if isinstance(sub_queries, list) else []

        except json.JSONDecodeError as e:
            logger.error(f"JSON 디코딩 에러: {e}")
            return []
        except Exception as e:
            logger.error(f"CypherDecomposer 오류: {e}")
            return []


class Neo4jSearchTool(StandardizedTool):
    """
    Neo4j 통합 검색 툴

    자연어 쿼리를 받아서 다음 파이프라인을 수행:
    1. 쿼리 임베딩 생성
    2. 유사한 Few-shot 예제 검색
    3. Few-shot 기반 Cypher 쿼리 생성
    4. Neo4j에서 Cypher 실행
    5. 실패시 조건 완화 검색 (case 2)
    """

    name: str = "neo4j_search"
    description: str = (
        "요금제, 할인 혜택 등의 상품 정보에 대한 검색 질의를 처리합니다."
        "상품에 대한 정보를 찾고자 할 때 호출되어야 하는 도구입니다."
    )
    args_schema: Any = Neo4jSearchRequest
    response_model: Any = CypherResponse
    status: bool = True

    # 의존성 주입될 컴포넌트들
    llm: OpenAIChatLLM
    llm_embedding: OpenAIEmbeddingModel
    neo4j_db: Neo4jDatabase
    postgres_db: PostgreSQLDatabase
    graphmodel: AsyncGraphModel
    vectormodel: SemanticSearchModel
    cfg: BaseConfig

    async def _arun(
        self,
        query: str,
        expand_search: bool = True,
        return_type: int | None = None,
        tool_select_reason: str = "",
    ) -> Dict[str, Any]:
        """
        Neo4j 검색 파이프라인 실행 (원본 map-search-agent 로직)

        Args:
            query: 자연어 검색 쿼리
            expand_search: 검색 실패시 조건 완화 검색 수행 여부
            return_type: 응답 형태(정확 검색/확장 검색 임계값 판단 용도)
            tool_select_reason: 이 툴을 선택한 이유와 얻고자 하는 결과

        Returns:
            검색 결과 (case 1: 정확매치, case 2: 조건완화)
        """
        start_time = time.time()

        try:
            # 1. 임베딩 생성
            embedding = await self._embed_query(query)

            # 2. Few-shot 예제 검색
            fewshot_examples = await self._retrieve_fewshot_examples(
                embedding, return_type=return_type
            )

            # 3. Cypher 생성
            cypher_payload = await self._generate_cypher(query, fewshot_examples)

            cypher_text = ""
            cypher_params: Dict[str, Any] = {}
            if isinstance(cypher_payload, dict):
                raw_cypher = cypher_payload.get("cypher")
                if isinstance(raw_cypher, str):
                    cypher_text = raw_cypher.strip()
                params_candidate = cypher_payload.get("params")
                if isinstance(params_candidate, dict):
                    cypher_params = params_candidate

            if not cypher_text:
                raise ValueError("Cypher 생성에 실패했습니다")

            # 4. Cypher 실행 (Case 1: 기본 검색)
            raw_result = await self._execute_cypher(cypher_text, params=cypher_params)
            execution_time = int((time.time() - start_time) * 1000)

            # Case 1: 기본 검색 성공
            if raw_result and raw_result.get("data") and len(raw_result["data"]) > 0:
                response = {
                    "case": "1",
                    "cypher": cypher_text,
                    "data": raw_result["data"],
                    "message": "검색 성공",
                    "record_count": len(raw_result["data"]),
                    "execution_time": execution_time,
                }
                return self._validate_response(response)

            # Case 2: 검색 실패시 조건 완화 검색 적용 (expand_search=True인 경우만)
            if expand_search:
                # CypherDecomposer를 사용하여 조건 분해
                decomposer = CypherDecomposer(llm=self.llm, cfg=self.cfg)
                sub_queries = await decomposer.decompose(
                    original_question=query, base_cypher=cypher_text
                )

                # sub_queries에 있는 cypher들을 각각 실행해보고 결과 수집
                cypher_results = []
                for sub_cypher in sub_queries:
                    try:
                        sub_result = await self._execute_cypher(sub_cypher)
                        sub_data = sub_result.get("data", []) if sub_result else []
                        cypher_results.append(sub_data)
                    except Exception as e:
                        logger.error(f"서브쿼리 실행 실패: {e}")
                        cypher_results.append([])

                total_execution_time = int((time.time() - start_time) * 1000)

                # cypher_results를 평탄화하여 data로 변환
                flattened_data = []
                for result_list in cypher_results:
                    flattened_data.extend(result_list)

                response = {
                    "case": "2",
                    "cypher": sub_queries,  # 리스트!
                    "data": flattened_data,
                    "message": "조건 완화 검색 수행",
                    "record_count": len(flattened_data),
                    "execution_time": total_execution_time,
                }
                return self._validate_response(response)

            # expand_search=False인데 실패한 경우
            else:
                response = {
                    "case": "1",
                    "cypher": cypher,
                    "data": [],
                    "message": "검색 결과가 없습니다.",
                    "record_count": 0,
                    "execution_time": execution_time,
                }
                return self._validate_response(response)

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Neo4j 검색 실패: {str(e)}", exc_info=e)
            response = {
                "case": "1",
                "cypher": "",
                "data": [],
                "message": f"검색 실행 중 오류 발생: {str(e)}",
                "record_count": 0,
                "execution_time": execution_time,
            }
            return self._validate_response(response)

    async def _embed_query(self, query: str) -> List[float]:
        """
        자연어 쿼리를 벡터 임베딩으로 변환

        Few-shot 예제 검색을 위해 쿼리의 의미적 벡터 표현 생성
        """
        embedding_obj = await self.llm_embedding.aembed(text=query)
        return embedding_obj.embeddings[0]

    async def _retrieve_fewshot_examples(
        self, embedding: List[float], return_type: int | None = None
    ) -> str:
        """
        임베딩을 기반으로 유사한 Few-shot 예제 검색

        PostgreSQL의 벡터 데이터베이스에서 의미적으로 유사한
        query-cypher 쌍을 찾아서 프롬프트에 사용할 문자열로 변환
        """
        threshold_map = {1: 0.8, 2: 0.5}
        similarity_threshold = threshold_map.get(return_type, 0.8)

        async with self.postgres_db.get_async_session() as session:
            retrieved_examples = await self.vectormodel.asearch_by_vector(
                session=session,
                embedding=embedding,
                similarity_cutoff=similarity_threshold,
            )

        # few-shot 예제가 없는 경우 유사도 임계값 무시하고 가져오기
        # TODO: 이럴 때 가져올 기본 예제 선택하는 로직을 추가해도 좋을 듯
        if not retrieved_examples and similarity_threshold > 0.0:
            async with self.postgres_db.get_async_session() as session:
                retrieved_examples = await self.vectormodel.asearch_by_vector(
                    session=session,
                    embedding=embedding,
                    similarity_cutoff=0.0,
                )

        examples_text = []
        for few_shot_example, score in retrieved_examples:
            examples_text.append(
                few_shot_example.cypher_query
                # f"Query: {few_shot_example.query}\n"
                # f"Cypher: {few_shot_example.cypher_query}\n"
                # f"Score: {score:.3f}"
            )

        return "\n".join(examples_text)

    async def _generate_cypher(
        self, query: str, fewshot_examples: str
    ) -> Dict[str, Any]:
        """
        자연어 쿼리와 Few-shot 예제를 기반으로 Cypher 쿼리 생성

        LLM을 사용해서 Neo4j 스키마와 Few-shot 예제를 참고하여
        사용자 질문에 맞는 Cypher 쿼리를 자동 생성
        """
        # Neo4j 스키마 정보 가져오기 (세션 컨텍스트 보장)
        async with self.neo4j_db.get_async_session(mode="r") as session:
            graph_schema = await self.graphmodel.get_schema(session=session)

        # 프롬프트 구성
        prompt = CYPHER_GENERATION_PROMPT.partial(
            schema=graph_schema, question=query, fewshot_examples=fewshot_examples
        )
        system_message = prompt.format()

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": query},
        ]

        # LLM 호출
        llm_response = await self.llm.agenerate_response(
            messages=messages,
            model=self.cfg.llm_model,
            temperature=0.0,
            max_tokens=500,
            response_format={"type": "json_object"},
            seed=0,
        )
        content = (llm_response.message or "").strip()
        if not content:
            logger.warning("Cypher 생성 LLM 응답이 비어 있습니다.")
            return {}

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            logger.error("Cypher 생성 응답 JSON 파싱 실패", exc_info=error)
            return {}

        if isinstance(parsed, dict):
            return parsed

        logger.warning("Cypher 생성 응답이 dict 형태가 아닙니다.")
        return {}

    async def _execute_cypher(
        self, cypher: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        생성된 Cypher 쿼리를 Neo4j에서 실행

        Args:
            cypher: 실행할 Cypher 쿼리문

        Returns:
            실행 결과를 CypherResponse 형태로 변환한 딕셔너리
        """
        # Neo4j에서 쿼리 실행 (세션 컨텍스트 보장)
        async with self.neo4j_db.get_async_session(mode="r") as session:
            raw_result = await self.graphmodel.execute_read_tx(
                session=session,
                cypher=cypher,
                params=params or {},
            )

        # TODO: raw_result는 List[Record] 형태이므로 각 Record를 필요한 형태로 변환
        # - 한 가지 노드만 있을 경우
        #   - label을 속성처럼 포함시키고 속성(data()나 properties()로 추출한 값)을 나열
        # - 노드/관계가 있을 경우
        #   - 노드-관계-노드 구조를 유지하는 새로운 JSON 형식을 정의하고, 그에 맞게 변환
        #   - 한 가지 노드만 있을 경우와 호환성이 있도록 설계해야함

        # 결과를 표준 형태로 변환
        if raw_result:
            if isinstance(raw_result, list):
                return {
                    "data": self.format_records(raw_result),
                    "message": "검색 성공",
                    "record_count": len(raw_result),
                }
            else:
                return {
                    "data": self.format_records([raw_result]) if raw_result else [],
                    "message": "검색 성공",
                    "record_count": 1 if raw_result else 0,
                }

    def format_records(self, records):
        result = []
        for record in records:
            for value in record.values():
                if isinstance(value, Node):  # Node 객체인 경우
                    node_data = {
                        "label": list(value.labels)[0] if value.labels else None,
                        "properties": dict(value.items()),
                    }
                    result.append(node_data)
                elif isinstance(value, Relationship):  # Relationship 객체
                    result.append(
                        {
                            "type": "relationship",
                            "start": value.start_node.id,
                            "end": value.end_node.id,
                            "rel_type": value.type,
                            "properties": dict(value.items()),
                        }
                    )
                else:  # 스칼라 값 같은 기타 항목
                    result.append({"type": "value", "value": value})
        return result
