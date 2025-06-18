from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.app.agents.search_agent import app as agent_workflow
import json
import logging
from src.app.agents.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 허용할 오리진
    # allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 모든 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    # temperature: Optional[float] = 1.0
    # top_p: Optional[float] = 1.0
    # n: Optional[int] = 1
    # max_tokens: Optional[int] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@app.post("/v1/chat/completions")
async def agent_endpoint(request: ChatCompletionRequest):
    query = request.messages[-1].content
    stream = request.stream
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
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
        return {
            "choices":[
                {
                    "index": 0, 
                    "message": {
                        "role": "assistant", 
                        "content": "This is a static response\nNon-streaming mode is not implemented yet."
                    }
                }
            ], 
            "id": "chatcmpl-123", 
            "object": "chat.completion", 
            "created": 1234567890, 
            "model": request.model, 
            "usage": {
                "prompt_tokens": 10, 
                "completion_tokens": 20, 
                "total_tokens": 30
            }
        }

@app.get("/v1/models")
async def get_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "map-agent",
                "object": "model"
            }
        ]
    }
