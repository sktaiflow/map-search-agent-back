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
- For numeric fields, treat the term 무제한 (unlimited) as the value 999999.
- For age-related queries, check whether the given age is within the range defined by 최소나이 (minimum age) and 최대나이 (maximum age).
- For questions about cheap or expensive plans, sort by the value of VAT포함월정액 (VAT included monthly price).
- Focus primarily on the 마케팅키워드 (marketing keywords) nodes and 상품설명 (product description) fields when finding keywords.

Example:
- "18세 미만만 가입할 수 있는 요금제 알려줘" -> "MATCH (p:요금제)-[:최대가입가능나이]->(maxAge:최대나이) WHERE maxAge.값 < 18 RETURN p, maxAge"
Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.

The question is:
{question}"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

CYPHER_QA_TEMPLATE = """You are a product specialist in SK Telecom helps to form nice and human understandable answers in Korean.
The Information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
You should write your answer based on the 상품명 (product name), 상품설명 (product description), and VAT포함월정액 (monthlyprice) fields, and you can utilize additional fields depending on the question.
Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
If there are more than one product, the result should be a markdown table.
Here is an example:

Question: 데이터 무제한 요금제 하나만 알려줘
Context:'상품설명': '무제한 데이터와 0청년 특화 혜택 외 디즈니 플러스 멤버십을 제공하는 디즈니 플러스 전용 요금제로 SK텔레콤 공식 온라인 채널인 T다이렉트샵에서 만 19세 이상 34세 이하 개인 고객만 가입 가능한 온라인 전용 무약정 요금제', '라인업': '0청년 다이렉트 디즈니+ 요금제', '상품명': '0 청년 다이렉트 69(디즈니+)', 'VAT포함월정액': 69000
Helpful Answer: 데이터 무제한 요금제에는 0 청년 다이렉트 69(디즈니+)가 있고, 해당 요금제의 월정액 요금은 69,000원입니다. 해당 요금제는 무제한 데이터 외에 0청년 특화 혜택과 디즈니 플러스 멤버십을 제공하며, 만 19세 이상 34세 이하 개인 고객만 가입이 가능한 온라인 전용 무약정 요금제입니다.

Follow this example when generating answers.
If the provided information is empty, say that you don't know the answer.
Information:
{context}

Question: {question}
Helpful Answer:"""

CYPHER_QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"], template=CYPHER_QA_TEMPLATE
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
