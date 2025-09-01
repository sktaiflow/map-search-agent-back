from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple, List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import Runnable
from app.database.neo4j import Neo4jDatabase
from datetime import datetime
import re


@dataclass
class AsyncGraphCypherQAConfig:
    top_k: int = 10
    return_direct: bool = False
    enforce_read_only: bool = True
    cache_schema_ttl: timedelta = timedelta(minutes=5)


def is_read_only(cypher: str) -> bool:
    """Cypher 쿼리가 READ-ONLY인지 확인"""
    cypher_upper = cypher.upper().strip()
    write_keywords = ['CREATE', 'DELETE', 'SET', 'REMOVE', 'MERGE', 'DROP']
    return not any(keyword in cypher_upper for keyword in write_keywords)


class AsyncGraphCypherQAChain:
    """
    - LLM으로 Cypher 생성 (ainvoke)
    - 네이티브 async Neo4j READ 실행
    - (옵션) 결과를 다시 LLM에 넣어 자연어 답변 생성
    - 세션 관리는 Neo4jDatabase.get_async_session() 컨텍스트로 처리
    """

    def __init__(
        self,
        db: Neo4jDatabase,
        llm: Runnable,
        cfg: Optional[AsyncGraphCypherQAConfig] = None,
    ):
        self.db = db
        self.llm = llm
        self.qa_llm = llm
        self.cfg = cfg or AsyncGraphCypherQAConfig()
        self._schema_cache: Tuple[Optional[str], datetime] = (None, datetime.min)

    def _extract_cypher(self, content: str) -> str:
        """LLM 응답에서 Cypher 쿼리 추출"""
        if "```cypher" in content:
            return content.split("```cypher")[1].split("```")[0].strip()
        elif "```" in content:
            return content.split("```")[1].split("```")[0].strip()
        else:
            return content.strip()

    async def aread(self, session, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Neo4j READ 트랜잭션 실행"""
        params = params or {}
        
        async def _work(tx):
            result = await tx.run(cypher, params)
            records = []
            async for record in result:
                records.append(record.data())
            return records
        
        rows = await session.execute_read(_work)
        return rows

    async def run_read(self, cypher: str) -> List[Dict[str, Any]]:
        """기본 READ 쿼리 실행"""
        async with self.db.get_async_session() as session:
            return await self.aread(session, cypher)

    async def _generate_cypher(self, question: str, schema: str, prompt: str) -> str:
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Graph Schema:\n{schema}\n\nUser Question:\n{question}"),
        ]
        ai: AIMessage = await self.llm.ainvoke(messages)
        cypher = self._extract_cypher(ai.content)

        if self.cfg.enforce_read_only and not is_read_only(cypher):
            raise ValueError(
                "Generated Cypher contains non-read-only clauses. Aborting for safety."
            )
        return cypher

    async def _execute_read(self, cypher: str) -> List[Dict[str, Any]]:
        async with self.db.get_async_session() as session:
            rows = await self.aread(session, cypher, params={})
            if self.cfg.top_k and self.cfg.top_k > 0:
                return rows[: self.cfg.top_k]
            return rows

    async def _get_schema_str(self, refresh: bool = False) -> str:
        """
        PROMPT에 넣을 스키마 문자열 생성.
        - 라벨/관계타입/프로퍼티키를 모아 프롬프트에 넣기 좋은 텍스트로 변환
        - APOC이 있으면 apoc.meta.schema를 우선 시도
        """
        # 캐시 확인
        cached_schema, cache_time = self._schema_cache
        if not refresh and cached_schema and (datetime.now() - cache_time) < self.cfg.cache_schema_ttl:
            return cached_schema
        
        schema_lines = ["# Graph Schema (summary)"]

        try:
            # 1) APOC meta schema 시도
            apoc_schema = await self.run_read("CALL apoc.meta.schema() YIELD * RETURN * LIMIT 20")
            if apoc_schema:
                schema_lines.append("APOC meta.schema sample (limited 20 rows):")
                for row in apoc_schema:
                    schema_lines.append(str(row))
                schema_str = "\n".join(schema_lines)
                self._schema_cache = (schema_str, datetime.now())
                return schema_str
        except Exception as e:
            schema_lines.append(f"(APOC meta.schema 사용 불가, fallback)")

        # 2) Fallback: 기본 시스템 프로시저
        try:
            labels = await self.run_read("CALL db.labels() YIELD label RETURN label")
            rels = await self.run_read(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            )
            props = await self.run_read("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey")

            label_list = ", ".join(sorted([r["label"] for r in labels]))
            rel_list = ", ".join(sorted([r["relationshipType"] for r in rels]))
            prop_list = ", ".join(sorted([r["propertyKey"] for r in props]))

            schema_lines.extend(
                [
                    f"Labels: {label_list or '(none)'}",
                    f"Relationships: {rel_list or '(none)'}",
                    f"PropertyKeys: {prop_list or '(none)'}",
                ]
            )

            # 샘플 노드 모양
            sample_nodes = await self.run_read(
                """
                MATCH (n) WITH labels(n) AS ls, keys(n) AS ks LIMIT 3
                RETURN ls AS labels, ks AS keys
                """
            )
            if sample_nodes:
                schema_lines.append("Sample node shapes (labels, keys):")
                for s in sample_nodes:
                    schema_lines.append(f"- {s['labels']} / {s['keys']}")
        except Exception as e:
            schema_lines.append(f"Schema fallback failed: {str(e)}")

        schema_str = "\n".join(schema_lines)
        self._schema_cache = (schema_str, datetime.now())
        return schema_str

    async def ainvoke(
        self,
        prompt: str,
        question: str,
        *,
        refresh_schema: bool = False,
        return_cypher_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Params
        - refresh_schema: True면 스키마 캐시 무시하고 재생성
        - return_cypher_only: True면 Cypher만 생성해서 반환

        Returns
        {
          "cypher": str,
          "records": List[Dict[str, Any]],
          "result": str (answer)
        }
        """
        schema = await self._get_schema_str(refresh=refresh_schema)
        cypher = await self._generate_cypher(question, schema, prompt)

        if return_cypher_only:
            return {"cypher": cypher, "records": [], "result": ""}

        records = await self._execute_read(cypher)

        if self.cfg.return_direct:
            return {"cypher": cypher, "records": records, "result": records}

        # 후가공 답변
        if records:
            qa_messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Question:\n{question}\n\nResults:\n{records}"),
            ]
            ans_ai: AIMessage = await self.qa_llm.ainvoke(qa_messages)
            return {"cypher": cypher, "records": records, "result": ans_ai.content}
        else:
            return {"cypher": cypher, "records": [], "result": "I don't know the answer."}