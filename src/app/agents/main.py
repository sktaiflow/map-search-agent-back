import json
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.app.agents.logging_config import setup_logging
from src.app.agents.search_agent import app as agent_workflow
from src.app.tools.tool_registry import tool_registry  # ✅ 필수

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False


@app.post("/v1/chat/completions")
async def agent_endpoint(request: ChatCompletionRequest):
    query = request.messages[-1].content
    stream = request.stream
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    inputs = {"input": query}

    if stream:
        async def event_stream(inputs: Dict[str, Any]):
            final_state = None
            try:
                async for event in agent_workflow.astream(inputs):
                    for node_name, node_state in event.items():
                        # ✅ 섹션 헤더 + 코드블럭 오픈
                        header_chunk = {
                            "id": f"chunk-{node_name}-start",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "role": "assistant",
                                    "content": f"\n[{node_name}]\n```json\n"
                                },
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(header_chunk)}\n\n"

                        # ✅ JSON 본문 라인 단위 출력 (큰 데이터 필터링)
                        filtered_state = {k: v for k, v in node_state.items() 
                                        if k not in ['product_meta', 'raw_results']}
                        # 큰 데이터는 요약 정보만 표시
                        if 'product_meta' in node_state:
                            filtered_state['product_meta'] = f"[{len(node_state['product_meta'])} items]"
                        if 'raw_results' in node_state:
                            filtered_state['raw_results'] = "[filtered for display]"
                        
                        pretty_json = json.dumps(filtered_state, ensure_ascii=False, indent=2)
                        for line in pretty_json.splitlines():
                            line_chunk = {
                                "id": f"chunk-{node_name}-line",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": request.model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "role": "assistant",
                                        "content": line + "\n"
                                    },
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(line_chunk)}\n\n"

                        # ✅ 코드블럭 닫기
                        footer_chunk = {
                            "id": f"chunk-{node_name}-end",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "role": "assistant",
                                    "content": "```"
                                },
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(footer_chunk)}\n\n"

                    final_state = event

                # ✅ 최종 응답 표시
                if final_state:
                    logger.info(f"📊 final_state 키들: {list(final_state.keys())}")
                    
                    # final_state 전체 구조 디버깅
                    if 'final_response' in final_state:
                        logger.info(f"🔧 final_response 노드 키들 상세: {list(final_state['final_response'].keys())}")
                        if 'reasoning' in final_state['final_response']:
                            logger.info(f"🔧 reasoning 내용: {final_state['final_response']['reasoning'][:100]}...")
                        if 'raw_results' in final_state['final_response']:
                            logger.info(f"🔧 raw_results 내용: {final_state['final_response']['raw_results']}")
                    
                    # 모든 노드의 상태를 확인하여 response가 있는지 찾기
                    final_response_found = False
                    for node_name, node_state in final_state.items():
                        logger.info(f"🔍 노드 '{node_name}' 타입: {type(node_state)}")
                        if isinstance(node_state, dict):
                            logger.info(f"🔍 노드 '{node_name}' 키들: {list(node_state.keys())}")
                            
                            if "response" in node_state:
                                logger.info(f"✅ 최종 응답 발견! 노드: {node_name}")
                                logger.info(f"🔍 node_state 키들: {list(node_state.keys())}")
                                logger.info(f"🔍 reasoning 존재: {'reasoning' in node_state}")
                                logger.info(f"🔍 raw_results 존재: {'raw_results' in node_state}")
                                
                                response_data = node_state['response']
                                logger.info(f"🔍 response 타입: {type(response_data)}")
                                
                                # 3단계 구조 응답 처리
                                if isinstance(response_data, dict):
                                    # 1단계: 원본 데이터
                                    raw_data = response_data.get('raw_data', [])
                                    raw_data_json = json.dumps(raw_data, ensure_ascii=False, indent=2)
                                    if len(raw_data_json) > 2000:
                                        raw_data_json = raw_data_json[:2000] + "...\n(결과가 잘렸습니다)"
                                    
                                    # 2단계: 단순 요약
                                    summary = response_data.get('summary', '요약이 없습니다.')
                                    
                                    # 3단계: 인사이트
                                    insights = response_data.get('insights', '인사이트가 없습니다.')
                                    
                                    final_content = f"""
**🎯 인사이트 및 추천:**
{insights}

**📝 검색 결과 요약:**
{summary}

**📊 원본 데이터:**
```json
{raw_data_json}
```

**🤔 추론 과정:**
{node_state.get('reasoning', '추론 정보 없음')}"""
                                else:
                                    # 레거시 호환
                                    final_content = f"""
**🎯 최종 답변:**
{response_data}

**🤔 추론 과정:**
{node_state.get('reasoning', '추론 정보 없음')}"""
                                
                                final_chunk = {
                                    "id": "chatcmpl-final",
                                    "object": "chat.completion.chunk", 
                                    "created": int(time.time()),
                                    "model": request.model,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {
                                            "role": "assistant",
                                            "content": final_content
                                        },
                                        "finish_reason": "stop"
                                    }]
                                }
                                yield f"data: {json.dumps(final_chunk)}\n\n"
                                final_response_found = True
                                break
                        else:
                            logger.info(f"🔍 노드 '{node_name}'는 dict가 아님: {type(node_state)}")
                    
                    if not final_response_found:
                        logger.warning("❌ 최종 응답을 찾을 수 없습니다!")
                        # 전체 구조 출력
                        logger.info(f"📋 전체 final_state 구조:")
                        for node_name, node_state in final_state.items():
                            logger.info(f"  - {node_name}: {type(node_state)}")
                            if isinstance(node_state, dict):
                                for key in node_state.keys():
                                    logger.info(f"    - {key}: {type(node_state[key])}")
                else:
                    logger.error("💥 final_state가 None이거나 비어있습니다!")

                # 스트림 종료 신호
                yield "data: [DONE]\n\n"

            except Exception as e:
                error_chunk = {
                    "id": "chatcmpl-error",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": f"오류가 발생했습니다: {str(e)}"
                        },
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(inputs), media_type="text/event-stream")

    else:
        return {
            "choices": [
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