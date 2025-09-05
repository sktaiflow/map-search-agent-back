from typing import Any, Dict, List


# TODO: 추후 구현 필요
def split_query(query: str) -> List[str]:
    """동의어 API 호출하기위한 키워드 자르는 method"""
    return query.split(",")


# TODO: 현재 단순 concat ','
def concat_query(query: List[str]):
    """List[str] -> str"""
    return ",".join(query)


async def preprocess_synonyms(product_id: str):
    """product_id 기반으로 상품 정보 조회"""
    pass


async def retrieval_query(user_input):
    pass


async def postprocess_synonyms(response: Dict[str, Any]):
    pass
