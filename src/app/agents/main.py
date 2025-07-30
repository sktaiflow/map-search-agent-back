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

                        # ✅ JSON 본문 라인 단위 출력 (큰 데이터만 필터링)
                        # 작은 데이터는 그대로 표시, 큰 데이터만 요약
                        filtered_state = {}
                        
                        # 작은 데이터들은 그대로 포함
                        small_data_fields = ['input', 'plan', 'current_step', 'status']
                        for key in small_data_fields:
                            if key in node_state:
                                if key == 'input' and len(str(node_state[key])) > 100:
                                    filtered_state[key] = str(node_state[key])[:100] + "..."
                                else:
                                    filtered_state[key] = node_state[key]
                        
                        # 큰 데이터들만 요약으로 대체
                        if 'product_meta' in node_state:
                            product_count = len(node_state['product_meta']) if isinstance(node_state['product_meta'], list) else 0
                            filtered_state['product_meta'] = f"[{product_count}개 검색 결과]"
                        
                        if 'past_steps' in node_state:
                            filtered_state['past_steps'] = f"[{len(node_state['past_steps'])}개 완료된 단계]"
                        
                        if 'reasoning' in node_state:
                            filtered_state['reasoning'] = "[추론 과정 있음]"
                        
                        if 'response' in node_state:
                            filtered_state['response'] = "[최종 응답 생성됨]"
                        
                        if 'raw_results' in node_state:
                            filtered_state['raw_results'] = "[원시 결과 데이터]"
                        
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
                                    # 1단계: 원본 데이터 (OpenWebUI 표시용 문자열 길이 제한)
                                    raw_data = response_data.get('raw_data', [])
                                    
                                    # 전체 JSON을 우선 생성
                                    full_json = json.dumps(raw_data, ensure_ascii=False, indent=2)
                                    
                                    # 2000자 이하로 제한
                                    if len(full_json) > 2000:
                                        # 아이템을 하나씩 줄여가며 2000자 이하가 될 때까지 자르기
                                        if isinstance(raw_data, list):
                                            for i in range(len(raw_data), 0, -1):
                                                truncated_data = raw_data[:i]
                                                truncated_json = json.dumps(truncated_data, ensure_ascii=False, indent=2)
                                                if len(truncated_json) <= 2000:
                                                    raw_data_json = truncated_json + f"\n\n... (총 {len(raw_data)}개 중 {i}개만 표시됨)"
                                                    break
                                            else:
                                                # 아이템 1개도 2000자를 넘는 경우
                                                raw_data_json = full_json[:2000] + f"\n\n... (문자열이 잘림, 총 {len(raw_data)}개 아이템)"
                                        else:
                                            # 리스트가 아닌 경우 그냥 자르기
                                            raw_data_json = full_json[:2000] + "\n\n... (문자열이 잘림)"
                                    else:
                                        raw_data_json = full_json
                                    
                                    # 2단계: 단순 요약
                                    summary = response_data.get('summary', '요약이 없습니다.')
                                    
                                    # 3단계: 인사이트
                                    insights = response_data.get('insights', '인사이트가 없습니다.')
                                    
                                    # Cypher 쿼리 추출
                                    cypher_query = ""
                                    if 'past_steps' in node_state:
                                        # past_steps에서 prod_meta_search 결과 찾기
                                        for step in node_state.get('past_steps', []):
                                            if step.get('tool') == 'prod_meta_search':
                                                # step의 result에서 cypher 정보 추출
                                                step_result = step.get('result', {})
                                                if isinstance(step_result, dict) and 'cypher' in step_result:
                                                    actual_cypher = step_result['cypher']
                                                    if actual_cypher:
                                                        cypher_query = actual_cypher
                                                        break
                                                # 백업: query args에서 검색어 추출
                                                elif isinstance(step.get('query'), dict) and 'query' in step['query']:
                                                    search_query = step['query']['query']
                                                    cypher_query = f"검색 쿼리: '{search_query}'\n(실제 생성된 Cypher는 로그 참조)"
                                                    break
                                    
                                    cypher_section = f"\n\n**🔍 생성된 Cypher 쿼리:**\n```cypher\n{cypher_query}\n```" if cypher_query else ""
                                    
                                    final_content = f"""
**🎯 인사이트 및 추천:**
{insights}

**📝 검색 결과 요약:**
{summary}{cypher_section}

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