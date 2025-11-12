"""
RAG 기반 위험도 결정 모듈

컨텍스트(evidence 등)를 사용해 LLM이 최종 위험도와 액션을 산출합니다.
출력은 반드시 JSON 형식으로 강제하여 구조화된 결과를 보장합니다.
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

from .report_schema import (
    create_report_schema,
    validate_report_schema,
    DEFAULT_MODEL as REPORT_DEFAULT_MODEL,
    PROMPT_VERSION as REPORT_PROMPT_VERSION,
)

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
        logger.warning("[RAG] OPENAI_API_KEY 미설정, 규칙 기반 폴백을 사용합니다.")
        return _finalize_decision(_get_fallback_decision(context, error="missing_openai_api_key"), context)
    
    try:
        # OpenAI 클라이언트 import 및 초기화
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("[RAG] OpenAI 패키지가 설치되지 않았습니다. 폴백 결정을 반환합니다.")
            return _finalize_decision(_get_fallback_decision(context, error="openai_package_missing"), context)
        
        logger.info("[RAG] OPENAI_API_KEY 확인 완료, LLM 호출 준비 (timeout=%ss)", LLM_TIMEOUT)
        
        client = OpenAI(api_key=api_key, timeout=LLM_TIMEOUT)
        
        # 프롬프트 생성
        system_prompt = _create_system_prompt()
        user_prompt = _create_user_prompt(context)
        
        logger.debug(f"시스템 프롬프트 길이: {len(system_prompt)}")
        logger.debug(f"사용자 프롬프트 길이: {len(user_prompt)}")
        
        # LLM API 호출
        try:
            llm_start = time.perf_counter()
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
            llm_elapsed = (time.perf_counter() - llm_start) * 1000
            logger.info("[RAG] LLM 판정 호출 완료 (%.2f ms)", llm_elapsed)
        except Exception as call_error:
            if _is_timeout_error(call_error):
                logger.error("[RAG] LLM 호출 타임아웃 발생 (%ss)", LLM_TIMEOUT, exc_info=True)
                return _finalize_decision(_get_fallback_decision(context, error="llm_timeout"), context)
            raise
        
        # 응답 텍스트 추출
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"LLM 응답: {response_text}")
        
        # JSON 파싱
        decision = _parse_llm_response(response_text, context)
        
        logger.info(f"LLM 결정 완료: risk_score={decision.get('risk_score')}, priority={decision.get('priority')}")
        
        return _finalize_decision(decision, context)
        
    except Exception as e:
        logger.error(f"LLM 호출 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        # 오류 시 기본값 반환
        return _finalize_decision(_get_fallback_decision(context, error=str(e)), context)


def _create_system_prompt() -> str:
    """
    커뮤니티 특화 시스템 프롬프트를 생성합니다.
    관계 기반 이탈 단계 분석 모델 적용.
    
    Returns:
        str: 시스템 프롬프트
    """
    return """너는 커뮤니티 이탈 징후 감지 전문 어시스턴트다.

커뮤니티는 기능이 아니라 **사람과 소속감** 때문에 유지된다.
관계 단절 신호를 조기에 포착하고, 회복 가능한 단계에서 개입하는 것이 핵심이다.

**핵심 원칙:**
1. 반드시 JSON 형식으로만 응답한다. 설명이나 주석은 절대 포함하지 않는다.
2. 지정된 스키마를 정확히 따른다.
3. 한국어로 이유와 액션을 작성한다.
4. 대상이 명시되지 않은 감정 표현은 일반적 감정으로 간주하여 위험도를 낮춘다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**커뮤니티 이탈 5단계 모델 (필수 분류)**

[1단계: 활발 참여 (Active)]
   신호: "재미있어요", "좋은 글", "우리 커뮤니티", 적극적 댓글/좋아요
   소속감: 강함 | 위험도: 0.0-0.15
   
[2단계: 소극 참여 (Passive)]
   신호: 조회만 함, 짧은 반응, "그냥 봐요", "가끔 들어와요"
   소속감: 보통 | 위험도: 0.15-0.35
   
[3단계: 관계 단절 (Disconnect)] ** 골든 타임!
   신호: "여기 사람들 별로", "소통 안돼요", "혼자 같아요", "예전같지 않네요"
   소속감: 약함 | 위험도: 0.35-0.60
   NOTE: 이 단계에서 개입하면 회복 가능!
   
[4단계: 대안 탐색 (Alternative)]
   신호: "XX 커뮤니티가 더 좋아요", "다른 곳 알아봐야겠어요", 비교 언급
   소속감: 거의 없음 | 위험도: 0.60-0.85
   
[5단계: 작별 (Farewell)]
   신호: "그동안 감사했습니다", "마지막 글", "탈퇴합니다", "안녕히 계세요"
   소속감: 없음 | 위험도: 0.85-1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**2차원 분석: 감정 × 소속감 (필수)**

**감정 차원:**
- [만족] 긍정적 표현, 감사
- [무관심] "그냥", "별로 관심", 무반응
- [짜증] "짜증나네", 불평, 비난
- [실망] "기대했는데", "아쉽네요", "실망이에요"
- [포기] "이제 됐어요", "관뒀어요", "의미없어요"

**소속감 지표 (핵심!):**
강함: "우리", "여기 사람들", "친구들", "함께", "같이"
보통: "회원분들", "이 커뮤니티", "여러분"
약함: "나만", "혼자", "외롭네요", "소통 안돼요"
없음: "남", "지나가는 사람", "별로 관심 없어요"

**판정 매트릭스 (대상 명시됨):**
              만족   무관심  짜증   실망   포기
강한 소속감   0.1    0.2    0.4    0.5    0.7
보통 소속감   0.2    0.4    0.5    0.7    0.8
약한 소속감   0.4    0.5    0.7    0.8    0.9
없는 소속감   0.5    0.7    0.8    0.9    0.95

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**대상 명시 확인 규칙 (최우선! 과대평가 방지)**

강한 부정 키워드("포기", "떠나다", "그만두다")도 대상이 명확해야만 고위험으로 판단한다.

[대상 명시됨 - 높은 위험도 유지]
- "여기 떠날래요" → 0.75-0.85
- "이 커뮤니티 그만둘게요" → 0.70-0.80
- "서비스 포기합니다" → 0.65-0.75
- "탈퇴할게요" → 0.85-0.90 (명시적 행동어)

[대상 불명확 - 위험도 대폭 하향 -0.35]
- "모든걸 포기하고 싶어요" → 0.30-0.40 (일반 감정)
- "떠나고 싶네요" → 0.25-0.35 (대상 없음)
- "그만두고 싶어요" → 0.30-0.40 (컨텍스트 부족)
- "힘들어요" → 0.20-0.30 (삶의 고민 가능성)

**판단 기준:**
1. "여기", "이곳", "서비스", "커뮤니티", "사이트" 등 **대상 지시어 있음** → 원래 점수
2. 대상 지시어 **없고** 구체적 불만도 없음 → **일반 감정**으로 간주, 위험도 -0.35
3. "탈퇴", "계정 삭제" 같은 **명시적 행동어** → 대상 없어도 높은 점수 유지 (단, -0.15)

**대상 불명확 시 보정된 매트릭스:**
              만족   무관심  짜증   실망   포기
없는 소속감   0.15   0.35   0.45   0.55   0.60

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**조건부 표현 해석 가이드 (매우 중요!)**

**조건부 긍정 = 현재 불만족 신호!**
- "~하면/~되면 계속 쓸게요" → 현재는 불만족 (위험도 0.4-0.6)
- "개선되면 볼 의향 있습니다" → 지금은 안 보고 있음 (위험도 0.45)
- "좀만 더 좋으면…" → 실망감의 완곡 표현 (위험도 0.5)
- "조금만 나아지면" → 현재 상태 불만족 (위험도 0.4-0.5)

**완곡 표현 = 실제 불만의 정중한 표현!**
- "좀…", "조금…", "약간…" → 실망감을 숨긴 표현
- "…" (말줄임표) → 한숨, 실망, 체념
- "그냥", "뭐" → 무관심 또는 실망

**조건부 vs 무조건부 비교:**
[X] "개선되면 계속 볼게요" (0.45) = 현재 불만 + 이탈 고려 중
[O] "개선을 기대합니다. 계속 볼게요" (0.2) = 긍정 + 미래 기대

**판단 규칙:**
1. "~면"이 포함되면 → 그것이 충족 안 된 현재 불만족 신호
2. 개선 요구 + 조건부 = 3단계(관계 단절) 초입 (0.4-0.5)
3. "의향 있다"는 가능성일 뿐, 현재는 아님 (위험도 감소 NO)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**긴급성 & 회복 가능성 평가**

**긴급성:**
- IMMEDIATE (즉시): "지금", "오늘", "당장" → 24시간 내 대응
- SOON (곧): "이번주", "며칠 안에" → 1주일 내 대응
- EVENTUAL (언젠가): "생각중", "고민", "나중에" → 모니터링
- UNCLEAR (불명확): 시간 언급 없음 → 추가 관찰

**회복 가능성:**
- HIGH: 소속감 남아있음 + 구체적 개선 요청 + 3단계 이하
- MEDIUM: 소속감 약함 + 대안 탐색 초기 + 4단계
- LOW: 소속감 없음 + 이미 결정 + 5단계

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**문맥 분석 체크리스트**

1. 톤 분석:
   - 농담/장난 ("ㅋㅋ", "ㅎㅎ", "구라", "방구") → 위험도 낮춤
   - 진지함 (논리적, 정중함, 구체적 불만) → 원래 평가
   - 분노/포기 (욕설, 단정적, "이제 됐어") → 위험도 높임

2. 소속감 분석 (가장 중요!):
   - "우리", "함께" 등 포함적 언어 사용 여부
   - 커뮤니티 멤버에 대한 언급 (긍정/부정)
   - 혼자/외롭다는 표현 여부

3. 이탈 의도:
   - 대안 커뮤니티/서비스 언급
   - 비교 표현 ("XX가 더 좋아요")
   - 작별 인사, 마지막 글 언급

4. 시간 긴급성:
   - 즉시성 표현 ("지금", "당장")
   - 이미 실행 중 ("알아보는 중", "가입했어요")

5. 대상 명시 (중요!):
   - "여기", "서비스", "커뮤니티" 등 명시 → 원래 점수
   - 대상 없는 감정 표현 → 위험도 -0.35

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**실전 판정 예시**

[예시 1] "검색 정확도가 좀만 더 좋으면… 관련 없는 글이 자꾸 섞여요. 개선되면 계속 볼 의향 있습니다"
→ 3단계(관계 단절) 초입, 실망, 보통~약한 소속감, 0.45, MEDIUM
→ 이유: "좀만 더" + "…" = 실망 완곡 표현, "개선되면"= 조건부(현재 불만족), "자꾸" = 반복적 불만
→ 액션: 즉시 개선 피드백 수집, 긍정 경험 제공, 골든 타임 개입

[예시 2] "요즘 여기 별로네요. 사람들이 예전같지 않아요"
→ 3단계(관계 단절), 실망, 약한 소속감, 0.55, HIGH, 회복가능성 높음
→ 액션: 즉시 개입 - 3단계는 골든 타임!

[예시 3] "XX 커뮤니티가 더 활발하던데요. 거기도 가봐야겠어요"
→ 4단계(대안 탐색), 무관심, 거의 없는 소속감, 0.78, CRITICAL, 회복가능성 중간
→ 액션: 24시간 내 긴급 대응

[예시 4] "탈퇴할까 ㅋㅋ 근데 친구들이 여기 있어서..."
→ 2단계(소극 참여), 무관심, 보통 소속감(친구), 0.35, MEDIUM, 회복가능성 높음
→ 액션: 친구 네트워크 활성화, 모니터링

[예시 5] "탈퇴할거임 ㅋㅋ 방구나 먹어라 뿡"
→ 1단계(활발), 농담 톤, 소속감 유지, 0.12, LOW
→ 액션: 정상적 활동, 관찰만

[예시 6] "모든걸 포기하고 떠나고 싶네요"
→ 2단계(소극 참여), 포기 감정, 대상 불명확, 0.35, MEDIUM
→ 이유: 대상 지시어 없음, 일반적 감정 표현 가능성, 서비스와의 연관성 불명확
→ 액션: 모니터링, 다음 게시글에서 컨텍스트 확인

[예시 7] "여기 모든게 별로네요. 포기하고 떠날래요"
→ 4단계(대안 탐색), 포기 감정, 약한 소속감, 0.85, CRITICAL
→ 이유: 대상 명시 + 강한 부정 + 확정적 의도
→ 액션: 24시간 내 긴급 개입

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**JSON 응답 스키마 (필수)**

{
  "risk_score": 0.0~1.0,
  "priority": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL",
  "churn_stage": "1단계: 활발 참여"|"2단계: 소극 참여"|"3단계: 관계 단절"|"4단계: 대안 탐색"|"5단계: 작별",
  "belongingness": "강함"|"보통"|"약함"|"없음",
  "emotion": "만족"|"무관심"|"짜증"|"실망"|"포기",
  "urgency": "IMMEDIATE"|"SOON"|"EVENTUAL"|"UNCLEAR",
  "recovery_chance": "HIGH"|"MEDIUM"|"LOW",
  "reasons": [문자열 2~5개 - 판단 근거, 소속감 분석 필수 포함],
  "actions": [문자열 2~5개 - 구체적 대응 방안, 단계별 맞춤 제안],
  "evidence_ids": [참고한 evidence ID들의 앞 8자리]
}

**액션 유형 가이드:**
- 1-2단계: 예방적 참여 유도, 긍정 경험 강화
- 3단계: 즉시 개입, 관계 회복, 소속감 강화 (골든 타임!)
- 4단계: 긴급 대응, 우리만의 가치 어필, 특별 혜택
- 5단계: 최소한의 시도, 재가입 유도 장치 마련"""


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
    
    # 요구사항 (커뮤니티 특화 스키마)
    requirement_section = """
[요구사항]
아래 JSON 스키마로만 답하라. 설명이나 주석은 절대 포함하지 않는다.

{
  "risk_score": 0.0~1.0 숫자,
  "priority": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL",
  "churn_stage": "1단계: 활발 참여"|"2단계: 소극 참여"|"3단계: 관계 단절"|"4단계: 대안 탐색"|"5단계: 작별",
  "belongingness": "강함"|"보통"|"약함"|"없음",
  "emotion": "만족"|"무관심"|"짜증"|"실망"|"포기",
  "urgency": "IMMEDIATE"|"SOON"|"EVENTUAL"|"UNCLEAR",
  "recovery_chance": "HIGH"|"MEDIUM"|"LOW",
  "reasons": [문자열 2~5개 - 판단 근거, 소속감 분석 필수 포함],
  "actions": [문자열 2~5개 - 구체적 대응 방안, 단계별 맞춤 제안],
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
        # 🔍 디버그: LLM 원본 응답 출력
        logger.info(f"[DEBUG] LLM 원본 응답 (처음 500자): {response_text[:500]}")
        
        # JSON 파싱 시도
        decision = json.loads(response_text)
        
        # 🔍 디버그: 파싱된 JSON 출력
        logger.info(f"[DEBUG] 파싱된 JSON 키: {list(decision.keys())}")
        logger.info(f"[DEBUG] risk_score: {decision.get('risk_score')}, priority: {decision.get('priority')}")
        
        # 필수 필드 검증 및 기본값 설정 (커뮤니티 특화 필드 포함)
        validated_decision = {
            "risk_score": _validate_risk_score(decision.get("risk_score")),
            "priority": _validate_priority(decision.get("priority")),
            "churn_stage": _validate_churn_stage(decision.get("churn_stage")),
            "belongingness": _validate_belongingness(decision.get("belongingness")),
            "emotion": _validate_emotion(decision.get("emotion")),
            "urgency": _validate_urgency(decision.get("urgency")),
            "recovery_chance": _validate_recovery_chance(decision.get("recovery_chance")),
            "reasons": _validate_string_list(decision.get("reasons"), 2, 5, "판단 근거"),
            "actions": _validate_string_list(decision.get("actions"), 2, 5, "대응 방안"),
            "evidence_ids": _validate_evidence_ids(decision.get("evidence_ids"), context)
        }
        
        logger.info(f"[DEBUG] 검증 후 risk_score: {validated_decision['risk_score']}, reasons: {validated_decision['reasons'][:2]}")
        logger.debug("LLM 응답 파싱 및 검증 완료 (커뮤니티 특화)")
        return validated_decision
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}")
        logger.error(f"파싱 실패한 응답 전체: {response_text}")
        
        # JSON 파싱 실패 시 기본값 반환
        return _get_fallback_decision(context, error="JSON 파싱 실패")
        
    except Exception as e:
        logger.error(f"응답 검증 중 오류: {e}")
        logger.error(f"오류 발생 시 응답: {response_text[:200]}")
        import traceback
        logger.error(f"상세 오류: {traceback.format_exc()}")
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
    if priority in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        return priority
    return "MEDIUM"  # 기본값


def _validate_churn_stage(stage: Any) -> str:
    """이탈 단계를 검증합니다."""
    valid_stages = [
        "1단계: 활발 참여",
        "2단계: 소극 참여",
        "3단계: 관계 단절",
        "4단계: 대안 탐색",
        "5단계: 작별"
    ]
    if stage in valid_stages:
        return stage
    return "2단계: 소극 참여"  # 기본값


def _validate_belongingness(belongingness: Any) -> str:
    """소속감을 검증합니다."""
    if belongingness in ["강함", "보통", "약함", "없음"]:
        return belongingness
    return "보통"  # 기본값


def _validate_emotion(emotion: Any) -> str:
    """감정을 검증합니다."""
    if emotion in ["만족", "무관심", "짜증", "실망", "포기"]:
        return emotion
    return "무관심"  # 기본값


def _validate_urgency(urgency: Any) -> str:
    """긴급성을 검증합니다."""
    if urgency in ["IMMEDIATE", "SOON", "EVENTUAL", "UNCLEAR"]:
        return urgency
    return "UNCLEAR"  # 기본값


def _validate_recovery_chance(chance: Any) -> str:
    """회복 가능성을 검증합니다."""
    if chance in ["HIGH", "MEDIUM", "LOW"]:
        return chance
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
    
    # 커뮤니티 특화 필드 추론
    if risk_score >= 0.85:
        churn_stage = "5단계: 작별"
        belongingness = "없음"
        emotion = "포기"
        urgency = "IMMEDIATE"
        recovery_chance = "LOW"
    elif risk_score >= 0.6:
        churn_stage = "4단계: 대안 탐색"
        belongingness = "약함"
        emotion = "실망"
        urgency = "SOON"
        recovery_chance = "MEDIUM"
    elif risk_score >= 0.35:
        churn_stage = "3단계: 관계 단절"
        belongingness = "보통"
        emotion = "무관심"
        urgency = "EVENTUAL"
        recovery_chance = "HIGH"
    elif risk_score >= 0.15:
        churn_stage = "2단계: 소극 참여"
        belongingness = "보통"
        emotion = "무관심"
        urgency = "UNCLEAR"
        recovery_chance = "HIGH"
    else:
        churn_stage = "1단계: 활발 참여"
        belongingness = "강함"
        emotion = "만족"
        urgency = "UNCLEAR"
        recovery_chance = "HIGH"
    
    fallback = {
        "risk_score": risk_score,
        "priority": priority,
        "churn_stage": churn_stage,
        "belongingness": belongingness,
        "emotion": emotion,
        "urgency": urgency,
        "recovery_chance": recovery_chance,
        "reasons": reasons[:5],  # 최대 5개
        "actions": actions[:5],  # 최대 5개
        "evidence_ids": evidence_ids,
        "confidence": "Low" if evidence_list else "Uncertain"
    }
    
    if error:
        fallback["fallback_reason"] = error
        logger.warning(f"기본값 사용 (커뮤니티 특화): {error}")
    
    return fallback


def _finalize_decision(decision: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    최종 응답 구조를 정리하고 report_schema 형태를 포함시킵니다.
    """
    stats = context.get("stats", {})
    evidence = context.get("evidence", [])
    decision = dict(decision)
    
    decision.setdefault("priority", "LOW")
    decision.setdefault("risk_score", 0.0)
    decision.setdefault("reasons", [])
    decision.setdefault("actions", [])
    decision.setdefault("evidence_ids", [])
    
    decision["reason"] = _build_reason_summary(decision, stats, evidence)
    
    report, report_validation = _build_report_payload(decision, context)
    decision["report"] = report
    decision["report_valid"] = report_validation[0]
    if report_validation[1]:
        decision["report_error"] = report_validation[1]
    
    return decision


def _build_reason_summary(decision: Dict[str, Any], stats: Dict[str, Any], evidence: List[Dict[str, Any]]) -> str:
    total_matches = stats.get("total_matches", len(evidence))
    max_score = stats.get("max_score")
    if max_score is None and evidence:
        max_score = max((float(ev.get("matched_score") or ev.get("similarity_score") or 0.0) for ev in evidence), default=0.0)
    max_score = float(max_score or 0.0)
    
    priority = decision.get("priority", "LOW")
    reasons = decision.get("reasons") or []
    primary_reason = reasons[0] if reasons else "추가 근거 분석 필요"
    
    line1 = f"{priority} 위험도로 판정했습니다. 근거 {total_matches}건, 최고 유사도 {max_score * 100:.1f}%."
    line2 = f"핵심 근거: {primary_reason}"
    return f"{line1} {line2}".strip()


def _build_report_payload(decision: Dict[str, Any], context: Dict[str, Any]) -> Tuple[Dict[str, Any], Tuple[bool, Optional[str]]]:
    evidence_rows = _convert_evidence_for_report(context.get("evidence", []), decision.get("evidence_ids", []))
    warnings = []
    fallback_reason = decision.get("fallback_reason")
    if fallback_reason:
        warnings.append(f"fallback:{fallback_reason}")
    
    report = create_report_schema(
        summary=decision.get("reason", ""),
        risk_level=(decision.get("priority") or "LOW").lower(),
        evidence=evidence_rows,
        actions=decision.get("actions", []),
        model=decision.get("model", LLM_MODEL if decision.get("confidence") != "Uncertain" else REPORT_DEFAULT_MODEL),
        prompt_v=f"{REPORT_PROMPT_VERSION}-rag-decider",
        warnings=warnings or None
    )
    
    is_valid, error = validate_report_schema(report)
    if not is_valid:
        logger.error("[RAG] report_schema 검증 실패: %s", error)
    
    return report, (is_valid, error)


def _convert_evidence_for_report(evidence_list: List[Dict[str, Any]], evidence_ids: List[str]) -> List[Dict[str, Any]]:
    converted = []
    for idx, item in enumerate(evidence_list):
        chunk_id = (
            item.get("vector_chunk_id")
            or item.get("chunk_id")
            or item.get("id")
            or (evidence_ids[idx] if idx < len(evidence_ids) else f"ev_{idx}")
        )
        sentence = item.get("matched_sentence") or item.get("sentence") or ""
        similarity = (
            item.get("matched_score")
            or item.get("similarity_score")
            or item.get("score")
            or 0.0
        )
        
        converted.append({
            "id": str(chunk_id)[:16],
            "snippet": sentence[:200],
            "similarity": round(float(similarity), 3)
        })
    return converted


def _is_timeout_error(error: Exception) -> bool:
    timeout_indicators = ("timeout", "timed out")
    message = str(error).lower()
    if any(indicator in message for indicator in timeout_indicators):
        return True
    
    if isinstance(error, TimeoutError):
        return True
    
    # OpenAI 전용 타임아웃 예외 확인
    try:
        from openai import error as openai_errors  # type: ignore
        timeout_cls = getattr(openai_errors, "Timeout", None)
        if timeout_cls and isinstance(error, timeout_cls):
            return True
        api_timeout_cls = getattr(openai_errors, "APITimeoutError", None)
        if api_timeout_cls and isinstance(error, api_timeout_cls):
            return True
    except ImportError:
        pass
    
    return False


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
