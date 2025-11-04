"""
위험 점수 계산기 모듈
각 문장에 대해 이탈 위험 점수를 계산하고, 고위험 문장을 벡터 DB에 저장하는 기능을 제공합니다.
"""

import random
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# OpenAI API 설정
try:
    import openai
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
        print("[INFO] OpenAI API 키가 설정되었습니다.")
    else:
        print("[WARN] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
except ImportError:
    print("[WARN] openai 패키지가 설치되지 않았습니다. pip install openai 를 실행해주세요.")
    openai = None

# 고위험 문장 판단 임계값
THRESHOLD = 0.75


class RiskScorer:
    """
    문장별 이탈 위험 점수를 계산하는 클래스
    """
    
    def __init__(self):
        # 위험 키워드 패턴들 (추후 확장 가능)
        self.risk_keywords = {
            'high_risk': [
                '그만둘', '포기', '떠날', '나갈', '싫어', '짜증', '화나', '실망',
                '의미없', '소용없', '헛된', '시간낭비', '별로', '최악'
            ],
            'medium_risk': [
                '어려워', '힘들어', '복잡해', '모르겠', '이해안돼', '답답해',
                '지쳐', '피곤해', '귀찮아', '번거로워'
            ],
            'low_risk': [
                '괜찮', '좋아', '재미있', '흥미로', '도움', '유용해',
                '만족', '행복', '즐거워', '기대돼'
            ]
        }
        
    def score_sentences(
        self, 
        sentences: List[Dict[str, Any]], 
        store_high_risk: bool = False  # 기본값을 False로 변경 (DB 저장 안함)
    ) -> Dict[str, Any]:
        """
        문장 리스트에 대해 이탈 위험 점수를 계산하여 추가
        
        Args:
            sentences (List[Dict]): 문장 데이터 리스트
                각 딕셔너리는 다음 키를 포함해야 함:
                - sentence: 문장 내용
                - user_id: 사용자 ID (선택)
                - post_id: 게시글 ID (선택)
                - created_at: 생성 시간 (선택)
                - sentence_index: 문장 순서 (선택)
            store_high_risk (bool): 고위험 문장을 벡터 DB에 저장할지 여부 (기본값: False)
                
        Returns:
            Dict[str, Any]: 분석 결과 딕셔너리
                - all_scored: 위험 점수가 추가된 모든 문장 리스트
                - high_risk_candidates: 임계값을 넘은 고위험 문장들 리스트
        """
        scored_sentences = []
        high_risk_candidates = []  # 임계값을 넘은 고위험 문장들
        
        print(f"[INFO] {len(sentences)}개 문장에 대한 이탈 위험도 분석을 시작합니다...")
        
        for i, sentence_data in enumerate(sentences):
            sentence = sentence_data.get('sentence', '')
            
            print(f"[INFO] 문장 {i+1}/{len(sentences)} 분석 중: {sentence[:50]}...")
            
            # 실제 LLM을 사용한 위험 점수 계산
            # 이 부분은 실제 LLM 호출이며, 운영 시 비용이 든다
            risk_score = self._call_llm_for_risk_analysis(sentence)
            
            # 위험 레벨 결정 (THRESHOLD 기준 적용)
            if risk_score >= THRESHOLD:
                risk_level = 'high'
            elif risk_score >= 0.4:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            # 고위험 문장 판단
            is_high_risk = risk_score >= THRESHOLD
            
            # 기존 데이터에 위험 점수 정보 추가
            scored_data = sentence_data.copy()
            scored_data.update({
                'risk_score': risk_score,
                'risk_level': risk_level,
                'analyzed_at': datetime.now(),
                'is_high_risk': is_high_risk
            })
            
            scored_sentences.append(scored_data)
            
            # 고위험 문장은 별도 리스트에 추가
            if is_high_risk:
                high_risk_candidates.append(scored_data)
                print(f"[WARN] 고위험 문장 발견 (점수: {risk_score:.3f}): {sentence[:100]}...")
        
        print(f"[INFO] 분석 완료. 총 {len(scored_sentences)}개 문장 중 {len(high_risk_candidates)}개가 고위험으로 분류됨")
        
        # 고위험 문장들을 관리자 대시보드용 저장소에 저장
        if high_risk_candidates:
            self._save_to_high_risk_store(high_risk_candidates)
        
        # 고위험 문장들을 벡터 DB에 저장 (옵션)
        if store_high_risk and high_risk_candidates:
            self._store_high_risk_sentences(high_risk_candidates)
            
        # 새로운 리턴 형태
        return {
            "all_scored": scored_sentences,
            "high_risk_candidates": high_risk_candidates
        }
    
    def _calculate_risk_score(self, sentence: str) -> tuple[float, str, List[str]]:
        """
        단일 문장에 대한 위험 점수 계산
        
        Args:
            sentence (str): 분석할 문장
            
        Returns:
            tuple: (위험점수, 위험레벨, 위험요소리스트)
        """
        if not sentence or not sentence.strip():
            return 0.0, 'low', []
            
        sentence_lower = sentence.lower()
        risk_factors = []
        base_score = 0.0
        
        # TODO: 실제 LLM 호출로 대체 예정
        # 현재는 키워드 기반 간단한 점수 계산
        
        # 고위험 키워드 체크
        high_risk_count = 0
        for keyword in self.risk_keywords['high_risk']:
            if keyword in sentence_lower:
                high_risk_count += 1
                risk_factors.append(f"고위험_키워드: {keyword}")
                
        # 중위험 키워드 체크  
        medium_risk_count = 0
        for keyword in self.risk_keywords['medium_risk']:
            if keyword in sentence_lower:
                medium_risk_count += 1
                risk_factors.append(f"중위험_키워드: {keyword}")
                
        # 저위험(긍정) 키워드 체크
        low_risk_count = 0
        for keyword in self.risk_keywords['low_risk']:
            if keyword in sentence_lower:
                low_risk_count += 1
                risk_factors.append(f"긍정_키워드: {keyword}")
        
        # 점수 계산 로직
        base_score = (high_risk_count * 0.4) + (medium_risk_count * 0.2) - (low_risk_count * 0.1)
        
        # 문장 길이 고려 (너무 짧거나 긴 문장은 점수 조정)
        sentence_length = len(sentence.strip())
        if sentence_length < 10:
            base_score *= 0.5  # 짧은 문장은 점수 감소
        elif sentence_length > 100:
            base_score *= 1.2  # 긴 문장은 점수 증가
            
        # TODO: 여기에 실제 LLM API 호출 로직 추가 예정
        # 예시:
        # llm_score = await self._call_llm_for_risk_analysis(sentence)
        # base_score = (base_score + llm_score) / 2
        
        # 임시로 약간의 랜덤성 추가 (실제 LLM 결과 시뮬레이션)
        random_factor = random.uniform(-0.1, 0.1)
        final_score = max(0.0, min(1.0, base_score + random_factor))
        
        # 위험 레벨 결정 (THRESHOLD 기준 적용)
        if final_score >= THRESHOLD:
            risk_level = 'high'
        elif final_score >= 0.4:
            risk_level = 'medium'
        else:
            risk_level = 'low'
            
        return final_score, risk_level, risk_factors
    
    def _store_high_risk_sentences(self, high_risk_sentences: List[Dict[str, Any]]) -> None:
        """
        고위험 문장들을 벡터 DB에 저장
        
        Args:
            high_risk_sentences (List[Dict]): 고위험 문장 리스트
        """
        try:
            # 벡터 스토어 import (지연 import로 순환 참조 방지)
            from .vector_store import upsert_high_risk_chunk
            
            for sentence_data in high_risk_sentences:
                sentence = sentence_data.get('sentence', '')
                
                # 임베딩 생성
                embedding = self._get_embedding(sentence)
                
                # 메타데이터 준비
                metadata_dict = {
                    "user_id": sentence_data.get('user_id'),
                    "post_id": sentence_data.get('post_id'),
                    "sentence": sentence,
                    "risk_score": sentence_data.get('risk_score'),
                    "created_at": sentence_data.get('created_at'),
                    "sentence_index": sentence_data.get('sentence_index'),
                    "risk_level": sentence_data.get('risk_level'),
                    "risk_factors": sentence_data.get('risk_factors', []),
                    "analyzed_at": sentence_data.get('analyzed_at')
                }
                
                # 벡터 DB에 저장
                upsert_high_risk_chunk(embedding, metadata_dict)
                
        except ImportError as e:
            print(f"[WARN] 벡터 스토어 모듈을 불러올 수 없습니다: {e}")
        except Exception as e:
            print(f"[ERROR] 고위험 문장 저장 중 오류 발생: {e}")
    
    def _get_embedding(self, sentence: str) -> List[float]:
        """
        문장의 벡터 임베딩을 생성
        
        Args:
            sentence (str): 임베딩을 생성할 문장
            
        Returns:
            List[float]: 벡터 임베딩 (1536차원)
            
        Note:
            실제 OpenAI 임베딩 서비스를 사용하여 벡터를 생성합니다.
            환경변수 OPENAI_API_KEY가 설정되어 있어야 합니다.
        """
        try:
            # embedding_service에서 실제 임베딩 생성
            from .embedding_service import get_embedding
            embedding = get_embedding(sentence)
            
            print(f"[DEBUG] 임베딩 생성 완료: {sentence[:30]}... -> {len(embedding)}차원")
            return embedding
            
        except ImportError as e:
            print(f"[WARN] embedding_service를 불러올 수 없습니다: {e}")
            # fallback: 임시 구현 - 1536차원 더미 벡터 생성
            embedding_dim = 1536
            embedding = [0.0] * embedding_dim
            print(f"[DEBUG] 더미 임베딩 생성: {sentence[:30]}... -> {embedding_dim}차원")
            return embedding
            
        except Exception as e:
            print(f"[ERROR] 임베딩 생성 중 오류 발생: {e}")
            # fallback: 더미 벡터 반환
            embedding_dim = 1536
            embedding = [0.0] * embedding_dim
            return embedding
    
    def _save_to_high_risk_store(self, high_risk_candidates: List[Dict[str, Any]]) -> None:
        """
        고위험 문장들을 관리자 대시보드용 저장소에 저장
        
        Args:
            high_risk_candidates (List[Dict]): 고위험 문장 리스트
        """
        try:
            # high_risk_store import (지연 import로 순환 참조 방지)
            from .high_risk_store import save_high_risk_chunk
            
            for sentence_data in high_risk_candidates:
                # 저장소용 데이터 준비
                chunk_dict = {
                    "user_id": sentence_data.get('user_id'),
                    "post_id": sentence_data.get('post_id'),
                    "sentence": sentence_data.get('sentence', ''),
                    "risk_score": sentence_data.get('risk_score', 0.0),
                    "created_at": sentence_data.get('created_at'),
                    "sentence_index": sentence_data.get('sentence_index'),
                    "risk_level": sentence_data.get('risk_level'),
                    "analyzed_at": sentence_data.get('analyzed_at')
                }
                
                # 고위험 저장소에 저장
                chunk_id = save_high_risk_chunk(chunk_dict)
                print(f"[INFO] 관리자 대시보드용 저장 완료: {chunk_id}")
                
        except ImportError as e:
            print(f"[WARN] high_risk_store 모듈을 불러올 수 없습니다: {e}")
        except Exception as e:
            print(f"[ERROR] 고위험 문장 저장소 저장 중 오류 발생: {e}")
    
    def _call_llm_for_risk_analysis(self, sentence: str) -> float:
        """
        LLM을 호출하여 문장의 이탈 위험도를 분석
        
        이 부분은 실제 LLM 호출이며, 운영 시 비용이 든다.
        OpenAI GPT API를 사용하여 문장의 이탈 위험도를 0.0~1.0 사이의 점수로 계산한다.
        
        Args:
            sentence (str): 분석할 문장
            
        Returns:
            float: 0.0~1.0 사이의 위험 점수 (실패 시 기본값 0.0)
        """
        if not sentence or not sentence.strip():
            return 0.0
            
        # OpenAI API가 사용 가능한지 확인
        if not openai or not OPENAI_API_KEY:
            print("[WARN] OpenAI API를 사용할 수 없습니다. 기본값 0.0을 반환합니다.")
            return 0.0
            
        try:
            # 이탈 위험도 분석을 위한 프롬프트
            prompt = f"""이 문장이 '서비스를 그만 쓸 것 같다 / 탈퇴할 것 같다 / 완전히 실망했다 / 가치가 없다' 같은 이탈 의도를 얼마나 강하게 표현하는지 0.00~1.00 숫자만 답해.

문장: "{sentence}"

평가 기준:
- 0.00~0.30: 긍정적이거나 중립적 (만족, 좋아함, 계속 사용 의도)
- 0.31~0.60: 약간의 불만이나 고민 (개선 요구, 아쉬움 표현)
- 0.61~0.80: 강한 불만이나 실망 (화남, 짜증, 문제 제기)
- 0.81~1.00: 이탈 의도 명확 (그만두기, 탈퇴, 포기 의사)

숫자만 답해:"""

            # OpenAI API 호출
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 사용자 이탈 위험도를 정확히 분석하는 전문가입니다. 주어진 문장을 분석하여 0.00~1.00 사이의 숫자만 정확히 답해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1  # 일관된 결과를 위해 낮은 temperature 사용
            )
            
            # 응답에서 점수 추출
            response_text = response.choices[0].message.content.strip()
            
            # 숫자만 추출 (소수점 포함)
            import re
            score_match = re.search(r'(\d+\.?\d*)', response_text)
            
            if score_match:
                score = float(score_match.group(1))
                # 0.0~1.0 범위로 정규화
                score = max(0.0, min(1.0, score))
                
                print(f"[DEBUG] LLM 분석 결과 - 문장: '{sentence[:30]}...' -> 점수: {score:.3f}")
                return score
            else:
                print(f"[WARN] LLM 응답에서 점수를 추출할 수 없습니다: {response_text}")
                return 0.0
                
        except openai.RateLimitError:
            print("[ERROR] OpenAI API 요청 한도 초과. 기본값 0.0을 반환합니다.")
            return 0.0
        except openai.AuthenticationError:
            print("[ERROR] OpenAI API 인증 실패. API 키를 확인해주세요.")
            return 0.0
        except Exception as e:
            print(f"[ERROR] LLM 호출 중 오류 발생: {e}. 기본값 0.0을 반환합니다.")
            return 0.0
    
    def get_risk_summary(self, scored_sentences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        분석된 문장들의 위험도 요약 정보 생성
        
        Args:
            scored_sentences (List[Dict]): 위험 점수가 계산된 문장 리스트
            
        Returns:
            Dict[str, Any]: 요약 정보
                - total_sentences: 총 문장 수
                - average_risk_score: 평균 위험 점수
                - high_risk_count: 고위험 문장 수 (>= THRESHOLD)
                - medium_risk_count: 중위험 문장 수
                - low_risk_count: 저위험 문장 수
                - high_risk_threshold: 고위험 판단 임계값
                - top_risk_sentences: 가장 위험한 문장들 (상위 3개)
        """
        if not scored_sentences:
            return {
                'total_sentences': 0,
                'average_risk_score': 0.0,
                'high_risk_count': 0,
                'medium_risk_count': 0,
                'low_risk_count': 0,
                'high_risk_threshold': THRESHOLD,
                'top_risk_sentences': []
            }
            
        total_sentences = len(scored_sentences)
        total_score = sum(s.get('risk_score', 0.0) for s in scored_sentences)
        average_score = total_score / total_sentences if total_sentences > 0 else 0.0
        
        # 위험 레벨별 카운트 (THRESHOLD 기준 적용)
        high_risk_count = sum(1 for s in scored_sentences if s.get('risk_score', 0.0) >= THRESHOLD)
        medium_risk_count = sum(1 for s in scored_sentences 
                               if 0.4 <= s.get('risk_score', 0.0) < THRESHOLD)
        low_risk_count = sum(1 for s in scored_sentences if s.get('risk_score', 0.0) < 0.4)
        
        # 가장 위험한 문장들 (상위 3개)
        sorted_sentences = sorted(
            scored_sentences, 
            key=lambda x: x.get('risk_score', 0.0), 
            reverse=True
        )
        top_risk_sentences = sorted_sentences[:3]
        
        return {
            'total_sentences': total_sentences,
            'average_risk_score': round(average_score, 3),
            'high_risk_count': high_risk_count,
            'medium_risk_count': medium_risk_count,
            'low_risk_count': low_risk_count,
            'high_risk_threshold': THRESHOLD,
            'top_risk_sentences': [
                {
                    'sentence': s.get('sentence', ''),
                    'risk_score': s.get('risk_score', 0.0),
                    'risk_factors': s.get('risk_factors', []),
                    'is_high_risk': s.get('is_high_risk', False)
                }
                for s in top_risk_sentences
            ]
        }
    
    def get_high_risk_sentences(self, scored_sentences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        고위험 문장들만 필터링하여 반환
        
        Args:
            scored_sentences (List[Dict]): 점수가 계산된 문장 리스트
            
        Returns:
            List[Dict[str, Any]]: 고위험 문장들 (risk_score >= THRESHOLD)
        """
        return [
            sentence for sentence in scored_sentences 
            if sentence.get('risk_score', 0.0) >= THRESHOLD
        ]


# 편의를 위한 함수형 인터페이스
def score_sentences(
    sentences: List[Dict[str, Any]], 
    store_high_risk: bool = False
) -> Dict[str, Any]:
    """
    문장들에 위험 점수를 계산하는 편의 함수
    
    Args:
        sentences (List[Dict]): 문장 데이터 리스트
        store_high_risk (bool): 고위험 문장을 벡터 DB에 저장할지 여부 (기본값: False)
        
    Returns:
        Dict[str, Any]: 분석 결과 딕셔너리
            - all_scored: 위험 점수가 추가된 모든 문장 리스트
            - high_risk_candidates: 임계값을 넘은 고위험 문장들 리스트
    """
    scorer = RiskScorer()
    return scorer.score_sentences(sentences, store_high_risk)


def get_high_risk_threshold() -> float:
    """
    고위험 판단 임계값 반환
    
    Returns:
        float: 고위험 임계값
    """
    return THRESHOLD