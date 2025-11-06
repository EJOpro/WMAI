"""
RAG 기반 위험도 결정 모듈

컨텍스트(evidence 등)를 사용해 LLM이 최종 위험도와 액션을 산출합니다.
출력은 반드시 JSON 형식으로 강제하여 구조화된 결과를 보장합니다.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 설정 상수
LLM_MODEL = "gpt-4o-mini"  # 빠르고 경제적인 모델 사용
LLM_TIMEOUT = 30  # API 호출 타임아웃 (초)
MAX_TOKENS = 500  # 최대 토큰 수 (JSON 응답용)
TEMPERATURE = 0.1  # 낮은 온도로 일관된 결과

# 로깅 설정
logger = logging.getLogger(__name__)


def decide_with_rag(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    RAG 컨텍스트를 기반으로 LLM이 최종 위험도와 액션을 결정합니다.
    
    Args:
        context (Dict[str, Any]): check_new_post에서 생성된 컨텍스트
        
    Returns:
        Dict[str, Any]: LLM 결정 결과
        {
            "risk_score": float,        # 0.0 ~ 1.0
            "priority": str,            # "LOW", "MEDIUM", "HIGH"
            "reasons": List[str],       # 위험도 판단 이유 2~4개
            "actions": List[str],       # 권장 액션 2~4개
            "evidence_ids": List[str]   # 참고한 evidence ID들
        }
    """
    
    logger.info("LLM 기반 위험도 결정 시작")
    
    # 환경변수에서 OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 기본값을 반환합니다.")
        return _get_fallback_decision(context)
    
    try:
        # OpenAI 클라이언트 import 및 초기화
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("OpenAI 패키지가 설치되지 않았습니다. 기본값을 반환합니다.")
            return _get_fallback_decision(context)
        
        client = OpenAI(api_key=api_key, timeout=LLM_TIMEOUT)
        
        # 프롬프트 생성
        system_prompt = _create_system_prompt()
        user_prompt = _create_user_prompt(context)
        
        logger.debug(f"시스템 프롬프트 길이: {len(system_prompt)}")
        logger.debug(f"사용자 프롬프트 길이: {len(user_prompt)}")
        
        # LLM API 호출
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"}  # JSON 형식 강제
        )
        
        # 응답 텍스트 추출
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"LLM 응답: {response_text}")
        
        # JSON 파싱
        decision = _parse_llm_response(response_text, context)
        
        logger.info(f"LLM 결정 완료: risk_score={decision.get('risk_score')}, priority={decision.get('priority')}")
        
        return decision
        
    except Exception as e:
        logger.error(f"LLM 호출 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        # 오류 시 기본값 반환
        return _get_fallback_decision(context, error=str(e))


def _create_system_prompt() -> str:
    """
    시스템 프롬프트를 생성합니다.
    
    Returns:
        str: 시스템 프롬프트
    """
    return """너는 커뮤니티 이탈 징후 감지 전문 어시스턴트다.

주어진 컨텍스트를 바탕으로 사용자의 이탈 위험도를 분석하고 대응 방안을 제시한다.

**중요 규칙:**
1. 반드시 JSON 형식으로만 응답한다. 설명이나 주석은 절대 포함하지 않는다.
2. 지정된 스키마를 정확히 따른다.
3. 한국어로 이유와 액션을 작성한다.
4. 객관적이고 실용적인 판단을 한다.

**위험도 기준:**
- LOW (0.0-0.3): 일반적인 불만, 즉시 대응 불필요
- MEDIUM (0.3-0.7): 주의 관찰 필요, 예방적 조치 고려
- HIGH (0.7-1.0): 즉시 개입 필요, 적극적 대응 요구

**액션 유형:**
- 모니터링: 추가 관찰, 패턴 분석
- 소통: 직접 연락, 피드백 수집
- 개선: 서비스 개선, 맞춤 지원
- 예방: 사전 조치, 리텐션 프로그램"""


def _create_user_prompt(context: Dict[str, Any]) -> str:
    """
    사용자 프롬프트를 생성합니다.
    
    Args:
        context (Dict[str, Any]): 분석 컨텍스트
        
    Returns:
        str: 사용자 프롬프트
    """
    post_info = context.get("post", {})
    evidence_list = context.get("evidence", [])
    stats = context.get("stats", {})
    
    # 현재 글 개요
    post_section = f"""[현재 글 개요]
- user_id: {post_info.get('user_id', 'N/A')}
- post_id: {post_info.get('post_id', 'N/A')}
- created_at: {post_info.get('created_at', 'N/A')}
- 원문: "{post_info.get('original_text', '')[:200]}{'...' if len(post_info.get('original_text', '')) > 200 else ''}"

[분석 통계]
- 전체 문장 수: {stats.get('total_sentences', 0)}
- 매칭된 위험 문장 수: {stats.get('total_matches', 0)}
- 최고 유사도: {stats.get('max_score', 0.0):.3f}
- 평균 유사도: {stats.get('avg_score', 0.0):.3f}
- 고위험 문장 포함: {'예' if stats.get('has_high_risk', False) else '아니오'}"""
    
    # 증거 문장 모음
    evidence_section = "[증거 문장 모음 (확인된 위험 문장, 유사도 높은 순)]"
    
    if evidence_list:
        for i, evidence in enumerate(evidence_list[:10], 1):  # 최대 10개만 표시
            evidence_section += f"""
{i}. ID: {evidence.get('vector_chunk_id', 'N/A')[:8]}...
   - 원본 문장: "{evidence.get('sentence', '')}"
   - 매칭된 위험 문장: "{evidence.get('matched_sentence', '')}"
   - 유사도: {evidence.get('matched_score', 0.0):.3f}
   - 원래 위험점수: {evidence.get('risk_score', 0.0):.3f}
   - 매칭 게시물: {evidence.get('matched_post_id', 'N/A')}
   - 매칭 시점: {evidence.get('matched_created_at', 'N/A')}"""
    else:
        evidence_section += "\n(매칭된 위험 문장 없음)"
    
    # 요구사항
    requirement_section = """
[요구사항]
아래 JSON 스키마로만 답하라. 설명이나 주석은 절대 포함하지 않는다.

{
  "risk_score": 0.0~1.0 숫자,
  "priority": "LOW"|"MEDIUM"|"HIGH",
  "reasons": [문자열 2~4개 - 위험도 판단 근거],
  "actions": [문자열 2~4개 - 구체적 대응 방안],
  "evidence_ids": [참고한 evidence ID들의 앞 8자리]
}"""
    
    return f"{post_section}\n\n{evidence_section}\n{requirement_section}"


def _parse_llm_response(response_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM 응답을 JSON으로 파싱하고 검증합니다.
    
    Args:
        response_text (str): LLM 응답 텍스트
        context (Dict[str, Any]): 원본 컨텍스트 (fallback용)
        
    Returns:
        Dict[str, Any]: 파싱된 결정 결과
    """
    try:
        # JSON 파싱 시도
        decision = json.loads(response_text)
        
        # 필수 필드 검증 및 기본값 설정
        validated_decision = {
            "risk_score": _validate_risk_score(decision.get("risk_score")),
            "priority": _validate_priority(decision.get("priority")),
            "reasons": _validate_string_list(decision.get("reasons"), 2, 4, "위험도 판단 근거"),
            "actions": _validate_string_list(decision.get("actions"), 2, 4, "대응 방안"),
            "evidence_ids": _validate_evidence_ids(decision.get("evidence_ids"), context)
        }
        
        logger.debug("LLM 응답 파싱 및 검증 완료")
        return validated_decision
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}")
        logger.debug(f"파싱 실패한 응답: {response_text}")
        
        # JSON 파싱 실패 시 기본값 반환
        return _get_fallback_decision(context, error="JSON 파싱 실패")
        
    except Exception as e:
        logger.error(f"응답 검증 중 오류: {e}")
        return _get_fallback_decision(context, error="응답 검증 실패")


def _validate_risk_score(score: Any) -> float:
    """위험 점수를 검증하고 0.0~1.0 범위로 제한합니다."""
    try:
        score = float(score)
        return max(0.0, min(1.0, score))
    except (TypeError, ValueError):
        return 0.5  # 기본값


def _validate_priority(priority: Any) -> str:
    """우선순위를 검증합니다."""
    if priority in ["LOW", "MEDIUM", "HIGH"]:
        return priority
    return "MEDIUM"  # 기본값


def _validate_string_list(items: Any, min_count: int, max_count: int, default_prefix: str) -> List[str]:
    """문자열 리스트를 검증합니다."""
    if not isinstance(items, list):
        return [f"{default_prefix} 분석 필요"] * min_count
    
    # 문자열만 필터링
    valid_items = [str(item) for item in items if item and str(item).strip()]
    
    # 개수 조정
    if len(valid_items) < min_count:
        while len(valid_items) < min_count:
            valid_items.append(f"{default_prefix} 추가 분석 필요")
    elif len(valid_items) > max_count:
        valid_items = valid_items[:max_count]
    
    return valid_items


def _validate_evidence_ids(ids: Any, context: Dict[str, Any]) -> List[str]:
    """증거 ID 리스트를 검증합니다."""
    if not isinstance(ids, list):
        ids = []
    
    # 유효한 증거 ID들 추출
    evidence_list = context.get("evidence", [])
    available_ids = [e.get("vector_chunk_id", "")[:8] for e in evidence_list if e.get("vector_chunk_id")]
    
    # 입력된 ID들 중 유효한 것만 필터링
    valid_ids = []
    for id_item in ids:
        id_str = str(id_item)[:8] if id_item else ""
        if id_str in available_ids:
            valid_ids.append(id_str)
    
    return valid_ids


def _get_fallback_decision(context: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
    """
    LLM 호출 실패 시 사용할 기본 결정을 생성합니다.
    
    Args:
        context (Dict[str, Any]): 원본 컨텍스트
        error (str, optional): 오류 메시지
        
    Returns:
        Dict[str, Any]: 기본 결정
    """
    stats = context.get("stats", {})
    evidence_list = context.get("evidence", [])
    
    # 통계 기반 간단한 위험도 계산
    max_score = stats.get("max_score", 0.0)
    total_matches = stats.get("total_matches", 0)
    has_high_risk = stats.get("has_high_risk", False)
    
    # 위험도 점수 결정
    if has_high_risk and max_score >= 0.8:
        risk_score = 0.8
        priority = "HIGH"
    elif total_matches >= 2 and max_score >= 0.5:
        risk_score = 0.6
        priority = "MEDIUM"
    elif total_matches >= 1:
        risk_score = 0.4
        priority = "MEDIUM"
    else:
        risk_score = 0.2
        priority = "LOW"
    
    # 기본 이유와 액션
    reasons = [
        f"유사한 위험 문장 {total_matches}개 발견",
        f"최고 유사도 {max_score:.3f}",
    ]
    
    if has_high_risk:
        reasons.append("고위험 패턴 감지됨")
    
    actions = [
        "사용자 활동 모니터링 강화",
        "고객 만족도 조사 실시"
    ]
    
    if priority == "HIGH":
        actions.append("즉시 고객 지원팀 연락")
    elif priority == "MEDIUM":
        actions.append("예방적 소통 프로그램 적용")
    
    # 증거 ID 수집
    evidence_ids = [e.get("vector_chunk_id", "")[:8] for e in evidence_list[:3] if e.get("vector_chunk_id")]
    
    fallback = {
        "risk_score": risk_score,
        "priority": priority,
        "reasons": reasons[:4],  # 최대 4개
        "actions": actions[:4],  # 최대 4개
        "evidence_ids": evidence_ids
    }
    
    if error:
        fallback["fallback_reason"] = error
        logger.warning(f"기본값 사용: {error}")
    
    return fallback


# 테스트 및 디버깅용 함수들
def test_llm_connection() -> Dict[str, Any]:
    """
    LLM 연결 상태를 테스트합니다.
    
    Returns:
        Dict[str, Any]: 테스트 결과
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {
            "status": "error",
            "message": "OPENAI_API_KEY가 설정되지 않았습니다."
        }
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=10)
        
        # 간단한 테스트 요청
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        return {
            "status": "success",
            "message": "LLM 연결 성공",
            "model": LLM_MODEL,
            "response_length": len(response.choices[0].message.content)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"LLM 연결 실패: {str(e)}"
        }


def create_test_context() -> Dict[str, Any]:
    """
    테스트용 컨텍스트를 생성합니다.
    
    Returns:
        Dict[str, Any]: 테스트 컨텍스트
    """
    return {
        "post": {
            "user_id": "test_user_123",
            "post_id": "test_post_456",
            "created_at": "2024-11-04T15:30:00",
            "original_text": "이 서비스 정말 별로네요. 더 이상 사용하고 싶지 않아요."
        },
        "evidence": [
            {
                "sentence": "더 이상 사용하고 싶지 않아요.",
                "risk_score": 0.87,
                "matched_score": 0.92,
                "matched_sentence": "탈퇴할까 생각중입니다",
                "matched_post_id": "post_456",
                "matched_created_at": "2025-10-31T13:45:00",
                "vector_chunk_id": "abc12345def67890"
            }
        ],
        "stats": {
            "total_sentences": 2,
            "total_matches": 1,
            "max_score": 0.92,
            "avg_score": 0.92,
            "has_high_risk": True
        }
    }


if __name__ == "__main__":
    # 테스트 실행
    print("RAG 결정 모듈 테스트 시작...")
    
    # LLM 연결 테스트
    connection_test = test_llm_connection()
    print(f"LLM 연결 테스트: {connection_test}")
    
    # 테스트 컨텍스트로 결정 테스트
    if connection_test["status"] == "success":
        test_context = create_test_context()
        decision = decide_with_rag(test_context)
        print(f"테스트 결정 결과: {json.dumps(decision, ensure_ascii=False, indent=2)}")
    
    print("RAG 결정 모듈 테스트 완료!")
