"""
텍스트 분할기 모듈
긴 텍스트를 문장 단위로 나누는 기능을 제공합니다.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class TextSplitter:
    """
    텍스트를 문장 단위로 분할하는 클래스
    """
    
    def __init__(self):
        # 한국어 문장 분할을 위한 정규표현식 패턴
        # 마침표, 물음표, 느낌표 뒤에 공백이나 줄바꿈이 오는 경우를 문장의 끝으로 판단
        self.sentence_pattern = re.compile(r'[.!?]+\s*(?=\s|$|\n)')
        
    def split_text(
        self, 
        text: str, 
        user_id: Optional[str] = None, 
        post_id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        텍스트를 문장 단위로 분할하여 메타데이터와 함께 반환
        
        Args:
            text (str): 분할할 원문 텍스트
            user_id (str, optional): 사용자 ID
            post_id (str, optional): 게시글 ID  
            created_at (datetime, optional): 생성 시간
            
        Returns:
            List[Dict[str, Any]]: 문장별 딕셔너리 리스트
                각 딕셔너리는 다음 키를 포함:
                - sentence: 문장 내용
                - user_id: 사용자 ID
                - post_id: 게시글 ID
                - created_at: 생성 시간
                - sentence_index: 문장 순서 (0부터 시작)
        """
        if not text or not text.strip():
            return []
            
        # 기본값 설정
        if created_at is None:
            created_at = datetime.now()
            
        # 텍스트 전처리: 연속된 공백 제거, 줄바꿈 정리
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # 문장 분할
        sentences = self._split_sentences(cleaned_text)
        
        # 결과 리스트 생성
        result = []
        for i, sentence in enumerate(sentences):
            # 빈 문장이나 너무 짧은 문장 제외 (2글자 이하)
            if len(sentence.strip()) <= 2:
                continue
                
            sentence_dict = {
                "sentence": sentence.strip(),
                "user_id": user_id,
                "post_id": post_id,
                "created_at": created_at,
                "sentence_index": i
            }
            result.append(sentence_dict)
            
        return result
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        실제 문장 분할 로직
        
        Args:
            text (str): 분할할 텍스트
            
        Returns:
            List[str]: 분할된 문장 리스트
        """
        # 정규표현식으로 문장 분할
        sentences = self.sentence_pattern.split(text)
        
        # 빈 문자열 제거 및 공백 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 문장 부호가 제거된 경우를 위한 후처리
        processed_sentences = []
        for sentence in sentences:
            # 문장이 문장부호로 끝나지 않는 경우 마침표 추가
            if sentence and not sentence[-1] in '.!?':
                # 단, 마지막 문장이거나 명백히 완결된 문장인 경우만
                if len(sentence) > 10:  # 10글자 이상인 경우만 마침표 추가
                    sentence += '.'
            processed_sentences.append(sentence)
            
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


# 편의를 위한 함수형 인터페이스
def split_text_to_sentences(
    text: str, 
    user_id: Optional[str] = None, 
    post_id: Optional[str] = None,
    created_at: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    텍스트를 문장 단위로 분할하는 편의 함수
    
    Args:
        text (str): 분할할 원문 텍스트
        user_id (str, optional): 사용자 ID
        post_id (str, optional): 게시글 ID
        created_at (datetime, optional): 생성 시간
        
    Returns:
        List[Dict[str, Any]]: 문장별 딕셔너리 리스트
    """
    splitter = TextSplitter()
    return splitter.split_text(text, user_id, post_id, created_at)
