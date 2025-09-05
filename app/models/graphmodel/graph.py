from app.models.graphmodel.base import BaseAsyncGraphModel
from app.database.neo4j import Neo4jDatabase
from app import logger
from utils.decorators import (
    neo4j_session_required,
)


from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any, LiteralString, Union
from datetime import datetime, timedelta
from utils.timezone import KST

from neo4j import Result, AsyncTransaction, AsyncSession


from neo4j_graphrag.schema import (
    NODE_PROPERTIES_QUERY,
    REL_PROPERTIES_QUERY,
    REL_QUERY,
    INDEX_QUERY,
    SCHEMA_COUNTS_QUERY,
)

from neo4j_graphrag.schema import _clean_string_values, _value_sanitize, format_schema
from neo4j_graphrag.schema import (
    BASE_ENTITY_LABEL,
    BASE_KG_BUILDER_LABEL,
    EXCLUDED_LABELS,
    EXCLUDED_RELS,
    LIST_LIMIT,
    DISTINCT_VALUE_LIMIT,
    EXHAUSTIVE_SEARCH_LIMIT,
)

from neo4j import Query as Neo4jQuery


@dataclass
class GraphModelConfig:
    cache_schema_ttl: timedelta = timedelta(minutes=5)
    timeout: float = 1.0


class AsyncGraphModel(BaseAsyncGraphModel):

    def __init__(self, cfg: GraphModelConfig):
        self._schema_cache: Tuple[Optional[str], datetime] = (
            None,
            datetime.min.replace(tzinfo=KST),
        )
        self.cfg = cfg

    def _extract_cypher(self, content: str) -> str:
        if "```cypher" in content:
            return content.split("```cypher")[1].split("```")[0].strip()
        elif "```" in content:
            return content.split("```")[1].split("```")[0].strip()
        else:
            return content.strip()

    # TODO: is_enhanced 옵션 추가 (조심: 정확히 기존 기능과 똑같이 구현하려면 너무 구현할게 많음, 실험해보고 기존 로직과 다르게 구현하는게 좋아보임)
    async def get_schema(
        self,
        *,
        session: Optional[AsyncSession] = None,
        timeout: Optional[float] = None,
        is_enhanced: bool = False,
        sanitize: bool = True,
    ) -> str:
        if is_enhanced:
            raise ValueError("is_enhanced is not supported yet")

        structured_schema = await self.get_structured_schema(
            session=session,
            is_enhanced=is_enhanced,
            timeout=timeout or self.cfg.timeout,
            sanitize=sanitize,
        )
        return format_schema(structured_schema, is_enhanced)

    async def query_database(
        self,
        query: Union[LiteralString, str],
        *,
        session: Optional[AsyncSession] = None,
        timeout: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
        sanitize: bool = False,
    ):
        result = await self.asession_read(
            session=session,
            cypher=Neo4jQuery(text=query, timeout=timeout or self.cfg.timeout),
            params=params,
        )
        json_data = [r.data() for r in result]
        if sanitize:
            json_data = [_value_sanitize(el) for el in json_data]

        return json_data

    async def get_structured_schema(
        self,
        *,
        session: Optional[AsyncSession] = None,
        is_enhanced: bool = False,
        timeout: Optional[float] = None,
        sanitize: bool = False,
    ):
        node_properties = [
            data.get("output")
            for data in (
                await self.query_database(
                    session=session,
                    query=NODE_PROPERTIES_QUERY,
                    params={
                        "EXCLUDED_LABELS": EXCLUDED_LABELS
                        + [BASE_ENTITY_LABEL, BASE_KG_BUILDER_LABEL]
                    },
                    timeout=timeout or self.cfg.timeout,
                    sanitize=sanitize,
                )
            )
            if "output" in data
        ]

        rel_properties = [
            data.get("output")
            for data in (
                await self.query_database(
                    session=session,
                    query=REL_PROPERTIES_QUERY,
                    params={"EXCLUDED_LABELS": EXCLUDED_RELS},
                    timeout=timeout,
                    sanitize=sanitize,
                )
            )
            if "output" in data
        ]

        relationships = [
            data.get("output")
            for data in (
                await self.query_database(
                    session=session,
                    query=REL_QUERY,
                    params={
                        "EXCLUDED_LABELS": EXCLUDED_LABELS
                        + [BASE_ENTITY_LABEL, BASE_KG_BUILDER_LABEL]
                    },
                    timeout=timeout,
                    sanitize=sanitize,
                )
            )
            if "output" in data
        ]

        try:
            constraint = await self.asession_read(
                cypher=Neo4jQuery(text="SHOW CONSTRAINTS", timeout=timeout)
            )
            index = await self.asession_read(cypher=Neo4jQuery(text=INDEX_QUERY, timeout=timeout))

        except Exception as e:
            constraint = []
            index = []

        structured_schema = {
            "node_props": {el["label"]: el["properties"] for el in node_properties},
            "rel_props": {el["type"]: el["properties"] for el in rel_properties},
            "relationships": relationships,
            "metadata": {"constraint": constraint, "index": index},
        }

        return structured_schema

    # TODO: 람다에서 색인 후 스키마 업데이트 하는 기능 필요 (api etc ...) 없으면 cache_schema_ttl 만료까지 반영 안됨
    async def _get_schema_str(self, refresh: bool = False, timeout: Optional[float] = None) -> str:
        """
        PROMPT에 넣을 스키마 문자열 생성.
        - 라벨/관계타입/프로퍼티키를 모아 프롬프트에 넣기 좋은 텍스트로 변환
        - APOC이 있으면 apoc.meta.schema를 우선 시도
        """
        # 캐시 확인
        cached_schema, cache_time = self._schema_cache
        if (
            not refresh
            and cached_schema
            and (datetime.now() - cache_time) < self.cfg.cache_schema_ttl
        ):
            return cached_schema

        schema_lines = ["# Graph Schema (summary)"]

        try:
            # 1) APOC meta schema 시도
            apoc_schema = await self.asession_read(
                cypher=Neo4jQuery(
                    text="CALL apoc.meta.schema() YIELD value RETURN value",
                    timeout=timeout or self.cfg.timeout,
                )
            )
            if apoc_schema:
                schema_lines.append("APOC meta.schema sample (limited 20 rows):")
                for row in apoc_schema:
                    schema_lines.append(str(row))
                schema_str = "\n".join(schema_lines)
                self._schema_cache = (schema_str, datetime.now(tz=KST))
                return schema_str
        except Exception as e:
            logger.info(f"APOC meta.schema failed", exc_info=e)
            pass

        try:
            labels = await self.asession_read(cypher="CALL db.labels() YIELD label RETURN label")
            rels = await self.asession_read(
                cypher=Neo4jQuery(
                    text="CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType",
                    timeout=timeout or self.cfg.timeout,
                )
            )
            props = await self.asession_read(
                cypher=Neo4jQuery(
                    text="CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey",
                    timeout=timeout or self.cfg.timeout,
                )
            )

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
            sample_nodes = await self.asession_read(
                cypher=Neo4jQuery(
                    text=f"""
                        MATCH (n) WITH labels(n) AS ls, keys(n) AS ks LIMIT 3
                        RETURN ls AS labels, ks AS keys
                    """,
                    timeout=timeout or self.cfg.timeout,
                )
            )

            if sample_nodes:
                schema_lines.append("Sample node shapes (labels, keys):")
                for s in sample_nodes:
                    schema_lines.append(f"- {s['labels']} / {s['keys']}")

        except Exception as e:
            logger.error(f"get schema failed: {str(e)}", exc_info=e)
            self._schema_cache = (None, datetime.now(tz=KST))
            return ""

        schema_str = "\n".join(schema_lines)
        self._schema_cache = (schema_str, datetime.now(tz=KST))
        return schema_str
