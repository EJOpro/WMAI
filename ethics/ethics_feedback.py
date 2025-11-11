"""
Ethics 피드백 모듈
관리자 피드백을 벡터DB에 저장하는 기능 제공
독립적으로 구현 (chrun_backend 참조 없음)
"""

from typing import Dict, Optional
from datetime import datetime
from ethics.ethics_vector_db import get_client, upsert_confirmed_case
from ethics.ethics_embedding import get_embedding
from ethics.ethics_text_splitter import split_to_sentences


def save_feedback_to_vector_db(
    text: str,
    original_immoral_score: float,
    original_spam_score: float,
    original_immoral_confidence: float,
    original_spam_confidence: float,
    admin_action: str,  # 'immoral', 'spam', 'clean'
    admin_id: int,
    log_id: Optional[int] = None,
    note: Optional[str] = None
) -> bool:
    """
    관리자 피드백을 벡터DB에 저장
    
    Args:
        text: 피드백 대상 텍스트
        original_immoral_score: 원래 비윤리 점수
        original_spam_score: 원래 스팸 점수
        original_immoral_confidence: 원래 비윤리 신뢰도
        original_spam_confidence: 원래 스팸 신뢰도
        admin_action: 관리자 액션 ('immoral', 'spam', 'clean')
        admin_id: 관리자 ID
        log_id: ethics_logs 테이블의 ID (선택)
        note: 관리자 메모 (선택)
    
    Returns:
        bool: 저장 성공 여부
    """
    try:
        client = get_client()
        
        action = (admin_action or '').lower()
        
        # 관리자 액션에 따라 점수 및 신뢰도 조정
        if action == 'immoral':
            # 비윤리 확정
            adjusted_immoral_score = 90.0
            immoral_confidence = 100.0
            # 스팸 점수와 신뢰도는 기존 로그 기록과 동일
            adjusted_spam_score = original_spam_score
            spam_confidence = original_spam_confidence
            confirmed = True
            
        elif action == 'spam':
            # 스팸 확정
            adjusted_spam_score = 100.0
            spam_confidence = 100.0
            # 비윤리 점수와 신뢰도는 기존 로그 기록과 동일
            adjusted_immoral_score = original_immoral_score
            immoral_confidence = original_immoral_confidence
            confirmed = True
            
        elif action == 'clean':
            # 문제없음 확정
            # 비윤리 점수: 60 이상이면 50% 감점, 60 미만이면 30% 감점
            if original_immoral_score >= 60:
                adjusted_immoral_score = original_immoral_score * 0.5  # 50% 감점
            else:
                adjusted_immoral_score = original_immoral_score * 0.7  # 30% 감점
            immoral_confidence = 80.0
            
            # 스팸 점수: 60 이상이면 50% 감점, 60 미만이면 30% 감점
            if original_spam_score >= 60:
                adjusted_spam_score = original_spam_score * 0.5  # 50% 감점
            else:
                adjusted_spam_score = original_spam_score * 0.7  # 30% 감점
            spam_confidence = 80.0
            
            confirmed = True
        else:
            return False
        
        # 텍스트를 문장 단위로 청킹
        sentences = split_to_sentences(text, min_length=10)
        
        if not sentences:
            return False
        
        # 각 문장별로 저장
        saved_count = 0
        for sentence in sentences:
            # 임베딩 생성
            embedding = get_embedding(sentence)
            
            # 메타데이터 준비
            metadata = {
                "sentence": sentence,
                "immoral_score": adjusted_immoral_score,
                "spam_score": adjusted_spam_score,
                "immoral_confidence": immoral_confidence,
                "spam_confidence": spam_confidence,
                "confidence": max(immoral_confidence, spam_confidence),  # 높은 신뢰도 사용
                "confirmed": confirmed,
                "post_id": f"feedback_{log_id}" if log_id else "",
                "user_id": f"admin_{admin_id}",
                "created_at": datetime.now().isoformat(),
                "feedback_type": "admin_review",
                "admin_id": str(admin_id),
                "original_immoral_score": original_immoral_score,
                "original_spam_score": original_spam_score,
                "admin_action": admin_action,
                "note": note or ""
            }
            
            # 벡터DB에 저장
            upsert_confirmed_case(
                client=client,
                embedding=embedding,
                metadata=metadata
            )
            saved_count += 1
        
        print(f"[INFO] 관리자 피드백 저장 완료: action={admin_action}, "
              f"비윤리 {original_immoral_score:.1f} → {adjusted_immoral_score:.1f} (신뢰도 {immoral_confidence:.1f}), "
              f"스팸 {original_spam_score:.1f} → {adjusted_spam_score:.1f} (신뢰도 {spam_confidence:.1f}), "
              f"{saved_count}개 문장 저장")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 관리자 피드백 저장 실패: {e}")
        return False

