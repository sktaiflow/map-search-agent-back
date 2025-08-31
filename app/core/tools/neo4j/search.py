from typing import Dict, Any, List, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from app.core.tools.map.base import BaseToolKit, SafeValidationTool
from app.models.graphmodel.graph import AsyncGraphCypherQAChain
import asyncio
import time
import json


class Neo4jSearchInput(BaseModel):
    query: str = Field(description="검색할 사용자 쿼리")
    expand_search: bool = Field(description="case1(False): 정확매치, case2(True): 조건완화", default=True)


class Neo4jSearchOutput(BaseModel):
    search_strategy: str = Field(description="case_1 또는 case_2")
    total_queries: int = Field(description="실행된 쿼리 수")
    query_results: List[Dict[str, Any]] = Field(description="각 쿼리별 상세 결과")
    aggregated_products: List[Dict[str, Any]] = Field(description="통합된 상품 정보")
    total_products: int = Field(description="총 상품 수")


class Neo4jSearchTool(SafeValidationTool):
    name = "neo4j_product_search"
    description = "Neo4j 데이터베이스에서 상품 정보 검색 (case1: 정확매치, case2: 조건완화)"
    response_model: Type[BaseModel] = Neo4jSearchOutput
    
    def __init__(self, cypher_qa_chain: AsyncGraphCypherQAChain):
        super().__init__()
        self.cypher_qa_chain = cypher_qa_chain
    
    async def _decompose_query_for_case2(self, user_query: str) -> List[Dict[str, str]]:
        """case2용 쿼리 분해 전략"""
        strategies = [
            {"type": "exact_match", "query": user_query},
        ]
        
        # 가격 조건 완화
        price_keywords = ["저렴한", "비싼", "싼", "고가", "프리미엄"]
        if any(keyword in user_query for keyword in price_keywords):
            relaxed_query = user_query
            for keyword in price_keywords:
                relaxed_query = relaxed_query.replace(keyword, "")
            strategies.append({"type": "relaxed_price", "query": relaxed_query.strip()})
        
        # 카테고리 완화 (첫 번째 키워드만)
        words = user_query.split()
        if len(words) > 1:
            strategies.append({"type": "relaxed_category", "query": words[0]})
        
        # 키워드 추출 (2글자 이상만)
        keywords = [w for w in words if len(w) > 1]
        if len(keywords) > 1:
            strategies.append({"type": "keyword_based", "query": " ".join(keywords)})
        
        return strategies
    
    async def _execute_single_query(self, query_config: Dict[str, str]) -> Dict[str, Any]:
        """단일 쿼리 실행"""
        start_time = time.time()
        
        try:
            result = await self.cypher_qa_chain.ainvoke(
                prompt="사용자 질의에 맞는 상품 정보를 Neo4j에서 검색하세요.",
                question=query_config["query"]
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return {
                "query_type": query_config["type"],
                "cypher": result.get("cypher", ""),
                "results": result.get("records", []),
                "result_count": len(result.get("records", [])),
                "execution_time_ms": execution_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return {
                "query_type": query_config["type"],
                "cypher": "",
                "results": [],
                "result_count": 0,
                "execution_time_ms": execution_time,
                "success": False,
                "error": str(e)
            }
    
    async def _arun(self, query: str, expand_search: bool = True) -> str:
        """툴 실행 메인 함수"""
        if expand_search:
            # case2: 다중 쿼리 실행
            query_configs = await self._decompose_query_for_case2(query)
            results = await asyncio.gather(*[
                self._execute_single_query(config) for config in query_configs
            ])
            
            # 결과 집계 및 중복 제거
            all_products = []
            seen_ids = set()
            
            for result in results:
                for product in result["results"]:
                    product_id = product.get("id") or product.get("product_id") or str(product)
                    if product_id and product_id not in seen_ids:
                        all_products.append(product)
                        seen_ids.add(product_id)
            
            search_result = {
                "search_strategy": "case_2",
                "total_queries": len(results),
                "query_results": results,
                "aggregated_products": all_products,
                "total_products": len(all_products)
            }
        else:
            # case1: 단일 쿼리 실행
            query_config = {"type": "exact_match", "query": query}
            result = await self._execute_single_query(query_config)
            
            search_result = {
                "search_strategy": "case_1",
                "total_queries": 1,
                "query_results": [result],
                "aggregated_products": result["results"],
                "total_products": result["result_count"]
            }
        
        return json.dumps(search_result, ensure_ascii=False)


class Neo4jToolKit(BaseToolKit):
    """Neo4j 검색 툴킷"""
    
    def __init__(self, cypher_qa_chain: AsyncGraphCypherQAChain, status: bool = True):
        self.cypher_qa_chain = cypher_qa_chain
        self.status = status
    
    def get_tools(self) -> List[BaseTool]:
        """Neo4j 검색 툴 반환"""
        neo4j_tool = Neo4jSearchTool(self.cypher_qa_chain)
        neo4j_tool.status = self.status
        return [neo4j_tool]