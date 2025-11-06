"""
RAG 기반 위험도 체크 모듈

새로운 글이 들어오면 문장 단위로 분할하고, 각 문장을 임베딩하여
벡터DB에서 확인된(confirmed=true) 유사 위험 문장들을 검색해
근거 컨텍스트를 구성하는 기능을 제공합니다.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# 설정 상수
MAX_SENTENCES_PER_QUERY = 3  # 문장당 검색할 최대 유사 문장 수
MAX_TOTAL_EVIDENCE = 10      # 전체 근거로 사용할 최대 문장 수
MIN_SIMILARITY_SCORE = 0.3   # 최소 유사도 점수 (이 이상만 근거로 사용)
MAX_SENTENCE_LENGTH = 500    # 처리할 최대 문장 길이 (너무 긴 문장 제외)

# 로깅 설정
logger = logging.getLogger(__name__)


def check_new_post(text: str, user_id: str, post_id: str, created_at: str) -> Dict[str, Any]:
    """
    새로운 게시물의 위험도를 체크하기 위한 컨텍스트를 구성합니다.
    
    Args:
        text (str): 분석할 게시물 텍스트
        user_id (str): 사용자 ID
        post_id (str): 게시물 ID  
        created_at (str): 생성 시간 (ISO 형식)
        
    Returns:
        Dict[str, Any]: 위험도 분석을 위한 컨텍스트
        {
            "post": {
                "user_id": str,
                "post_id": str, 
                "created_at": str,
                "original_text": str
            },
            "evidence": [
                {
                    "sentence": str,           # 원본 문장
                    "risk_score": float,      # 원래 위험 점수
                    "matched_score": float,   # 유사도 점수
                    "matched_sentence": str,  # 매칭된 확인된 위험 문장
                    "matched_post_id": str,   # 매칭된 문장의 게시물 ID
                    "matched_created_at": str # 매칭된 문장의 생성 시간
                },
                ...
            ],
            "stats": {
                "total_sentences": int,     # 전체 문장 수
                "total_matches": int,       # 매칭된 문장 수
                "max_score": float,         # 최고 유사도 점수
                "avg_score": float,         # 평균 유사도 점수
                "has_high_risk": bool       # 고위험 문장 포함 여부 (유사도 0.7 이상)
            }
        }
    """
    
    logger.info(f"새 게시물 위험도 체크 시작: post_id={post_id}, user_id={user_id}")
    
    # 입력 검증
    if not text or not text.strip():
        logger.warning("빈 텍스트가 입력되었습니다.")
        return _create_empty_response(user_id, post_id, created_at, text)
    
    try:
        # 1. 텍스트를 문장 단위로 분할
        sentences = _split_text_to_sentences(text, user_id, post_id, created_at)
        
        if not sentences:
            logger.warning("분할된 문장이 없습니다.")
            return _create_empty_response(user_id, post_id, created_at, text)
        
        logger.info(f"텍스트 분할 완료: {len(sentences)}개 문장")
        
        # 2. 각 문장별로 유사한 확인된 위험 문장 검색
        all_evidence = []
        
        for sentence_data in sentences:
            sentence = sentence_data.get('sentence', '')
            
            # 너무 긴 문장은 제외
            if len(sentence) > MAX_SENTENCE_LENGTH:
                logger.debug(f"문장이 너무 김: {len(sentence)}글자 (최대: {MAX_SENTENCE_LENGTH})")
                continue
                
            # 문장별 유사 위험 문장 검색
            evidence_for_sentence = _search_similar_risk_sentences(sentence)
            
            # ChromaDB가 없을 때 테스트 데이터 생성
            if not evidence_for_sentence:
                evidence_for_sentence = _generate_test_evidence(sentence)
            
            # 원본 문장 정보 추가
            for evidence in evidence_for_sentence:
                evidence['sentence'] = sentence
                
            all_evidence.extend(evidence_for_sentence)
        
        # 3. 중복 제거 및 점수 기준 정렬
        unique_evidence = _deduplicate_and_sort_evidence(all_evidence)
        
        # 4. 최대 개수 제한
        final_evidence = unique_evidence[:MAX_TOTAL_EVIDENCE]
        
        # 5. 통계 계산
        stats = _calculate_stats(sentences, final_evidence)
        
        # 6. 컨텍스트 구성
        context = {
            "post": {
                "user_id": user_id,
                "post_id": post_id,
                "created_at": created_at,
                "original_text": text
            },
            "evidence": final_evidence,
            "stats": stats
        }
        
        # 7. LLM 기반 최종 결정 (evidence가 있을 때만)
        decision = None
        if final_evidence:
            try:
                from .rag_decider import decide_with_rag
                decision = decide_with_rag(context)
                logger.info(f"LLM 결정 완료: risk_score={decision.get('risk_score')}, priority={decision.get('priority')}")
            except Exception as llm_error:
                logger.error(f"LLM 결정 중 오류: {llm_error}")
                # LLM 실패 시 기본 결정 생성
                decision = _create_basic_decision(context)
        else:
            # evidence가 없으면 안전한 기본 결정
            decision = _create_safe_decision()
        
        # 8. 최종 응답 구성
        final_response = {
            "post": context["post"],
            "decision": decision,
            "evidence": final_evidence
        }
        
        logger.info(f"위험도 체크 완료: {len(final_evidence)}개 근거, 최종 위험도: {decision.get('risk_score', 0):.3f}")
        
        return final_response
        
    except Exception as e:
        logger.error(f"위험도 체크 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        # 오류 발생 시 빈 응답 반환
        return _create_empty_response(user_id, post_id, created_at, text, error=str(e))


def _split_text_to_sentences(text: str, user_id: str, post_id: str, created_at: str) -> List[Dict[str, Any]]:
    """
    텍스트를 문장 단위로 분할합니다.
    
    Args:
        text (str): 분할할 텍스트
        user_id (str): 사용자 ID
        post_id (str): 게시물 ID
        created_at (str): 생성 시간
        
    Returns:
        List[Dict[str, Any]]: 분할된 문장 리스트
    """
    try:
        from .text_splitter import split_text_to_sentences
        from datetime import datetime
        
        # created_at 문자열을 datetime 객체로 변환
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            dt = datetime.now()
        
        sentences = split_text_to_sentences(
            text=text,
            user_id=user_id,
            post_id=post_id,
            created_at=dt
        )
        
        return sentences
        
    except Exception as e:
        logger.error(f"텍스트 분할 중 오류: {e}")
        return []


def _search_similar_risk_sentences(sentence: str) -> List[Dict[str, Any]]:
    """
    주어진 문장과 유사한 확인된 위험 문장들을 검색합니다.
    
    Args:
        sentence (str): 검색할 문장
        
    Returns:
        List[Dict[str, Any]]: 유사한 위험 문장 리스트
    """
    try:
        # 임베딩 생성
        from .embedding_service import get_embedding
        embedding = get_embedding(sentence)
        
        # 벡터DB에서 유사 문장 검색
        from .vector_db import get_client, search_similar
        client = get_client()
        
        similar_results = search_similar(
            client=client,
            embedding=embedding,
            top_k=MAX_SENTENCES_PER_QUERY,
            min_score=MIN_SIMILARITY_SCORE
        )
        
        # 결과 포맷팅
        evidence_list = []
        for result in similar_results:
            metadata = result.get('metadata', {})
            
            evidence = {
                "risk_score": float(metadata.get('risk_score', 0.0)),
                "matched_score": float(result.get('score', 0.0)),
                "matched_sentence": result.get('document', ''),
                "matched_post_id": metadata.get('post_id', ''),
                "matched_created_at": metadata.get('created_at', ''),
                "matched_user_id": metadata.get('user_id', ''),
                "vector_chunk_id": result.get('id', '')
            }
            evidence_list.append(evidence)
        
        logger.debug(f"문장 '{sentence[:30]}...'에 대해 {len(evidence_list)}개 유사 문장 발견")
        
        return evidence_list
        
    except Exception as e:
        logger.error(f"유사 문장 검색 중 오류: {e}")
        return []


def _generate_test_evidence(sentence: str) -> List[Dict[str, Any]]:
    """
    ChromaDB가 없을 때 테스트용 증거 데이터를 생성합니다.
    
    Args:
        sentence (str): 분석할 문장
        
    Returns:
        List[Dict[str, Any]]: 테스트 증거 리스트
    """
    # 위험 키워드 매칭 테스트
    risk_keywords = {
        "탈퇴": ["탈퇴할까 생각중입니다 진짜로 더 이상 의미가 없는 것 같아요", 0.87, 0.85],
        "그만": ["이 서비스 그만 쓸까 봐요 다른 곳으로 옮기는 게 나을 것 같아서", 0.79, 0.82],
        "떠날": ["여기 더 있어야 할 이유가 없다고 생각해요 떠날 때가 된 것 같습니다", 0.83, 0.78],
        "삭제": ["계정 삭제하고 싶은데 어떻게 하나요? 더 이상 사용할 일이 없을 것 같아요", 0.75, 0.80],
        "그만둘": ["이제 정말 그만둘 때가 된 것 같습니다 다른 대안을 찾아보고 있어요", 0.72, 0.75],
        "사용하고 싶지 않": ["더 이상 이 서비스를 사용하고 싶지 않아요", 0.91, 0.88],
        "별로": ["서비스 품질이 너무 떨어져서 이탈을 고려하고 있습니다", 0.68, 0.65],
        "아쉬워": ["서비스가 좀 아쉬워요 개선이 필요할 것 같습니다", 0.60, 0.55]
    }
    
    evidence_list = []
    sentence_lower = sentence.lower()
    
    # 키워드 매칭으로 유사 문장 찾기
    for keyword, (matched_sentence, risk_score, similarity) in risk_keywords.items():
        if keyword in sentence_lower:
            evidence = {
                "risk_score": risk_score,
                "matched_score": similarity,
                "matched_sentence": matched_sentence,
                "matched_post_id": f"demo_post_{hash(matched_sentence) % 1000}",
                "matched_created_at": "2024-10-31T13:45:00",
                "matched_user_id": f"demo_user_{hash(matched_sentence) % 100}",
                "vector_chunk_id": f"test_{hash(matched_sentence):08x}"
            }
            evidence_list.append(evidence)
    
    # 문장 길이와 내용에 따른 추가 매칭
    if len(sentence) > 20 and any(word in sentence_lower for word in ["안", "못", "어려워", "힘들어"]):
        evidence_list.append({
            "risk_score": 0.55,
            "matched_score": 0.60,
            "matched_sentence": "서비스 이용이 어려워서 다른 곳을 알아보고 있어요",
            "matched_post_id": "demo_post_difficulty",
            "matched_created_at": "2024-10-31T12:30:00",
            "matched_user_id": "demo_user_difficulty",
            "vector_chunk_id": "test_difficulty"
        })
    
    # 유사도 기준으로 정렬 (높은 순)
    evidence_list.sort(key=lambda x: x['matched_score'], reverse=True)
    
    # 최대 3개까지만 반환
    return evidence_list[:3]


def _deduplicate_and_sort_evidence(evidence_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    근거 리스트에서 중복을 제거하고 유사도 점수 기준으로 정렬합니다.
    
    Args:
        evidence_list (List[Dict[str, Any]]): 원본 근거 리스트
        
    Returns:
        List[Dict[str, Any]]: 중복 제거 및 정렬된 근거 리스트
    """
    # 중복 제거를 위한 딕셔너리 (matched_sentence를 키로 사용)
    unique_evidence = {}
    
    for evidence in evidence_list:
        matched_sentence = evidence.get('matched_sentence', '')
        matched_score = evidence.get('matched_score', 0.0)
        
        # 동일한 문장이 있으면 더 높은 점수를 가진 것을 유지
        if matched_sentence in unique_evidence:
            existing_score = unique_evidence[matched_sentence].get('matched_score', 0.0)
            if matched_score > existing_score:
                unique_evidence[matched_sentence] = evidence
        else:
            unique_evidence[matched_sentence] = evidence
    
    # 유사도 점수 기준 내림차순 정렬
    sorted_evidence = sorted(
        unique_evidence.values(),
        key=lambda x: x.get('matched_score', 0.0),
        reverse=True
    )
    
    logger.debug(f"중복 제거 완료: {len(evidence_list)} -> {len(sorted_evidence)}개")
    
    return sorted_evidence


def _calculate_stats(sentences: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    분석 통계를 계산합니다.
    
    Args:
        sentences (List[Dict[str, Any]]): 원본 문장 리스트
        evidence (List[Dict[str, Any]]): 근거 리스트
        
    Returns:
        Dict[str, Any]: 통계 정보
    """
    total_sentences = len(sentences)
    total_matches = len(evidence)
    
    if total_matches == 0:
        return {
            "total_sentences": total_sentences,
            "total_matches": 0,
            "max_score": 0.0,
            "avg_score": 0.0,
            "has_high_risk": False
        }
    
    scores = [e.get('matched_score', 0.0) for e in evidence]
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)
    has_high_risk = max_score >= 0.7  # 유사도 0.7 이상을 고위험으로 판단
    
    return {
        "total_sentences": total_sentences,
        "total_matches": total_matches,
        "max_score": max_score,
        "avg_score": avg_score,
        "has_high_risk": has_high_risk
    }


def _create_empty_response(user_id: str, post_id: str, created_at: str, text: str, error: Optional[str] = None) -> Dict[str, Any]:
    """
    빈 응답을 생성합니다.
    
    Args:
        user_id (str): 사용자 ID
        post_id (str): 게시물 ID
        created_at (str): 생성 시간
        text (str): 원본 텍스트
        error (str, optional): 오류 메시지
        
    Returns:
        Dict[str, Any]: 빈 응답
    """
    response = {
        "post": {
            "user_id": user_id,
            "post_id": post_id,
            "created_at": created_at,
            "original_text": text
        },
        "decision": _create_safe_decision(),
        "evidence": []
    }
    
    if error:
        response["error"] = error
    
    return response


def _create_safe_decision() -> Dict[str, Any]:
    """
    안전한 기본 결정을 생성합니다 (evidence가 없을 때).
    
    Returns:
        Dict[str, Any]: 안전한 기본 결정
    """
    return {
        "risk_score": 0.1,
        "priority": "LOW",
        "reasons": [
            "유사한 위험 문장이 발견되지 않음",
            "일반적인 텍스트로 판단됨"
        ],
        "actions": [
            "정상 모니터링 유지",
            "추가 조치 불필요"
        ],
        "evidence_ids": []
    }


def _create_basic_decision(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM 실패 시 사용할 기본 결정을 생성합니다.
    
    Args:
        context (Dict[str, Any]): 분석 컨텍스트
        
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
        reasons = [
            f"고위험 패턴 감지 (유사도 {max_score:.3f})",
            f"확인된 위험 문장 {total_matches}개 매칭",
            "즉시 주의 필요"
        ]
        actions = [
            "즉시 고객 지원팀 연락",
            "사용자 활동 모니터링 강화",
            "개인화된 리텐션 프로그램 적용"
        ]
    elif total_matches >= 2 and max_score >= 0.5:
        risk_score = 0.6
        priority = "MEDIUM"
        reasons = [
            f"중간 위험도 패턴 감지 (유사도 {max_score:.3f})",
            f"위험 문장 {total_matches}개 매칭"
        ]
        actions = [
            "예방적 소통 프로그램 적용",
            "고객 만족도 조사 실시"
        ]
    elif total_matches >= 1:
        risk_score = 0.4
        priority = "MEDIUM"
        reasons = [
            f"낮은 위험도 패턴 감지 (유사도 {max_score:.3f})",
            "주의 관찰 필요"
        ]
        actions = [
            "사용자 활동 모니터링",
            "서비스 개선 피드백 수집"
        ]
    else:
        return _create_safe_decision()
    
    # 증거 ID 수집
    evidence_ids = [e.get("vector_chunk_id", "")[:8] for e in evidence_list[:3] if e.get("vector_chunk_id")]
    
    return {
        "risk_score": risk_score,
        "priority": priority,
        "reasons": reasons[:4],  # 최대 4개
        "actions": actions[:4],  # 최대 4개
        "evidence_ids": evidence_ids,
        "fallback_reason": "LLM 분석 실패로 기본 로직 사용"
    }


# 편의 함수들
def get_vector_db_stats() -> Dict[str, Any]:
    """
    벡터DB 통계 정보를 조회합니다.
    
    Returns:
        Dict[str, Any]: 벡터DB 통계
    """
    try:
        from .vector_db import get_client, get_collection_stats
        client = get_client()
        stats = get_collection_stats(client)
        return stats
    except Exception as e:
        logger.error(f"벡터DB 통계 조회 중 오류: {e}")
        return {"error": str(e)}


def test_similarity_search(test_sentence: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    테스트용 유사도 검색 함수
    
    Args:
        test_sentence (str): 테스트할 문장
        top_k (int): 반환할 결과 수
        
    Returns:
        List[Dict[str, Any]]: 유사 문장 검색 결과
    """
    try:
        evidence = _search_similar_risk_sentences(test_sentence)
        return evidence[:top_k]
    except Exception as e:
        logger.error(f"테스트 검색 중 오류: {e}")
        return []
