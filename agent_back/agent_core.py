"""
LangGraph Agent 코어 로직
ReAct 패턴 기반 에이전트
"""

import os
import re
import json
from typing import Annotated, List, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from agent_back.agent_tools import AGENT_TOOLS
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('.env')  # .env 파일 로드
load_dotenv('config.env', override=True)  # config.env를 우선적으로 로드
load_dotenv('match_config.env')  # 추가 설정


class AgentState(TypedDict):
    """Agent 상태 정의"""
    messages: Annotated[list, add_messages]
    tools_used: List[str]


class CommunityAgent:
    """커뮤니티 Agent 클래스"""
    
    def __init__(self, openai_api_key: str = None):
        """
        Agent 초기화
        
        Args:
            openai_api_key: OpenAI API 키 (None이면 config.env에서 로드)
        """
        # API 키 우선순위: 1) 파라미터 2) config.env의 OPENAI_API_KEY
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. "
                "config.env 파일에 OPENAI_API_KEY를 설정하세요."
            )
        
        # LLM 초기화
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            openai_api_key=api_key
        )
        
        # 도구 바인딩
        self.llm_with_tools = self.llm.bind_tools(AGENT_TOOLS)
        
        # Agent 그래프 생성
        self.graph = self._create_graph()
        
        print("[OK] LangGraph Community Agent 초기화 완료")
    
    def _create_graph(self):
        """Agent 그래프 생성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self._execute_tools)
        
        # 엔트리 포인트
        workflow.set_entry_point("agent")
        
        # 조건부 엣지
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        
        # tools 노드 후 다시 agent로
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def _call_model(self, state: AgentState):
        """LLM 호출 (Thought 단계)"""
        messages = state["messages"]
        
        # 시스템 메시지 추가
        system_message = SystemMessage(content="""당신은 커뮤니티 관리 AI 어시스턴트입니다.

사용 가능한 도구:
1. semantic_search_tool: 게시글/댓글 의미 기반 검색
2. churn_analysis_tool: 사용자 이탈 분석 실행
3. ethics_check_tool: 비윤리/스팸 분석 조회
4. match_reports_tool: 신고 통계 조회
5. trends_analysis_tool: 트렌드 키워드 분석 조회
6. execute_churn_analysis_tool: 이탈 분석 실행 (고급 옵션)
7. execute_ethics_analysis_tool: 비윤리/스팸 분석 실행
8. approve_report_tool: 신고 승인
9. reject_report_tool: 신고 거부
10. filter_reports_tool: 신고 목록 필터링
11. board_navigation_tool: 게시판 필터링/정렬/페이지 이동
12. board_detail_tool: 게시글 상세 조회
13. board_filter_tool: 게시판 카테고리 필터링
14. board_page_tool: 게시판 페이지 이동
15. daily_report_tool: 일일 보고서 생성 (신고 현황, 비윤리/스팸 통계, 이탈률, 트렌드)

게시판 조작 명령 예시:
- "육아 관련 글 보여줘" → semantic_search_tool("육아") 사용
- "자유게시판만 보여줘" → board_filter_tool(category="free") 사용
- "인기순으로 정렬해줘" → board_navigation_tool(action="sort", sort_by="popular") 사용
- "다음 페이지 보여줘" → board_navigation_tool(action="page", page=2) 사용
- "3페이지로 가줘" → board_page_tool(page=3) 사용
- "첫 번째 글 자세히 보여줘" → board_detail_tool(relative_position="첫번째") 사용
- "두 번째 글 전체 내용 보기" → board_detail_tool(relative_position="두번째") 사용
- "게시글 5번 상세보기" → board_detail_tool(post_id=5) 사용

**중요: 게시글 상세보기 명령**
사용자가 "자세히", "상세", "전체 내용", "상세보기", "세부 내용" 등의 키워드를 사용하면:
- board_detail_tool을 사용하여 왼쪽 패널에 모달로 표시
- relative_position: "첫번째", "두번째", "세번째", "네번째", "다섯번째" 등
- 또는 post_id로 특정 게시글 지정 가능

실행 명령 예시:
- "이탈률 알려줘" → churn_analysis_tool 사용
- "이탈 분석해줘" → churn_analysis_tool 사용
- "최근 3개월 이탈 분석 실행" → execute_churn_analysis_tool(period_months=3) 사용
- "이 텍스트 비윤리 분석해줘" → execute_ethics_analysis_tool 사용
- "id #18 승인해줘" → approve_report_tool(report_id=18) 사용
- "신고 25번 거부" → reject_report_tool(report_id=25) 사용
- "대기중 신고 보여줘" → filter_reports_tool(status="대기중") 사용
- "승인된 신고 확인" → filter_reports_tool(status="승인") 사용
- "거부된 신고 보여줘" → filter_reports_tool(status="거부") 사용
- "전체 신고 보기" → filter_reports_tool(status="전체") 사용

일일 보고서 명령 예시:
- "오늘의 할일 보여줘" → daily_report_tool 사용
- "일일 보고서 보여줘" → daily_report_tool 사용
- "오늘의 업무 현황은?" → daily_report_tool 사용
- "데일리 리포트" → daily_report_tool 사용

도구 사용 가이드:
- 검색: semantic_search_tool로 의미 기반 검색 후 왼쪽 패널에 게시판 표시
- 조회: 기존 데이터/통계를 보여주는 것
- 실행: 새로운 분석을 수행하거나 액션을 취하는 것
- 필터링: 목록의 표시 상태를 변경하는 것
- 게시판 조작: 현재 표시된 게시판의 필터링, 정렬, 페이지 이동 등

사용자 질문을 분석하고 적절한 도구를 선택하세요.
도구 실행 결과를 바탕으로 친절하고 명확한 답변을 제공하세요.
항상 한국어로 답변하세요.""")
        
        full_messages = [system_message] + messages
        response = self.llm_with_tools.invoke(full_messages)
        
        return {"messages": [response]}
    
    def _should_continue(self, state: AgentState):
        """다음 단계 결정"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # 도구 호출이 있으면 tools 노드로
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # 없으면 종료
        return END
    
    def _execute_tools(self, state: AgentState):
        """도구 실행 (Action 단계)"""
        messages = state["messages"]
        last_message = messages[-1]
        
        tool_calls = last_message.tool_calls if hasattr(last_message, 'tool_calls') else []
        
        tool_messages = []
        tools_used = state.get("tools_used", [])
        
        for tool_call in tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # 도구 찾기
            tool_func = next((t for t in AGENT_TOOLS if t.name == tool_name), None)
            
            if tool_func:
                try:
                    result = tool_func.invoke(tool_args)
                    
                    # 사용된 도구 기록
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                    
                    # ToolMessage 생성
                    from langchain_core.messages import ToolMessage
                    tool_message = ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id']
                    )
                    tool_messages.append(tool_message)
                    
                except Exception as e:
                    from langchain_core.messages import ToolMessage
                    tool_message = ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call['id']
                    )
                    tool_messages.append(tool_message)
        
        return {
            "messages": tool_messages,
            "tools_used": tools_used
        }
    
    def chat(self, query: str, session_messages: List = None) -> dict:
        """
        사용자 질문에 대한 답변 생성
        
        Args:
            query: 사용자 질문
            session_messages: 이전 대화 내역 (optional)
            
        Returns:
            {
                "answer": str,
                "tool_used": str,
                "tool_id": str,
                "action_type": str,  # "view" or "execute"
                "execution_data": dict | None,
                "page_url": str | None,
                "full_response": str
            }
        """
        # 대화 내역 준비
        messages = session_messages.copy() if session_messages else []
        messages.append(HumanMessage(content=query))
        
        # Agent 실행
        initial_state = {
            "messages": messages,
            "tools_used": []
        }
        
        result = self.graph.invoke(initial_state)
        
        # 최종 답변과 도구 응답 결합
        final_answer = ""
        tool_response_with_metadata = ""
        
        # 도구 응답에서 메타데이터 태그 추출
        from langchain_core.messages import ToolMessage
        for message in result["messages"]:
            if isinstance(message, ToolMessage):
                content = str(message.content)
                # BOARD_IDS, SEARCH_QUERY, SEARCH_METADATA 태그 추출
                if '[BOARD_IDS]:' in content:
                    tool_response_with_metadata = content
        
        # AI 최종 답변 추출
        for message in reversed(result["messages"]):
            if isinstance(message, AIMessage) and not (hasattr(message, 'tool_calls') and message.tool_calls):
                final_answer = message.content
                break
        
        # 메타데이터 태그를 최종 답변에 추가 (사용자에게는 보이지 않음)
        if tool_response_with_metadata:
            # 메타데이터 태그만 추출
            metadata_lines = []
            for line in tool_response_with_metadata.split('\n'):
                if line.strip().startswith('[BOARD_IDS]:') or \
                   line.strip().startswith('[SEARCH_QUERY]:') or \
                   line.strip().startswith('[SEARCH_METADATA]:'):
                    metadata_lines.append(line)
            
            if metadata_lines:
                final_answer = final_answer + '\n\n' + '\n'.join(metadata_lines)
        
        # 사용된 도구 추출
        tools_used = result.get("tools_used", [])
        tool_used = tools_used[0] if tools_used else None
        
        # 실행 명령 데이터 추출 (ToolMessage에서)
        action_type = "view"
        execution_data = None
        
        for message in result["messages"]:
            if hasattr(message, 'content'):
                content_str = str(message.content)
                # JSON 형식의 실행 명령 찾기
                if '"action": "execute_analysis"' in content_str or '"action": "execute_action"' in content_str or '"action": "filter_reports"' in content_str or '"action": "show_post_detail"' in content_str or '"action": "back_to_list"' in content_str:
                    try:
                        execution_data = json.loads(content_str)
                        action_type = "execute"
                        # 실행 명령이 발견되면 답변을 execution_data의 message로 대체
                        if execution_data.get("message"):
                            final_answer = execution_data["message"]
                        # execution_data가 중첩된 경우 추출
                        if "execution_data" in execution_data:
                            execution_data = execution_data["execution_data"]
                        break
                    except json.JSONDecodeError:
                        pass
        
        # 페이지 URL 추출 (도구 결과에서 추출)
        page_url = None
        for message in result["messages"]:
            if hasattr(message, 'content') and '[페이지 이동:' in str(message.content):
                match = re.search(r'\[페이지 이동: (.*?)\]', str(message.content))
                if match:
                    page_url = match.group(1).strip()
                    break
        
        # 도구 이름을 한글로 변환
        tool_name_map = {
            "semantic_search_tool": "의미 기반 검색",
            "churn_analysis_tool": "이탈 분석",
            "ethics_check_tool": "비윤리/스팸 분석",
            "match_reports_tool": "신고 통계",
            "trends_analysis_tool": "트렌드 분석",
            "execute_churn_analysis_tool": "이탈 분석 실행",
            "execute_ethics_analysis_tool": "비윤리/스팸 분석 실행",
            "approve_report_tool": "신고 승인",
            "reject_report_tool": "신고 거부",
            "filter_reports_tool": "신고 필터링",
            "board_navigation_tool": "게시판 조작",
            "board_detail_tool": "게시글 상세보기",
            "board_filter_tool": "게시판 필터링",
            "board_page_tool": "페이지 이동",
            "board_list_tool": "목록 보기",
            "daily_report_tool": "일일 보고서"
        }
        
        tool_display_name = tool_name_map.get(tool_used, tool_used) if tool_used else "없음"
        
        return {
            "answer": final_answer,
            "tool_used": tool_display_name,
            "tool_id": tool_used,
            "action_type": action_type,
            "execution_data": execution_data,
            "page_url": page_url,
            "full_response": final_answer
        }


# 전역 Agent 인스턴스
_agent_instance = None


def get_agent() -> CommunityAgent:
    """Agent 싱글톤 반환"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CommunityAgent()
    return _agent_instance

