"""
텍스트 분할기 모듈 (KSS + Fallback + 메타데이터 강화)

KSS(Korean Sentence Splitter)를 우선 사용하고 실패 시 정규식으로 fallback하여
한국어 커뮤니티 텍스트를 정확하게 문장 단위로 분할합니다.

주요 개선사항:
- KSS 통합: 구어체, 생략부호, 채팅체 처리 향상
- 메타데이터 강화: 앞뒤 문장, 위치 정보 추가
- 문맥 보존: 문장 독립성 문제 해결
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TextSplitter:
    """
    KSS 기반 텍스트 분할기 (Fallback 지원)
    
    한국어 특화 문장 분리 + 메타데이터 강화로 RAG 성능 향상
    """
    
    def __init__(self, use_kss: bool = True):
        """
        Args:
            use_kss (bool): KSS 사용 여부 (기본값: True)
        """
        self.use_kss = use_kss
        
        # Fallback용 정규표현식 패턴 (기존 방식)
        self.sentence_pattern = re.compile(r'[.!?]+\s*(?=\s|$|\n)')
        
        # KSS 초기화
        if self.use_kss:
            try:
                import kss
                self.kss = kss
                self.kss_available = True
                logger.info("KSS 초기화 완료 - 한국어 특화 문장 분리 활성화")
            except ImportError:
                logger.warning("KSS가 설치되지 않았습니다. 정규식 fallback을 사용합니다.")
                self.kss_available = False
        else:
            self.kss_available = False
            logger.info("정규식 기반 문장 분리 사용")
        
    def split_text(
        self, 
        text: str, 
        user_id: Optional[str] = None, 
        post_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        텍스트를 문장 단위로 분할하여 강화된 메타데이터와 함께 반환
        
        Args:
            text (str): 분할할 원문 텍스트
            user_id (str, optional): 사용자 ID
            post_id (str, optional): 게시글 ID  
            created_at (datetime, optional): 생성 시간
            user_context (dict, optional): 사용자 컨텍스트 정보
                - activity_trend: 활동 추이 (예: "증가", "감소")
                - prev_posts_count: 이전 게시글 수
                - join_date: 가입일
                - recent_activity_score: 최근 활동 점수
            
        Returns:
            List[Dict[str, Any]]: 문장별 딕셔너리 리스트
                각 딕셔너리는 다음 키를 포함:
                - sentence: 문장 내용
                - user_id: 사용자 ID
                - post_id: 게시글 ID
                - created_at: 생성 시간
                - sentence_index: 문장 순서 (0부터 시작)
                
                ⭐ 추가 메타데이터 (문맥 정보):
                - prev_sentence: 이전 문장 내용
                - next_sentence: 다음 문장 내용
                - total_sentences: 전체 문장 수
                - is_first: 첫 문장 여부
                - is_last: 마지막 문장 여부
                - splitter_method: 분할 방법 ("kss" 또는 "regex")
                
                ⭐ 사용자 컨텍스트 (선택적):
                - user_activity_trend: 사용자 활동 추이
                - user_prev_posts_count: 이전 게시글 수
                - user_join_date: 가입일
        """
        if not text or not text.strip():
            return []
            
        # 기본값 설정
        if created_at is None:
            created_at = datetime.now()
            
        # 텍스트 전처리: 연속된 공백 제거, 줄바꿈 정리
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # 문장 분할 (KSS 우선, 실패 시 정규식)
        sentences = self._split_sentences(cleaned_text)
        splitter_method = "kss" if self.kss_available else "regex"
        
        # 결과 리스트 생성
        result = []
        total_sentences = len(sentences)
        
        for i, sentence in enumerate(sentences):
            # 빈 문장이나 너무 짧은 문장 제외 (2글자 이하)
            if len(sentence.strip()) <= 2:
                continue
            
            # 기본 메타데이터
            sentence_dict = {
                # 기본 정보
                "sentence": sentence.strip(),
                "user_id": user_id,
                "post_id": post_id,
                "created_at": created_at,
                "sentence_index": i,
                
                # ⭐ 문맥 정보 (문장 독립성 해결)
                "prev_sentence": sentences[i-1].strip() if i > 0 else "",
                "next_sentence": sentences[i+1].strip() if i < total_sentences-1 else "",
                "total_sentences": total_sentences,
                "is_first": (i == 0),
                "is_last": (i == total_sentences-1),
                
                # 분할 방법 기록
                "splitter_method": splitter_method
            }
            
            # ⭐ 사용자 컨텍스트 추가 (선택적)
            if user_context:
                # 제목 추가 (가장 중요한 문맥 정보)
                if "title" in user_context:
                    sentence_dict["title"] = user_context["title"]
                
                if "activity_trend" in user_context:
                    sentence_dict["user_activity_trend"] = user_context["activity_trend"]
                if "prev_posts_count" in user_context:
                    sentence_dict["user_prev_posts_count"] = user_context["prev_posts_count"]
                if "join_date" in user_context:
                    sentence_dict["user_join_date"] = user_context["join_date"]
                if "recent_activity_score" in user_context:
                    sentence_dict["user_recent_activity_score"] = user_context["recent_activity_score"]
            
            result.append(sentence_dict)
            
        return result
    
    def _fix_incomplete_splits(self, sentences: List[str]) -> List[str]:
        """
        잘못 분할된 문장들을 복구하는 후처리
        
        KSS가 "~봐자", "~해야지", "~가야지" 등을 잘못 분할하는 경우를 수정
        예: ["여기 있어봐", "자 소용없다"] → ["여기 있어봐자 소용없다"]
        
        Args:
            sentences (List[str]): 분할된 문장 리스트
            
        Returns:
            List[str]: 복구된 문장 리스트
        """
        if len(sentences) <= 1:
            return sentences
        
        corrected = []
        i = 0
        
        while i < len(sentences):
            current = sentences[i].strip()
            
            # 마지막 문장이 아니면 다음 문장과의 병합 체크
            if i < len(sentences) - 1:
                next_sent = sentences[i + 1].strip()
                
                # 패턴 1: 다음 문장이 "자"로 시작하는 경우
                # "~봐자", "~해야지", "~가야지" 등의 패턴 복구
                if next_sent.startswith('자 ') or next_sent == '자':
                    merged = current + next_sent
                    corrected.append(merged)
                    logger.debug(f"문장 병합: '{current}' + '{next_sent}' → '{merged}'")
                    i += 2
                    continue
                
                # 패턴 2: 현재 문장이 불완전한 조사로 끝나는 경우
                # "~면", "~는", "~은", "~고" 등으로 끝나는 경우
                incomplete_endings = ['면', '는', '은', '이', '가', '를', '에', '고', '서', '며']
                if any(current.endswith(ending) for ending in incomplete_endings):
                    # 다음 문장이 너무 짧으면(10자 이하) 병합
                    if len(next_sent) <= 10:
                        merged = current + ' ' + next_sent
                        corrected.append(merged)
                        logger.debug(f"불완전 문장 병합: '{current}' + '{next_sent}' → '{merged}'")
                        i += 2
                        continue
            
            # 병합하지 않는 경우 그대로 추가
            corrected.append(current)
            i += 1
        
        return corrected
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        실제 문장 분할 로직 (KSS 우선, 실패 시 정규식 Fallback)
        
        Args:
            text (str): 분할할 텍스트
            
        Returns:
            List[str]: 분할된 문장 리스트
        """
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1단계: KSS 시도 (한국어 특화)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if self.kss_available:
            try:
                # KSS 6.0+ 간단한 API 사용
                sentences = self.kss.split_sentences(text)
                
                # 빈 문장 제거
                sentences = [s.strip() for s in sentences if s.strip()]
                
                # ⭐ 후처리: 잘못 분할된 "~자" 패턴 복구
                # 예: "여기 있어봐" + "자 소용없다" → "여기 있어봐자 소용없다"
                sentences = self._fix_incomplete_splits(sentences)
                
                if sentences:  # 성공
                    logger.debug(f"KSS로 {len(sentences)}개 문장 분할 완료 (후처리 적용)")
                    return sentences
                    
            except Exception as e:
                logger.warning(f"KSS 분할 실패, 정규식 fallback 사용: {e}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2단계: Fallback - 정규식 방식
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        sentences = self.sentence_pattern.split(text)
        
        # 빈 문자열 제거 및 공백 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 문장 부호 후처리
        processed_sentences = []
        for sentence in sentences:
            # 문장이 문장부호로 끝나지 않는 경우 마침표 추가
            if sentence and sentence[-1] not in '.!?':
                # 10글자 이상인 경우만 마침표 추가
                if len(sentence) > 10:
                    sentence += '.'
            processed_sentences.append(sentence)
        
        logger.debug(f"정규식으로 {len(processed_sentences)}개 문장 분할 완료")
        return processed_sentences
    
    def split_multiple_texts(
        self, 
        texts_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        여러 텍스트를 한번에 분할 처리
        
        Args:
            texts_data (List[Dict]): 텍스트 데이터 리스트
                각 딕셔너리는 다음 키를 포함해야 함:
                - text: 분할할 텍스트
                - user_id: 사용자 ID (선택)
                - post_id: 게시글 ID (선택)
                - created_at: 생성 시간 (선택)
                
        Returns:
            List[Dict[str, Any]]: 모든 문장들의 리스트
        """
        all_sentences = []
        
        for text_data in texts_data:
            text = text_data.get('text', '')
            user_id = text_data.get('user_id')
            post_id = text_data.get('post_id')
            created_at = text_data.get('created_at')
            
            sentences = self.split_text(
                text=text,
                user_id=user_id,
                post_id=post_id,
                created_at=created_at
            )
            
            all_sentences.extend(sentences)
            
        return all_sentences


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 편의 함수 (Backward Compatibility)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def split_text_to_sentences(
    text: str, 
    user_id: Optional[str] = None, 
    post_id: Optional[str] = None,
    created_at: Optional[datetime] = None,
    use_kss: bool = True,
    user_context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    텍스트를 문장 단위로 분할하는 편의 함수 (KSS + 메타데이터 강화)
    
    Args:
        text (str): 분할할 원문 텍스트
        user_id (str, optional): 사용자 ID
        post_id (str, optional): 게시글 ID
        created_at (datetime, optional): 생성 시간
        use_kss (bool): KSS 사용 여부 (기본값: True)
        user_context (dict, optional): 사용자 컨텍스트 정보
        
    Returns:
        List[Dict[str, Any]]: 강화된 메타데이터를 포함한 문장 리스트
    """
    splitter = TextSplitter(use_kss=use_kss)
    return splitter.split_text(text, user_id, post_id, created_at, user_context)