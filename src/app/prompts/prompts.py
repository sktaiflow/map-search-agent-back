def get_planning_prompt(schema: str, **kwargs):
    """
    Planning 프롬프트 템플릿을 반환합니다.
    Args:
        schema: 쿼리 실행에 필요한 스키마 정보
    Returns:
        str: 완성된 프롬프트 템플릿
    """
    objective = kwargs.get("objective", "")

    prompt = f"""
        For the given objective and schema information, come up with a cypher query execution plan.
        This plan should involve individual query generation tasks, that if executed correctly will yield the correct answer.
        Do not add any superfluous steps. The result of the final step should be the final answer.
        Make sure that each step has all the information needed—do not skip steps.
        Answer in Korean.
        
        Schema: {schema}
    """    
    # objective가 있는 경우에만 추가
    if objective:
        prompt += f"\n\nObjective: {objective}"

    return prompt

def get_cypher_generate_prompt(ontology: str, **kwargs):
    """
    Cypher 생성 프롬프트 템플릿을 반환합니다.
    Args:
        ontology: 쿼리 실행에 필요한 온톨로지 정보
    Returns:
        str: 완성된 프롬프트 템플릿
cypher_generate_prompt = """

"""
