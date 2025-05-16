from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_neo4j.chains.graph_qa.cypher import construct_schema
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# from fastapi.responses import StreamingResponse
import sys
from pathlib import Path
from datetime import datetime

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

CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Schema:
{schema}
Domain mapping and other rules::
- '무제한' -> value of includedData -> 999999
- Questions about age should perform a comparative search for MinAge, MaxAge
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


# class ChatRequest(BaseModel):
#     query: str


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
async def chat_completions(request: Request):
    print("Call chat_completions")
    try:
        body = await request.json()
        query = body["messages"][-1]["content"]
        # Neo4j 연결 테스트
        graph = Neo4jGraph(
            url="bolt://graph-db:7687",
            username="neo4j",
            password="neo4jpassword",
            # enhanced_schema=True,
            sanitize=True,  # 연결 검증
        )

        # LangChain 초기화
        chain = GraphCypherQAChain.from_llm(
            ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key="e97ee307-a791-4e06-ade1-df4b9d032eed",
                openai_api_base="https://aihub-api.sktelecom.com/aihub/v2/sandbox",
                streaming=True,
            ),
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            graph=graph,
            verbose=True,
            allow_dangerous_requests=True,
            # validate_cypher=True,
            # return_direct=True
        )

        # 질문 출력
        print("Query:", query)

        # 쿼리 실행
        result = chain.invoke({"query": query})
        print(f"Final answer: {result['result']}")

        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": result["result"]},
                    "finish_reason": "stop",
                }
            ],
        }

    except Exception as e:
        import traceback

        traceback.print_exc()  # 서버 로그에 스택 트레이스 출력
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
