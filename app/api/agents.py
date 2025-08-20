from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict

from app.container import Container
from app.agents.map_search_agent import MapSearchAgent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/test")
@inject
async def test_agent_injection(
    agent_factory: Dict[str, MapSearchAgent] = Depends(Provide[Container.agents.factory])
):
    """DI가 제대로 작동하는지 테스트하는 엔드포인트"""
    try:
        available_agents = list(agent_factory.keys())
        return {
            "message": "DI injection successful",
            "available_agents": available_agents
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DI injection failed: {str(e)}")


@router.get("/agent/{agent_name}")
@inject
async def get_agent_info(
    agent_name: str,
    agent_factory: Dict[str, MapSearchAgent] = Depends(Provide[Container.agents.factory])
):
    """특정 에이전트 정보 조회"""
    if agent_name not in agent_factory:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agent_factory[agent_name]
    return {
        "agent_name": agent.config.agent_name,
        "agent_class": agent.__class__.__name__,
        "graph_class": agent.graph.__class__.__name__
    }