class GraphInitError(RuntimeError):
    """그래프 초기화(프리워밍) 단계에서의 일반 오류"""


class GraphSchemaEmptyError(GraphInitError):
    """empty schema"""
