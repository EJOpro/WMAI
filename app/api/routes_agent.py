"""
Agent API 라우터
LangGraph 기반 챗봇 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

router = APIRouter(tags=["agent"])

# 세션 저장소 (메모리 기반)
conversation_sessions = {}


class AgentChatRequest(BaseModel):
    """Agent 채팅 요청 모델"""
    query: str = Field(..., description="사용자 질문", min_length=1)
    session_id: Optional[str] = Field(None, description="세션 ID (없으면 자동 생성)")


class AgentChatResponse(BaseModel):
    """Agent 채팅 응답 모델"""
    answer: str = Field(..., description="Agent 응답")
    tool_used: str = Field(..., description="사용된 도구 이름")
    tool_id: Optional[str] = Field(None, description="도구 ID")
    action_type: str = Field(default="view", description="액션 타입 (view/execute)")
    execution_data: Optional[Dict[str, Any]] = Field(None, description="실행 명령 데이터")
    page_url: Optional[str] = Field(None, description="이동할 페이지 URL")
    session_id: str = Field(..., description="세션 ID")


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Agent 채팅 엔드포인트
    
    - 사용자 질문을 분석하여 적절한 도구 선택
    - 도구 실행 후 결과를 자연어로 답변
    - 필요시 페이지 이동 URL 반환
    """
    try:
        # Agent 로드 (지연 로딩)
        from agent_back.agent_core import get_agent
        agent = get_agent()
        
        # 세션 ID 생성 또는 가져오기
        session_id = request.session_id or str(uuid.uuid4())
        
        # 세션 메시지 가져오기
        if session_id not in conversation_sessions:
            conversation_sessions[session_id] = {
                "messages": [],
                "created_at": datetime.now().isoformat()
            }
        
        session_messages = conversation_sessions[session_id]["messages"]
        
        # Agent 실행
        result = agent.chat(request.query, session_messages)
        
        # 세션에 메시지 추가
        from langchain_core.messages import HumanMessage, AIMessage
        conversation_sessions[session_id]["messages"].append(HumanMessage(content=request.query))
        conversation_sessions[session_id]["messages"].append(AIMessage(content=result["answer"]))
        
        return AgentChatResponse(
            answer=result["answer"],
            tool_used=result["tool_used"],
            tool_id=result.get("tool_id"),
            action_type=result.get("action_type", "view"),
            execution_data=result.get("execution_data"),
            page_url=result.get("page_url"),
            session_id=session_id
        )
        
    except Exception as e:
        print(f"[ERROR] Agent 실행 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent 실행 중 오류 발생: {str(e)}")


@router.delete("/agent/session/{session_id}")
async def clear_session(session_id: str):
    """세션 초기화"""
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
        return {"message": "세션이 초기화되었습니다.", "session_id": session_id}
    return {"message": "세션을 찾을 수 없습니다.", "session_id": session_id}


@router.get("/agent/health")
async def agent_health():
    """Agent 상태 확인"""
    try:
        from agent_back.agent_core import get_agent
        agent = get_agent()
        
        return {
            "status": "ok",
            "agent": "LangGraph Community Agent",
            "tools": ["semantic_search", "churn_analysis", "ethics_check", "match_reports", "trends_analysis"],
            "sessions": len(conversation_sessions)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

