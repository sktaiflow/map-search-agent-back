from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_neo4j.chains.graph_qa.cypher import construct_schema
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from fastapi.responses import StreamingResponse, JSONResponse
import sys
from pathlib import Path
from datetime import datetime
from src.app.agents.search_agent import app as agent_workflow
import asyncio
import json
import re

app = FastAPI()

sys.path.append(str(Path(__file__).resolve().parent.parent))

# origins = [
#     "http://openwebui-container:8080",  # 컨테이너 이름 기준
#     "http://localhost:8080"     # 로컬 테스트용
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 허용할 오리진
    # allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 모든 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)
MAX_CHUNK_SIZE = 2048 * 1024  # 2MB
CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Schema:
{schema}

Domain mapping and other rules:
- "무제한"과 관련있는 값은 전부 999999로 치환하였음
- 나이 제약 사항이 있는 요금제 -> 나이 비교 검색 필요
- 저렴한 요금제 알려줘 -> 가장 낮은 가격 순으로 소팅

Example:
- "18세 미만만 가입할 수 있는 요금제 알려줘" -> "MATCH (p:Plan)-[:HAS_maxAge]->(maxAge:MaxAge) WHERE maxAge.value < 18 RETURN p"
Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.

The question is:
{question}"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

# class Request(BaseModel):
#     query: str


@app.get("/v1")
def read_root():
    return {"msg": "ok"}


@app.get("/v1/models")
async def get_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "map-agent",
                "object": "model",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def agent_endpoint(request: Request):
    body = await request.json()
    query = body["messages"][-1]["content"]
    stream = body.get("stream", False)
    if not query:
        raise HTTPException(status_code=400, detail="input field is required")
    inputs = {"input": query}

    if stream:

        async def event_stream():
            async for event in agent_workflow.astream(inputs):
                for node_name, node_result in event.items():
                    # 최종 답변(plain text)만 따로 처리
                    if (
                        isinstance(node_result, dict)
                        and "response" in node_result
                        and node_name in ("replan", "agent")
                    ):
                        content = node_result["response"]
                    elif isinstance(node_result, (dict, list)):
                        content = f"[{node_name}]\n```json\n{json.dumps(node_result, ensure_ascii=False, indent=2)}\n```"
                    else:
                        content = f"[{node_name}] {str(node_result)}"
                    chunk = {
                        "choices": [
                            {
                                "delta": {"content": content + "\n"},
                                "index": 0,
                                "finish_reason": None,
                            }
                        ]
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'choices': [{'delta': {}, 'index': 0, 'finish_reason': 'stop'}]})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    else:
        last_message = None
        async for event in agent_workflow.astream(inputs):
            if "response" in event.get("replan", {}):
                last_message = event["replan"]["response"]
            elif "response" in event.get("agent", {}):
                last_message = event["agent"]["response"]
        if last_message is None:
            raise HTTPException(status_code=500, detail="No response generated")
        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": "gpt-4o-0513",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": last_message},
                    "finish_reason": "stop",
                }
            ],
        }


@app.post("/v1/chat/stream")
async def agent_stream_endpoint(request: Request):
    body = await request.json()
    query = body["messages"][-1]["content"]
    if not query:
        raise HTTPException(status_code=400, detail="input field is required")
    inputs = {"input": query}

    async def event_stream():
        async for event in agent_workflow.astream(inputs):
            for node_name, node_result in event.items():
                # 단계별로 node와 result를 스트리밍
                yield f"data: {json.dumps({'node': node_name, 'result': node_result}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def safe_json_pretty(obj):
    # 문자열이면 파싱해서 dict/list로 변환
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except Exception:
            pass
    return json.dumps(obj, ensure_ascii=False, indent=2)


def deep_json_parse(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                try:
                    obj[k] = json.loads(v)
                except Exception:
                    pass
            elif isinstance(v, (dict, list)):
                obj[k] = deep_json_parse(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                try:
                    obj[i] = json.loads(v)
                except Exception:
                    pass
            elif isinstance(v, (dict, list)):
                obj[i] = deep_json_parse(v)
    return obj


def strip_codeblock(text):
    # 모든 마크다운 코드블록(```...```)을 제거하고 내부 텍스트만 남김
    return re.sub(r"```[a-zA-Z]*\n([\s\S]*?)\n```", lambda m: m.group(1), text, flags=re.MULTILINE)
