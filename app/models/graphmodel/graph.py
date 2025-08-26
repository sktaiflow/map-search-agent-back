from app.models.graphmodel.base import BaseGraphModel
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple, List, Dict, Any
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.schema.runnable import Runnable
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import Runnable
from app.database.neo4j import Neo4jDatabase
from datetime import datetime, timedelta


@dataclass
class AsyncGraphCypherQAConfig:
    top_k: int = 10
    return_direct: bool = False
    enforce_read_only: bool = True
    cache_schema_ttl: timedelta = timedelta(minutes=5)


class AsyncGraphCypherQAChain(BaseGraphModel):
    """
    - LLM으로 Cypher 생성 (ainvoke)
    - 네이티브 async Neo4j READ (BaseGraphModel.aread + Async 트랜잭션)
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

    # TODO: 파싱로직
    def _extract_cypher(self, content: str) -> str:
        return content.split("```cypher")[1].split("```")[0].strip()

    async def _generate_cypher(self, question: str, schema: str, prompt: str) -> str:
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Graph Schema:\n{schema}\n\nUser Question:\n{question}"),
        ]
        ai: AIMessage = await self.llm.ainvoke(messages)
        cypher = extract_cypher(ai.content)

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
          "answer": Optional[str]
        }
        """
        schema = await self._get_schema(refresh=refresh_schema)
        cypher = await self._generate_cypher(question, schema)

        if return_cypher_only or self.cfg.return_direct:
            # 실행 없이 Cypher만 보고 싶거나, 실행 결과만 바로 반환하고 싶을 때
            if return_cypher_only:
                return {"cypher": cypher, "records": [], "answer": None}

        records = await self._execute_read(cypher)

        if self.cfg.return_direct:
            return {"cypher": cypher, "records": records, "answer": None}

        # 후가공 답변
        qa_messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Question:\n{question}\n\nResults:\n{records}"),
        ]
        ans_ai: AIMessage = await self.qa_llm.ainvoke(qa_messages)
        return {"cypher": cypher, "records": records, "answer": ans_ai.content}
