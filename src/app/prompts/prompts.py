from src.app.agents.schema import GraphState
from src.app.agents.utils import call_smartbee


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


## Translation question to prompt Node
def optimize_prompt(state: GraphState) -> GraphState:
    """
    Optimize User Prompt for Python Code Generation.
    Args:
        state (GraphState): The current graph state.
    Returns:
        GraphState: Updated state with new generation.
    """
    print("## STEP 1: OPTIMIZE PROMPT")
    # State
    messages = state["messages"]
    iterations = state["iterations"]

    SYSTEM_PROMPT = """You are a coding assistant specialized in Python programming and problem solving tasks with coding.
        Structure your answer in the following format:
        ---
        prompt: <Optimized code code generation user prompt to answer user question>
        reason: <Justification on optimization of coding logic in python to solve user question>
        ---
   """
    ## extract question
    if len(messages) == 1:
        question = messages[0]["content"]
    ## creater user prompt
    USER_PROMPT = f"""Optimize following user prompt for generation of clean python coding logic to solve user question.\n
        If you need to use any external libraries, include a comment at the top of the code listing the required pip installations\n
        Provide justification why your response can solve the user question with step by step coding logic .\n\n
        
        USER QUESTION:\n {question}\n\n
        
        Respond only with one best user problem optimized prompt and reason for coding logic.\n
        Ensure generate code include main function to run the code.\n
   """

    print("### STEP 1.1: User Question:", question)
    print("### STEP 1.2: User Prompt:", USER_PROMPT)
    user_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]

    try:
        llm_response = call_smartbee(
            system_message=SYSTEM_PROMPT,
            messages=user_messages,
            tools=[],
            response_format={"type": "json_object"},
        )
        code_response = llm_response.choices[0].message
        ## structure response
        if code_response.parsed:
            print("### STEP 1.3: LLM Optimized Prompt")
            print(code_response.parsed.prompt)
            print("### STEP 1.4: LLM Justification")
            print(code_response.parsed.reason)
        elif code_response.refusal:
            print("### STEP 1.5: LLM Refusal")
            print(code_response.refusal)
    except Exception as e:
        print("### STEP 1.6: Error")
        print(f"<LLM Error>: {e}")

    ## code generation prompts
    CODEGEN_SYSTEM_PROMPT = """You are a coding assistant specialized in Python code generator. Respond only with complete executable Python code, no explanations or comments except for required pip installations at the top.\n
        If you need to use any external libraries, include a comment at the top of the code listing the required pip installations.\n
        Structure your answer in the following format:
        ---
        Task: <description of the solution>
        Imports: <required import statements>
        Code: <executable code block>
        ---
   """
    OPTIMIZED_USER_PROMPT = f"""
        {code_response.parsed.prompt}\n\n
        Reason: {code_response.parsed.reason}\n\n
    """
    user_messages = [
        {"role": "system", "content": CODEGEN_SYSTEM_PROMPT},
        {"role": "user", "content": OPTIMIZED_USER_PROMPT},
    ]
    print("### STEP 1.7: Save Optimized Prompt")
    # Increment
    iterations = iterations + 1
    return {"generation": "", "messages": user_messages, "iterations": 0, "error": ""}
