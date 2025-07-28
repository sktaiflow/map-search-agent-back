# src/app/tools/tool_registry.py

import logging
from typing import Any, Callable, Dict, List

# 도구 함수들을 각 파일에서 import 합니다.
from src.app.tools.prod_meta_tools import prod_meta_search
from src.app.tools.user_tools import get_service_info, get_subscribed_products

# 이 모듈을 위한 로거 설정
logger = logging.getLogger(__name__)

# 도구 정보를 담고 있는 레지스트리 (기존 구조 유지)
# 각 도구는 'func' (실행할 함수)와 'args' (필요한 인자 이름 목록)를 가집니다.
tool_registry: Dict[str, Dict[str, Any]] = {
    "prod_meta_search": {
        "func": prod_meta_search,
        "args": ["query"]
    },
    "get_service_info": {
        "func": get_service_info,
        "args": ["svc_mgmt_num"]
    },
    "get_subscribed_products": {
        "func": get_subscribed_products,
        "args": ["svc_mgmt_num"]
    }
    # 새로운 도구를 추가할 경우, 여기에 같은 형식으로 추가하면 됩니다.
}


def resolve_tool(tool_name: str, args: Dict[str, Any]) -> Any:
    """
    도구 이름과 인자를 받아 tool_registry에서 해당 도구를 찾아 실행하고 결과를 반환합니다.
    이 함수는 순환 참조를 방지하기 위해 tool_registry와 함께 위치합니다.

    Args:
        tool_name (str): 실행할 도구의 이름입니다.
        args (Dict[str, Any]): 도구에 전달할 인자입니다.

    Returns:
        Any: 도구 실행 결과입니다.

    Raises:
        ValueError: tool_registry에 해당 도구가 없거나 필수 인자가 누락된 경우 발생합니다.
    """
    logger.info(f"도구 실행 요청: {tool_name}, 인자: {args}")

    # 1. 레지스트리에서 도구 정보 확인
    if tool_name not in tool_registry:
        available_tools = list(tool_registry.keys())
        error_message = f"'{tool_name}'은(는) 유효한 도구가 아닙니다. 사용 가능한 도구: {available_tools}"
        logger.error(error_message)
        raise ValueError(error_message)

    tool_info = tool_registry[tool_name]
    tool_func: Callable = tool_info["func"]
    required_args: List[str] = tool_info["args"]

    # 2. 필수 인자 확인
    # 'args'가 None인 경우를 대비하여 빈 딕셔너리로 처리
    provided_args = args or {}
    for arg_name in required_args:
        if arg_name not in provided_args:
            error_message = f"'{tool_name}' 도구 실행에 필수 인자 '{arg_name}'이(가) 누락되었습니다."
            logger.error(error_message)
            raise ValueError(error_message)

    # 3. 도구 실행
    try:
        # LangChain의 @tool 데코레이터로 생성된 도구는 .invoke() 메소드를 사용합니다.
        # 'args'가 여러 개일 수 있으므로 딕셔너리 전체를 전달합니다.
        result = tool_func.invoke(provided_args)
        logger.info(f"'{tool_name}' 도구 실행 완료. 결과: {result}")
        return result
    except Exception as e:
        logger.exception(f"'{tool_name}' 도구 실행 중 에러 발생: {e}")
        # 에러를 다시 발생시켜 상위 호출자가 처리하도록 함
        raise
