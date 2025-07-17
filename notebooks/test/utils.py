import json
import logging
import time

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import SystemMessage
from langchain_neo4j import Neo4jGraph
from langchain_ollama.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

logging.basicConfig(level=logging.INFO)


def call_ollama(
    messages: list,
    system_message: str,
    tools: list = None,
    seed: int = 0,
    tool_choice: str = "auto",
    format: str = None,
):
    if system_message:
        if len(messages) > 0 and messages[0].type.title().lower() == "system":
            messages[0].content = system_message
        else:
            messages.insert(0, SystemMessage(content=system_message))

    serialized_messages = [message_to_dict(msg) for msg in messages]

    model_kwargs = {}
    invoke_kwargs = {}
    if tools:
        model_kwargs["tools"] = tools
        invoke_kwargs["tool_choice"] = tool_choice

    try:
        llm = ChatOllama(
            base_url="http://host.docker.internal:11434",
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            temperature=0,
            model="llama3.1:8b",
            format="json",
            **model_kwargs
        )

        response = llm.invoke(messages)
        return response
    except Exception as e:
        raise ValueError(f"API 오류: {str(e)}")


def call_llm_with_retries(
    llm,
    messages,
    *,
    expect_json=False,
    max_retries=3,
    sleep_sec=1
):
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(messages)
            print(f"[attempt]{attempt} : {response}")
            if isinstance(response, str):
                raw_content = response.strip()
            elif isinstance(response, dict):
                raw_content = json.dumps(response)
            elif hasattr(response, "content"):
                raw_content = response.content.strip()
            elif hasattr(response, "text"):
                raw_content = response.text.strip()
            elif hasattr(response, "kwargs") and "content" in response.kwargs:
                raw_content = response.kwargs["content"].strip()
            else:
                raise TypeError(f"🤔 예상치 못한 응답 타입: {type(response)}, 내용: {repr(response)}")

            logging.info(f"\n[call_llm_with_retries] Attempt {attempt}:")

            if not raw_content:
                print("⚠️ 빈 응답입니다. 재시도합니다...")
                time.sleep(sleep_sec)
                continue

            if expect_json:
                cleaned = raw_content
                print(f"[cleaned]{cleaned}")
                if cleaned.startswith("```"):
                    cleaned = "\n".join(
                        line for line in cleaned.splitlines()
                        if not line.strip().startswith("```")
                    )
                return json.loads(cleaned)
            else:
                return raw_content

        except Exception as e:
            logging.info(f"❌ 예외 발생 (Attempt {attempt}): {e}")
            last_exception = e
            time.sleep(sleep_sec)
            continue

    raise ValueError(f"❌ LLM이 유효한 응답을 {max_retries}회 시도했으나 받지 못했습니다. 마지막 에러: {last_exception}")


def call_smartbee(
    messages: list,
    system_message: str,
    tools: list = None,
    tool_choice: str = "auto",
    response_format: dict = None,
    llm=None,
    expect_json=True
):
    llm_default = ChatOpenAI(
        model="gpt-4o",
        openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
        temperature=0,
    )
    if system_message:
        if len(messages) > 0 and messages[0].type.title().lower() == "system":
            messages[0].content = system_message
        else:
            messages.insert(0, SystemMessage(content=system_message))

    llm = llm or llm_default

    if tools:
        llm = llm.bind_tools(tools)
        if tool_choice:
            llm = llm.with_config({"tool_choice": tool_choice})
    if response_format:
        llm = llm.with_config({"response_format": response_format})

    return call_llm_with_retries(
        llm,
        messages,
        expect_json=expect_json,
    )


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
        sanitize=True,
    )
    return graph