from langchain_openai import ChatOpenAI
from langchain_ollama.chat_models import ChatOllama
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import SystemMessage
from langchain_neo4j import Neo4jGraph


def message_to_dict(message):
    """Convert various message formats to a standardized dictionary format."""
    if hasattr(message, "to_dict"):
        return message.to_dict()
    elif isinstance(message, dict):
        result = message.copy()
        if "content" not in result:
            result["content"] = ""
        return result
    if message.type.title().lower() == "human":
        role = "user"
        return {"role": role, "content": message.content}
    elif message.type.title().lower() == "ai":
        role = "assistant"
        return {"role": role, "content": message.content}
    elif message.type.title().lower() == "system":
        role = "system"
        return {"role": role, "content": message.content}
    elif message.type.title().lower() == "function" or message.type.title().lower() == "tool":
        role = "assistant"
        return {"role": role, "name": message.name, "content": message.content}
    else:
        print("message.type.title()>>>>", message.type.title())
        raise ValueError("message.type.title()>>>>", message.type.title())


def call_ollama(
    messages: list,
    system_message: str,
    tools: list = None,
    seed: int = 0,
    tool_choice: str = "auto",
    format: str = None,
):
    """
    Call the Llama API for chat completions using LangChain's invoke method

    Args:
        messages: Conversation messages
        system_message: System message
        tools: List of available tools
        model_idx: Model identifier
        seed: Random seed
        tool_choice: Tool selection mode
        response_format: Desired response format

    Returns:
        dict: API response

    Raises:
        ValueError: If API call fails or returns invalid response
    """
    # Process system message same way as in call_pe_tool_v2
    if system_message:
        if len(messages) > 0 and messages[0].type.title().lower() == "system":
            messages[0].content = system_message
        else:
            messages.insert(0, SystemMessage(content=system_message))
    # Serialize messages
    serialized_messages = [message_to_dict(msg) for msg in messages]
    # Prepare model kwargs and options for invoke
    model_kwargs = {}
    invoke_kwargs = {}
    # Handle tools and tool_choice
    if tools:
        model_kwargs["tools"] = tools
        invoke_kwargs["tool_choice"] = tool_choice
    # # Handle response_format
    # if response_format:
    #     invoke_kwargs["response_format"] = response_format

    try:
        # Initialize LangChain OpenAI client
        llm = ChatOllama(
            base_url="http://host.docker.internal:11434",
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            temperature=0,
            model="llama3.1:8b",
            format="json",
            **model_kwargs
        )
        
        # Call API via LangChain with additional parameters
        response = llm.invoke(messages)
        return response
    except Exception as e:
        raise ValueError(f"API 오류: {str(e)}")

def call_pe_tool_v2(
    messages: list,
    system_message: str,
    tools: list = None,
    model_idx: int = 124252,  # 124730(4.1)
    seed: int = 0,
    tool_choice: str = "auto",
    response_format: str = None,
):
    """
    Call the PE Tool V2 API for chat completions using LangChain's invoke method

    Args:
        messages: Conversation messages
        tools: List of available tools
        model_idx: Model identifier
        seed: Random seed
        tool_choice: Tool selection mode
        response_format: Desired response format

    Returns:
        dict: API response

    Raises:
        ValueError: If API call fails or returns invalid response
    """
    # Process system message same way as in call_pe_tool_v2
    if system_message:
        if len(messages) > 0 and messages[0].type.title().lower() == "system":
            messages[0].content = system_message
        else:
            messages.insert(0, SystemMessage(content=system_message))
    # Serialize messages
    serialized_messages = [message_to_dict(msg) for msg in messages]
    # Prepare model kwargs and options for invoke
    model_kwargs = {}
    invoke_kwargs = {}
    # Handle tools and tool_choice
    if tools:
        model_kwargs["tools"] = tools
        invoke_kwargs["tool_choice"] = tool_choice
    # Handle response_format
    if response_format:
        invoke_kwargs["response_format"] = response_format

    try:
        # print("serialized_messages>>>>", serialized_messages, flush=True)
        # Initialize LangChain OpenAI client
        llm = ChatOpenAI(
            base_url="https://aide.dev.apollo-lunar.com/pe-proxy/api/v1/compatible/openai/stream",
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            temperature=0,
            model=str(model_idx),
            api_key="None",
            seed=seed,
            # **model_kwargs,
        )
        # Call API via LangChain with additional parameters
        if tools:
            llm_with_tools = llm.bind_tools(tools)
            response = llm_with_tools.invoke(serialized_messages, **invoke_kwargs)
            # print("response_with_tools>>>>", response, flush=True)
        else:
            response = llm.invoke(serialized_messages, **invoke_kwargs)
            # print("response>>>>", response, flush=True)
        return response
    except Exception as e:
        raise ValueError(f"API 오류: {str(e)}")


def call_smartbee():
    """미구현"""
    pass


def tool_to_openai_function(tool_obj):
    args = tool_obj.args
    properties = {}
    required = []
    for k, v in args.items():
        properties[k] = {
            "type": v.get("type"),
            "description": v.get("description"),
        }
        if "default" not in v or v["default"] is None:
            required.append(k)
    return {
        "type": "function",
        "function": {
            "name": tool_obj.name,
            "description": tool_obj.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
        "strict": True,
    }


def neo4j_connect(env: str = "openwebui", enhanced_schema: bool = False):
    url = "bolt://neo4j-gds-apoc-n10s:7687" if env == "openwebui" else "bolt://localhost:7687"
    graph = Neo4jGraph(
        url=url,
        username="neo4j",
        password="neo4jpassword",
        enhanced_schema=enhanced_schema,
        sanitize=True,  # 연결 검증
    )
    return graph
