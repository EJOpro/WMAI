"""
RAG 기반 위험 보고서 생성 모듈
새로운 게시글/댓글을 분석하여 관리자용 위험 보고서를 생성합니다.
"""

import random
import math
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

from .text_splitter import TextSplitter
from .risk_scorer import RiskScorer, THRESHOLD
from .vector_store import get_vector_store
from .embedding_service import get_embedding
from .high_risk_store import get_recent_high_risk


def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    두 벡터 간의 코사인 유사도를 계산
    
    Args:
        vec1 (List[float]): 첫 번째 벡터
        vec2 (List[float]): 두 번째 벡터
        
    Returns:
        float: 코사인 유사도 (0.0~1.0, 높을수록 유사)
        
    Note:
        코사인 유사도 = (A·B) / (||A|| * ||B||)
        여기서 A·B는 내적, ||A||는 벡터 A의 크기(norm)
    """
    if len(vec1) != len(vec2):
        return 0.0
        
    # 내적 계산 (dot product)
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # 각 벡터의 크기 계산 (magnitude/norm)
    magnitude_a = math.sqrt(sum(a * a for a in vec1))
    magnitude_b = math.sqrt(sum(b * b for b in vec2))
    
    # 0으로 나누기 방지
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0
    
    # 코사인 유사도 계산
    cosine_sim = dot_product / (magnitude_a * magnitude_b)
    
    # -1~1 범위를 0~1 범위로 정규화 (선택사항)
    # return (cosine_sim + 1.0) / 2.0
    
    # 음수 유사도는 0으로 처리 (일반적으로 유사하지 않음을 의미)
    return max(0.0, cosine_sim)


class RAGReporter:
    """
    RAG 파이프라인을 사용하여 위험 보고서를 생성하는 클래스
    """
    
    def __init__(self):
        self.text_splitter = TextSplitter()
        self.risk_scorer = RiskScorer()
        self.vector_store = get_vector_store()
        
        # 우선순위 결정을 위한 임계값들
        self.priority_thresholds = {
            'HIGH': 0.8,      # 매우 높은 위험
            'MEDIUM': 0.6,    # 중간 위험
            'LOW': 0.4        # 낮은 위험
        }
        
        # 제안 액션 템플릿들
        self.action_templates = {
            'HIGH': [
                "즉시 1:1 DM으로 불만사항 확인 및 해결 방안 제시",
                "고객 서비스팀 에스컬레이션 및 우선 처리",
                "개인 맞춤 혜택 제공으로 이탈 방지"
            ],
            'MEDIUM': [
                "1:1 DM으로 서비스 이용 현황 확인",
                "FAQ 또는 가이드 자료 제공",
                "커뮤니티 매니저 모니터링 강화"
            ],
            'LOW': [
                "일반적인 고객 만족도 조사 진행",
                "정기적인 서비스 개선 안내",
                "커뮤니티 활동 독려"
            ]
        }
    
    def generate_risk_report(
        self, 
        new_post_text: str, 
        user_id: str, 
        post_id: str, 
        created_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        새로운 게시글/댓글에 대한 위험 보고서 생성
        
        Args:
            new_post_text (str): 새로 작성된 게시글/댓글 텍스트
            user_id (str): 작성자 사용자 ID
            post_id (str): 게시글 ID
            created_at (datetime, optional): 작성 시간
            
        Returns:
            Dict[str, Any]: 관리자용 위험 보고서
                - suspicious_user_id: 의심 사용자 ID
                - evidence_sentences: 위험 문장들
                - similar_patterns: 유사한 패턴의 기존 문장들
                - why_flagged: 플래그된 이유
                - suggested_action: 제안 조치사항
                - priority: 우선순위 (HIGH/MEDIUM/LOW)
                - risk_score: 전체 위험 점수
                - analysis_timestamp: 분석 시간
        """
        if created_at is None:
            created_at = datetime.now()
            
        # 1. 텍스트를 문장 단위로 분할
        sentences = self.text_splitter.split_text(
            text=new_post_text,
            user_id=user_id,
            post_id=post_id,
            created_at=created_at
        )
        
        if not sentences:
            return self._create_empty_report(user_id, post_id)
        
        # 2. 각 문장의 위험 점수 계산
        scoring_result = self.risk_scorer.score_sentences(
            sentences, 
            store_high_risk=False  # 보고서 생성 시에는 저장하지 않음
        )
        
        # 새로운 리턴 형태에서 데이터 추출
        scored_sentences = scoring_result.get('all_scored', [])
        high_risk_candidates = scoring_result.get('high_risk_candidates', [])
        
        # 3. 고위험 문장들 추출 (임계값 기준)
        high_risk_sentences = [
            s for s in scored_sentences 
            if s.get('risk_score', 0.0) >= THRESHOLD
        ]
        
        # 4. 각 고위험 문장에 대해 유사한 패턴 검색
        similar_patterns = []
        for sentence_data in high_risk_sentences:
            sentence = sentence_data.get('sentence', '')
            
            # 실제 임베딩 생성
            try:
                embedding = get_embedding(sentence)
                
                # high_risk_store에서 confirmed=true인 항목들과 유사도 비교
                confirmed_chunks = self._get_confirmed_high_risk_chunks()
                
                # 유사한 문장들 찾기
                similar_chunks = self._find_similar_chunks(
                    query_embedding=embedding,
                    candidate_chunks=confirmed_chunks,
                    top_k=3,
                    similarity_threshold=0.7
                )
                
                # 현재 문장 정보와 함께 저장
                for chunk in similar_chunks:
                    chunk['query_sentence'] = sentence
                    chunk['query_risk_score'] = sentence_data.get('risk_score', 0.0)
                
                similar_patterns.extend(similar_chunks)
                
            except Exception as e:
                print(f"[WARN] 유사도 검색 실패 (문장: {sentence[:50]}...): {e}")
                continue
        
        # 5. 보고서 생성
        report = self._generate_report_content(
            user_id=user_id,
            post_id=post_id,
            scored_sentences=scored_sentences,
            high_risk_sentences=high_risk_sentences,
            similar_patterns=similar_patterns,
            created_at=created_at
        )
        
        return report
    
    def _get_confirmed_high_risk_chunks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        confirmed=true인 고위험 문장들을 조회
        
        Args:
            limit (int): 조회할 최대 개수
            
        Returns:
            List[Dict[str, Any]]: 확인된 고위험 문장들
        """
        try:
            # 최근 고위험 문장들 조회
            all_chunks = get_recent_high_risk(limit=limit)
            
            # confirmed=true인 항목들만 필터링
            confirmed_chunks = [
                chunk for chunk in all_chunks 
                if chunk.get('confirmed', False) == True
            ]
            
            print(f"[INFO] 확인된 고위험 문장 {len(confirmed_chunks)}개 조회 (전체 {len(all_chunks)}개 중)")
            return confirmed_chunks
            
        except Exception as e:
            print(f"[ERROR] 확인된 고위험 문장 조회 실패: {e}")
            return []
    
    def _find_similar_chunks(
        self, 
        query_embedding: List[float], 
        candidate_chunks: List[Dict[str, Any]], 
        top_k: int = 3,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        쿼리 임베딩과 유사한 청크들을 찾기
        
        Args:
            query_embedding (List[float]): 쿼리 문장의 임베딩
            candidate_chunks (List[Dict]): 후보 청크들
            top_k (int): 반환할 최대 개수
            similarity_threshold (float): 유사도 임계값
            
        Returns:
            List[Dict[str, Any]]: 유사한 청크들 (유사도 순으로 정렬)
        """
        if not candidate_chunks:
            return []
            
        similarities = []
        
        for chunk in candidate_chunks:
            sentence = chunk.get('sentence', '')
            if not sentence:
                continue
                
            try:
                # 후보 문장의 임베딩 생성
                candidate_embedding = get_embedding(sentence)
                
                # 코사인 유사도 계산
                similarity = calculate_cosine_similarity(query_embedding, candidate_embedding)
                
                # 임계값 이상인 경우만 포함
                if similarity >= similarity_threshold:
                    chunk_with_similarity = chunk.copy()
                    chunk_with_similarity['similarity_score'] = similarity
                    similarities.append(chunk_with_similarity)
                    
            except Exception as e:
                print(f"[WARN] 임베딩 생성 실패 (문장: {sentence[:30]}...): {e}")
                continue
        
        # 유사도 순으로 정렬하고 상위 k개 반환
        similarities.sort(key=lambda x: x.get('similarity_score', 0.0), reverse=True)
        
        result = similarities[:top_k]
        print(f"[INFO] 유사한 문장 {len(result)}개 발견 (임계값: {similarity_threshold})")
        
        return result
    
    def _get_embedding(self, sentence: str) -> List[float]:
        """
        문장의 벡터 임베딩을 생성
        
        Args:
            sentence (str): 임베딩을 생성할 문장
            
        Returns:
            List[float]: 벡터 임베딩
            
        Note: 
            이제 실제 embedding_service.get_embedding()을 사용합니다.
            이 메서드는 하위 호환성을 위해 유지됩니다.
        """
        try:
            return get_embedding(sentence)
        except Exception as e:
            print(f"[ERROR] 임베딩 생성 실패: {e}")
            # fallback: 768차원 랜덤 벡터
            embedding_dim = 768
            return [random.uniform(-1.0, 1.0) for _ in range(embedding_dim)]
    
    def _generate_report_content(
        self,
        user_id: str,
        post_id: str,
        scored_sentences: List[Dict[str, Any]],
        high_risk_sentences: List[Dict[str, Any]],
        similar_patterns: List[Dict[str, Any]],
        created_at: datetime
    ) -> Dict[str, Any]:
        """
        보고서 내용 생성
        
        Args:
            user_id (str): 사용자 ID
            post_id (str): 게시글 ID
            scored_sentences (List[Dict]): 점수가 계산된 모든 문장들
            high_risk_sentences (List[Dict]): 고위험 문장들
            similar_patterns (List[Dict]): 유사한 패턴의 기존 문장들
            created_at (datetime): 작성 시간
            
        Returns:
            Dict[str, Any]: 생성된 보고서
        """
        # 전체 위험 점수 계산
        if scored_sentences:
            total_risk_score = sum(s.get('risk_score', 0.0) for s in scored_sentences)
            avg_risk_score = total_risk_score / len(scored_sentences)
        else:
            avg_risk_score = 0.0
        
        # 우선순위 결정
        priority = self._determine_priority(avg_risk_score, len(high_risk_sentences))
        
        # 플래그된 이유 생성
        why_flagged = self._generate_flag_reason(high_risk_sentences, similar_patterns)
        
        # 제안 조치사항 생성
        suggested_action = self._generate_suggested_action(priority, high_risk_sentences)
        
        # 증거 문장들 추출
        evidence_sentences = [s.get('sentence', '') for s in high_risk_sentences]
        
        # 유사 패턴 요약
        similar_pattern_summary = self._summarize_similar_patterns(similar_patterns)
        
        return {
            "suspicious_user_id": user_id,
            "post_id": post_id,
            "evidence_sentences": evidence_sentences,
            "similar_patterns": similar_pattern_summary,
            "why_flagged": why_flagged,
            "suggested_action": suggested_action,
            "priority": priority,
            "risk_score": round(avg_risk_score, 3),
            "high_risk_count": len(high_risk_sentences),
            "total_sentences": len(scored_sentences),
            "analysis_timestamp": datetime.now(),
            "post_created_at": created_at
        }
    
    def _determine_priority(self, avg_risk_score: float, high_risk_count: int) -> str:
        """
        우선순위 결정
        
        Args:
            avg_risk_score (float): 평균 위험 점수
            high_risk_count (int): 고위험 문장 개수
            
        Returns:
            str: 우선순위 (HIGH/MEDIUM/LOW)
        """
        # TODO: 실제 LLM 기반 우선순위 결정 로직 구현
        # 현재는 단순한 규칙 기반 결정
        
        if avg_risk_score >= self.priority_thresholds['HIGH'] or high_risk_count >= 3:
            return 'HIGH'
        elif avg_risk_score >= self.priority_thresholds['MEDIUM'] or high_risk_count >= 1:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_flag_reason(
        self, 
        high_risk_sentences: List[Dict[str, Any]], 
        similar_patterns: List[Dict[str, Any]]
    ) -> str:
        """
        플래그된 이유 생성
        
        Args:
            high_risk_sentences (List[Dict]): 고위험 문장들
            similar_patterns (List[Dict]): 유사한 패턴들
            
        Returns:
            str: 플래그된 이유 설명
        """
        if not high_risk_sentences:
            return "위험 요소가 감지되지 않음"
        
        # 위험 요소 분석
        all_risk_factors = []
        for sentence in high_risk_sentences:
            risk_factors = sentence.get('risk_factors', [])
            all_risk_factors.extend(risk_factors)
        
        # 가장 빈번한 위험 요소 찾기
        factor_counts = Counter(all_risk_factors)
        
        if not factor_counts:
            return "일반적인 위험 패턴 감지"
        
        # TODO: LLM을 사용한 더 정교한 이유 생성
        # 현재는 규칙 기반 생성
        
        most_common_factor = factor_counts.most_common(1)[0][0]
        
        if "고위험_키워드" in most_common_factor:
            if any("그만둘" in factor or "포기" in factor for factor in all_risk_factors):
                return "탈퇴/포기 의도가 명시적으로 표현됨"
            elif any("싫어" in factor or "짜증" in factor for factor in all_risk_factors):
                return "서비스에 대한 강한 부정적 감정 표현"
            elif any("시간낭비" in factor or "의미없" in factor for factor in all_risk_factors):
                return "서비스 가치에 대한 회의적 표현"
            else:
                return "부정적 감정 및 불만 표현이 반복됨"
        elif "중위험_키워드" in most_common_factor:
            return "서비스 이용 중 어려움 및 불편함 호소"
        else:
            return "이탈 위험 패턴이 감지됨"
    
    def _generate_suggested_action(
        self, 
        priority: str, 
        high_risk_sentences: List[Dict[str, Any]]
    ) -> str:
        """
        제안 조치사항 생성
        
        Args:
            priority (str): 우선순위
            high_risk_sentences (List[Dict]): 고위험 문장들
            
        Returns:
            str: 제안 조치사항
        """
        # TODO: LLM을 사용한 맞춤형 조치사항 생성
        # 현재는 템플릿 기반 생성
        
        templates = self.action_templates.get(priority, self.action_templates['LOW'])
        
        # 위험 요소에 따른 맞춤형 선택 (간단한 규칙)
        if high_risk_sentences:
            risk_factors = []
            for sentence in high_risk_sentences:
                risk_factors.extend(sentence.get('risk_factors', []))
            
            if any("그만둘" in factor or "포기" in factor for factor in risk_factors):
                # 탈퇴 의도가 명확한 경우
                return templates[0] if len(templates) > 0 else "긴급 고객 상담 필요"
            elif any("어려워" in factor or "복잡해" in factor for factor in risk_factors):
                # 사용성 문제인 경우
                return templates[1] if len(templates) > 1 else "사용법 안내 및 지원 필요"
        
        # 기본 템플릿 반환
        return templates[0] if templates else "일반적인 고객 관리 필요"
    
    def _summarize_similar_patterns(self, similar_patterns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        유사한 패턴들을 요약
        
        Args:
            similar_patterns (List[Dict]): 유사한 패턴들
            
        Returns:
            List[Dict[str, str]]: 요약된 패턴 정보
        """
        if not similar_patterns:
            return []
        
        # 중복 제거 및 상위 3개만 선택
        unique_patterns = []
        seen_sentences = set()
        
        for pattern in similar_patterns:
            sentence = pattern.get('sentence', '')
            if sentence and sentence not in seen_sentences:
                unique_patterns.append({
                    'sentence': sentence,
                    'user_id': pattern.get('user_id', 'unknown'),
                    'risk_score': pattern.get('risk_score', 0.0),
                    'similarity_score': pattern.get('similarity_score', 0.0)
                })
                seen_sentences.add(sentence)
                
                if len(unique_patterns) >= 3:
                    break
        
        return unique_patterns
    
    def _create_empty_report(self, user_id: str, post_id: str) -> Dict[str, Any]:
        """
        빈 보고서 생성 (분석할 내용이 없는 경우)
        
        Args:
            user_id (str): 사용자 ID
            post_id (str): 게시글 ID
            
        Returns:
            Dict[str, Any]: 빈 보고서
        """
        return {
            "suspicious_user_id": user_id,
            "post_id": post_id,
            "evidence_sentences": [],
            "similar_patterns": [],
            "why_flagged": "분석할 텍스트 내용이 없음",
            "suggested_action": "추가 모니터링 불필요",
            "priority": "LOW",
            "risk_score": 0.0,
            "high_risk_count": 0,
            "total_sentences": 0,
            "analysis_timestamp": datetime.now(),
            "post_created_at": datetime.now()
        }
    
    def generate_batch_reports(
        self, 
        posts_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        여러 게시글에 대한 일괄 보고서 생성
        
        Args:
            posts_data (List[Dict]): 게시글 데이터 리스트
                각 딕셔너리는 다음 키를 포함해야 함:
                - text: 게시글 텍스트
                - user_id: 사용자 ID
                - post_id: 게시글 ID
                - created_at: 작성 시간 (선택)
                
        Returns:
            List[Dict[str, Any]]: 보고서 리스트
        """
        reports = []
        
        for post_data in posts_data:
            try:
                report = self.generate_risk_report(
                    new_post_text=post_data.get('text', ''),
                    user_id=post_data.get('user_id', ''),
                    post_id=post_data.get('post_id', ''),
                    created_at=post_data.get('created_at')
                )
                reports.append(report)
            except Exception as e:
                # 개별 게시글 처리 실패 시 에러 보고서 생성
                error_report = self._create_error_report(
                    post_data.get('user_id', 'unknown'),
                    post_data.get('post_id', 'unknown'),
                    str(e)
                )
                reports.append(error_report)
        
        return reports
    
    def _create_error_report(self, user_id: str, post_id: str, error_msg: str) -> Dict[str, Any]:
        """
        에러 보고서 생성
        
        Args:
            user_id (str): 사용자 ID
            post_id (str): 게시글 ID
            error_msg (str): 에러 메시지
            
        Returns:
            Dict[str, Any]: 에러 보고서
        """
        return {
            "suspicious_user_id": user_id,
            "post_id": post_id,
            "evidence_sentences": [],
            "similar_patterns": [],
            "why_flagged": f"분석 중 오류 발생: {error_msg}",
            "suggested_action": "수동 검토 필요",
            "priority": "MEDIUM",
            "risk_score": 0.0,
            "high_risk_count": 0,
            "total_sentences": 0,
            "analysis_timestamp": datetime.now(),
            "post_created_at": datetime.now(),
            "error": True
        }


# 편의를 위한 함수형 인터페이스
def generate_risk_report(
    new_post_text: str, 
    user_id: str, 
    post_id: str, 
    created_at: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    위험 보고서 생성 편의 함수
    
    Args:
        new_post_text (str): 새로 작성된 게시글/댓글 텍스트
        user_id (str): 작성자 사용자 ID
        post_id (str): 게시글 ID
        created_at (datetime, optional): 작성 시간
        
    Returns:
        Dict[str, Any]: 관리자용 위험 보고서
    """
    reporter = RAGReporter()
    return reporter.generate_risk_report(new_post_text, user_id, post_id, created_at)
