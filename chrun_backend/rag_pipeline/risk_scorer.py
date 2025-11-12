"""
위험 점수 계산기 모듈
각 문장에 대해 이탈 위험 점수를 계산하고, 고위험 문장을 벡터 DB에 저장하는 기능을 제공합니다.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 환경 변수 로드
load_dotenv()

# OpenAI API 설정
try:
    import openai
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
        print("[INFO] OpenAI API 키가 설정되었습니다.")
    else:
        print("[WARN] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
except ImportError:
    print("[WARN] openai 패키지가 설치되지 않았습니다. pip install openai 를 실행해주세요.")
    openai = None

class RiskThresholdSettings(BaseSettings):
    rag_risk_threshold: Optional[float] = None
    risk_threshold: float = 0.70  # 고위험 판단 임계값 (0.70 이상)

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


def _resolve_threshold() -> float:
    env_candidates = [
        os.getenv("RAG_THRESHOLD"),
        os.getenv("RAG_RISK_THRESHOLD"),
        os.getenv("RISK_THRESHOLD"),
    ]
    for value in env_candidates:
        if value is None:
            continue
        try:
            return float(value)
        except ValueError:
            continue

    settings = RiskThresholdSettings()
    if settings.rag_risk_threshold is not None:
        return float(settings.rag_risk_threshold)
    return float(settings.risk_threshold)


# 고위험 문장 판단 임계값
THRESHOLD = _resolve_threshold()
_THRESHOLD_LOGGED = False


class RiskScorer:
    """
    문장별 이탈 위험 점수를 계산하는 클래스
    """
    
    def __init__(self):
        global _THRESHOLD_LOGGED
        if not _THRESHOLD_LOGGED:
            print(f"[INFO] RiskScorer THRESHOLD 적용: {THRESHOLD:.2f}")
            _THRESHOLD_LOGGED = True

        # ⭐ LLM 분석 결과 캐시 (같은 문장은 같은 결과 반환)
        self._analysis_cache = {}
        
        # 위험 키워드 패턴들 (추후 확장 가능)
        # | 구분        | 가중치 | 예시 키워드(확장됨)                                   |
        # | HIGH       | +0.45  | 탈퇴, 그만둘, 최악, 꺼져, 지옥, 환멸                  |
        # | ABUSIVE    | +0.35  | 개같, 병신, 미친놈, 죽어, 엿같, 빡치                  |
        # | MEDIUM     | +0.25  | 힘들어, 답답해, 포기할까, 다른 곳, 불편               |
        # | LOW(완충)  | -0.20  | 만족, 고마워, 기대, 재밌, 추천, 도움                 |
        self.keyword_profiles = [
            {
                "level": "HIGH",
                "weight": 0.45,
                "keywords": [
                    '그만둘', '포기', '떠날', '나갈', '싫어', '짜증', '화나', '실망',
                    '의미없', '소용없', '헛된', '시간낭비', '별로', '최악', '탈퇴', '접을까',
                    '환멸', '지옥', '불매', '못해먹', '차단', '밴', '강퇴', '쫓겨'
                ],
            },
            {
                "level": "ABUSIVE",
                "weight": 0.35,
                "keywords": [
                    '꺼져', '죽어', '미친놈', '미친년', '개같', '병신', '씨발', '좆같',
                    '빡치', '지랄', '엿같', '돌아이', '쓰레기', '멍청이', '도랏', '개빡치'
                ],
            },
            {
                "level": "MEDIUM",
                "weight": 0.25,
                "keywords": [
                    '어려워', '힘들어', '복잡해', '모르겠', '이해안돼', '답답해',
                    '지쳐', '피곤해', '귀찮아', '번거로워', '짜증나', '열받', '다른 서비스',
                    '대안', '포기할까', '갈아탈', '마음이 떠났', '다른 곳', '옮길', '이동할',
                    '정지', '제재', '불공정', '억울'
                ],
            },
            {
                "level": "LOW",
                "weight": -0.2,
                "keywords": [
                    '괜찮', '좋아', '재미있', '흥미로', '도움', '유용해',
                    '만족', '행복', '즐거워', '기대돼', '감사', '추천', '고맙', '사랑',
                    '기쁨', '뿌듯', '든든'
                ],
            },
        ]
        
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
        
        print(f"[INFO] {len(sentences)}개 문장에 대한 이탈 위험도 분석을 시작합니다...", flush=True)
        
        for i, sentence_data in enumerate(sentences):
            sentence = sentence_data.get('sentence', '')
            
            print(f"[INFO] 문장 {i+1}/{len(sentences)} 분석 중: {sentence[:50]}...", flush=True)
            
            # ⭐ 문맥 정보 추출 (제목 + 이전/다음 문장)
            # 제목을 이전 문장 앞에 추가 (가장 중요한 문맥)
            title = sentence_data.get('title', '')
            prev_sentence = sentence_data.get('prev_sentence', '')
            next_sentence = sentence_data.get('next_sentence', '')
            
            # ⭐ 디버그: 제목 확인
            if title:
                print(f"[DEBUG] 제목 감지됨: '{title}' (문장: {sentence[:30]}...)", flush=True)
            
            # 제목이 있으면 문맥 강화
            if title and prev_sentence:
                prev_sentence = f"[제목: {title}] {prev_sentence}"
            elif title:
                prev_sentence = f"[제목: {title}]"
            
            # 실제 LLM을 사용한 위험 점수 계산 (문맥 정보 포함)
            # 이 부분은 실제 LLM 호출이며, 운영 시 비용이 든다
            analysis = self.score_sentence(sentence, prev_sentence, next_sentence)
            risk_score = analysis["risk_score"]
            risk_level = analysis["risk_level"]
            reasons = analysis["reasons"]
            
            # 고위험 문장 판단
            is_high_risk = risk_score >= THRESHOLD
            
            # 기존 데이터에 위험 점수 정보 추가
            scored_data = sentence_data.copy()
            scored_data.update({
                'risk_score': risk_score,
                'risk_level': risk_level,
                'analyzed_at': datetime.now(),
                'is_high_risk': is_high_risk,
                'risk_factors': reasons,
                'reason': "; ".join(reasons)
            })
            
            scored_sentences.append(scored_data)
            
            # 고위험 문장은 별도 리스트에 추가
            if is_high_risk:
                high_risk_candidates.append(scored_data)
                print(f"[WARN] 고위험 문장 발견 (점수: {risk_score:.3f}): {sentence[:100]}...", flush=True)
        
        print(f"[INFO] 분석 완료. 총 {len(scored_sentences)}개 문장 중 {len(high_risk_candidates)}개가 고위험으로 분류됨", flush=True)
        
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
    
    def score_sentence(self, sentence: str, prev_sentence: str = "", next_sentence: str = "", title: str = "") -> Dict[str, Any]:
        """
        단일 문장의 위험 점수와 근거를 계산합니다.
        
        Args:
            sentence (str): 분석할 문장
            prev_sentence (str, optional): 이전 문장 (문맥 정보)
            next_sentence (str, optional): 다음 문장 (문맥 정보)
            title (str, optional): 글 제목 (제목-본문 충돌 체크용)
        """
        keyword_score, keyword_level, keyword_reasons = self._calculate_risk_score(sentence)
        llm_score = self._call_llm_for_risk_analysis(sentence, prev_sentence, next_sentence)
        
        # ⭐ RAG: 유사 사례 검색
        similar_cases = self._search_similar_confirmed_cases(sentence)

        print(f"[DEBUG] score_sentence - keyword_score: {keyword_score:.3f}, llm_score: {llm_score:.3f}")

        # LLM 점수가 있으면 LLM만 사용 (더 정확함)
        # LLM이 없으면 키워드 점수 사용
        if llm_score > 0:
            final_score = llm_score
        else:
            final_score = keyword_score  # 0 또는 음수 포함

        final_score = max(0.0, min(1.0, final_score))
        final_level = self._score_to_level(final_score)
        
        # ⭐ 신뢰도 계산
        confidence, confidence_level = self._calculate_confidence(
            llm_score, similar_cases, keyword_score, final_score
        )
        
        # ⭐ 제목-본문 충돌 체크
        title_conflict = False
        title_conflict_reason = ""
        if title and final_score >= THRESHOLD:  # 고위험일 때만 체크
            title_conflict, title_conflict_reason = self._check_title_content_conflict(
                title, sentence, final_score
            )
        
        print(f"[DEBUG] score_sentence - final_score: {final_score:.3f}, confidence: {confidence_level}, is_high_risk: {final_score >= THRESHOLD}")

        reasons = list(dict.fromkeys(keyword_reasons))  # 중복 제거 유지 순서
        if llm_score > 0:
            reasons.append(f"LLM_평가:{llm_score:.2f}")

        if not reasons:
            reasons.append("명확한 위험 신호 없음")

        return {
            "risk_score": final_score,
            "risk_level": final_level,
            "reasons": reasons,
            "keyword_score": keyword_score,
            "llm_score": llm_score,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "title_conflict": title_conflict,
            "title_conflict_reason": title_conflict_reason,
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

        for profile in self.keyword_profiles:
            matches = [kw for kw in profile["keywords"] if kw in sentence_lower]
            if not matches:
                continue

            delta = profile["weight"] * len(matches)
            base_score += delta

            label = profile["level"]
            if profile["weight"] > 0:
                risk_factors.extend([f"{label}_키워드:{kw}" for kw in matches])
            else:
                risk_factors.extend([f"완충_키워드:{kw}" for kw in matches])
        
        # 문장 길이 고려 (너무 짧거나 긴 문장은 점수 조정)
        sentence_length = len(sentence.strip())
        if sentence_length < 10:
            base_score *= 0.5  # 짧은 문장은 점수 감소
        elif sentence_length > 120:
            base_score *= 1.1  # 지나치게 긴 문장은 약간 증가
            
        final_score = max(0.0, min(1.0, base_score))
        
        # 위험 레벨 결정 (THRESHOLD 기준 적용)
        if final_score >= THRESHOLD:
            risk_level = 'high'
        elif final_score >= 0.4:
            risk_level = 'medium'
        else:
            risk_level = 'low'
            
        return final_score, risk_level, risk_factors

    @staticmethod
    def _score_to_level(score: float) -> str:
        if score >= THRESHOLD:
            return 'high'
        if score >= 0.4:
            return 'medium'
        return 'low'
    
    def _store_high_risk_sentences(self, high_risk_sentences: List[Dict[str, Any]]) -> None:
        """
        고위험 문장들을 벡터 DB에 저장
        
        Args:
            high_risk_sentences (List[Dict]): 고위험 문장 리스트
        """
        try:
            # 벡터 스토어 import (지연 import로 순환 참조 방지)
            from .vector_store import get_vector_store
            
            vector_store = get_vector_store()
            
            for sentence_data in high_risk_sentences:
                sentence = sentence_data.get('sentence', '')
                
                # 임베딩 생성
                embedding = self._get_embedding(sentence)
                
                # 메타데이터 준비
                metadata_dict = {
                    "user_id": sentence_data.get('user_id', 'unknown'),
                    "post_id": sentence_data.get('post_id', 'unknown'),
                    "sentence": sentence,
                    "risk_score": sentence_data.get('risk_score', 0.0),
                    "created_at": sentence_data.get('created_at', datetime.now().isoformat()),
                    "sentence_index": sentence_data.get('sentence_index', 0),
                    "risk_level": sentence_data.get('risk_level', 'unknown'),
                    "risk_factors": sentence_data.get('risk_factors', []),
                    "analyzed_at": sentence_data.get('analyzed_at', datetime.now().isoformat()),
                    "confirmed": False  # 자동 저장된 문장은 미확인 상태
                }
                
                # 벡터 DB에 저장
                vector_store.upsert_high_risk_chunk(embedding, metadata_dict)
                
            print(f"[INFO] {len(high_risk_sentences)}개의 고위험 문장을 ChromaDB에 저장 완료")
                
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
    
    def _search_similar_confirmed_cases(self, sentence: str, top_k: int = 3, min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        벡터DB에서 유사한 확정된 사례를 검색 (RAG)
        
        Args:
            sentence: 검색할 문장
            top_k: 최대 반환 개수
            min_score: 최소 유사도 (0.0~1.0)
            
        Returns:
            유사 사례 리스트 [{sentence, confirmed, similarity, risk_score}, ...]
        """
        try:
            from .embedding_service import get_embedding
            from .vector_db import get_client, search_similar
            
            # 1. 임베딩 생성
            embedding = get_embedding(sentence)
            
            # 2. 벡터DB에서 유사 문장 검색
            client = get_client()
            if not client:
                print("[WARN] ChromaDB 클라이언트를 사용할 수 없습니다. RAG 건너뜀.")
                return []
            
            results = search_similar(
                client=client,
                embedding=embedding,
                top_k=top_k,
                min_score=min_score,
                collection_name="confirmed_risk"
            )
            
            # 3. 결과 포맷팅
            similar_cases = []
            for result in results:
                metadata = result.get('metadata', {})
                similar_cases.append({
                    'sentence': result.get('document', ''),
                    'confirmed': metadata.get('confirmed', False),
                    'similarity': result.get('score', 0.0),
                    'risk_score': metadata.get('risk_score', 0.0),
                    'user_id': metadata.get('user_id', ''),
                    'created_at': metadata.get('created_at', '')
                })
            
            if similar_cases:
                print(f"[DEBUG] RAG: '{sentence[:30]}...'와 유사한 사례 {len(similar_cases)}건 발견", flush=True)
            
            return similar_cases
            
        except Exception as e:
            print(f"[ERROR] 벡터DB 검색 실패: {e}", flush=True)
            return []
    
    def _calculate_confidence(
        self, 
        llm_score: float, 
        similar_cases: List[Dict[str, Any]], 
        keyword_score: float,
        final_score: float
    ) -> tuple[float, str]:
        """
        판단 신뢰도 계산
        
        Args:
            llm_score: LLM 점수
            similar_cases: 유사 사례 리스트
            keyword_score: 키워드 점수
            final_score: 최종 위험 점수
            
        Returns:
            tuple: (신뢰도 점수 0.0~1.0, 신뢰도 레벨 'high'/'medium'/'low')
        """
        confidence = 0.0
        
        # 1. LLM 점수 존재 여부 (+0.3)
        if llm_score > 0:
            confidence += 0.3
        
        # 2. 유사 사례 개수 및 유사도 (최대 +0.4)
        if similar_cases:
            num_cases = len(similar_cases)
            avg_similarity = sum(case.get('similarity', 0) for case in similar_cases) / num_cases
            
            # 유사 사례 개수 기여도
            if num_cases >= 3:
                confidence += 0.2
            elif num_cases >= 1:
                confidence += 0.1
            
            # 평균 유사도 기여도
            if avg_similarity >= 0.8:
                confidence += 0.2
            elif avg_similarity >= 0.7:
                confidence += 0.1
        
        # 3. 키워드-LLM 점수 일치도 (+0.3)
        if llm_score > 0 and keyword_score > 0:
            score_diff = abs(llm_score - keyword_score)
            if score_diff < 0.1:
                confidence += 0.3  # 거의 일치
            elif score_diff < 0.3:
                confidence += 0.2  # 어느 정도 일치
            else:
                confidence += 0.1  # 불일치
        elif llm_score > 0:
            confidence += 0.15  # LLM만 있음
        
        confidence = max(0.0, min(1.0, confidence))
        
        # 레벨 분류
        if confidence >= 0.75:
            level = "high"
        elif confidence >= 0.5:
            level = "medium"
        else:
            level = "low"
        
        return confidence, level
    
    def _check_title_content_conflict(
        self, 
        title: str, 
        content: str, 
        risk_score: float
    ) -> tuple[bool, str]:
        """
        제목과 본문의 대상이 다른지 체크 (간단한 휴리스틱)
        
        Args:
            title: 글 제목
            content: 분석 대상 문장
            risk_score: 위험 점수
            
        Returns:
            tuple: (충돌 여부, 충돌 이유)
        """
        if not title or not content:
            return False, ""
        
        title_lower = title.lower()
        content_lower = content.lower()
        
        # 외부 대상을 언급하는 키워드 (다른 곳/사이트/앱/서비스 등)
        external_keywords = [
            "다른", "다은", "딴", "타", "외부", "다른곳", "다른사이트", "다른앱", 
            "다른서비스", "다른플랫폼", "경쟁", "라이벌"
        ]
        
        # 제목에 외부 대상 언급이 있는지
        title_has_external = any(kw in title_lower for kw in external_keywords)
        
        # 본문에 이탈 의도 키워드가 있는지
        churn_keywords = [
            "탈퇴", "그만", "떠나", "이탈", "나가", "떠날", "안쓸", "안 쓸",
            "관둘", "그만둘", "안할", "안 할", "그만할", "포기"
        ]
        content_has_churn = any(kw in content_lower for kw in churn_keywords)
        
        # 충돌 판정: 제목은 외부 대상 비판, 본문은 이탈 의도
        if title_has_external and content_has_churn:
            return True, "제목은 외부 대상 언급, 본문은 서비스 이탈 의도 표현 (검토 권장)"
        
        return False, ""
    
    def _call_llm_for_risk_analysis(self, sentence: str, prev_sentence: str = "", next_sentence: str = "") -> float:
        """
        LLM을 호출하여 문장의 이탈 위험도를 분석 (캐싱 및 문맥 정보 지원)
        
        이 부분은 실제 LLM 호출이며, 운영 시 비용이 든다.
        OpenAI GPT API를 사용하여 문장의 이탈 위험도를 0.0~1.0 사이의 점수로 계산한다.
        
        Args:
            sentence (str): 분석할 문장
            prev_sentence (str, optional): 이전 문장 (문맥 정보)
            next_sentence (str, optional): 다음 문장 (문맥 정보)
            
        Returns:
            float: 0.0~1.0 사이의 위험 점수 (실패 시 기본값 0.0)
        """
        if not sentence or not sentence.strip():
            return 0.0
        
        # ⭐ 벡터DB에서 유사 사례 검색 (RAG)
        similar_cases = self._search_similar_confirmed_cases(sentence)
        
        # ⭐ 캐시 키 생성 (문장 + 문맥 + 유사 사례 수로 고유한 키 생성)
        cache_key = f"{sentence}|{prev_sentence}|{next_sentence}|{len(similar_cases)}"
        
        # ⭐ 캐시 확인 (같은 문장+문맥은 같은 결과 반환)
        if cache_key in self._analysis_cache:
            cached_score = self._analysis_cache[cache_key]
            print(f"[DEBUG] 캐시된 결과 사용 - '{sentence[:30]}...' -> {cached_score:.3f}", flush=True)
            return cached_score
            
        # OpenAI API가 사용 가능한지 확인
        if not openai or not OPENAI_API_KEY:
            print("[WARN] OpenAI API를 사용할 수 없습니다. 기본값 0.0을 반환합니다.")
            return 0.0
            
        try:
            # ⭐ 문맥 정보 구성 (게시글 제목 + 이전/다음 문장)
            context_info = ""
            has_context = prev_sentence or next_sentence
            
            if has_context:
                context_info = "\n\n📌 문맥 정보 (더 정확한 분석을 위해 고려):\n"
                if prev_sentence:
                    context_info += f"  • 이전 문장: \"{prev_sentence}\"\n"
                context_info += f"  • 현재 문장: \"{sentence}\" ← 이 문장을 평가하세요\n"
                if next_sentence:
                    context_info += f"  • 다음 문장: \"{next_sentence}\"\n"
                context_info += "\n⚠️ 현재 문장이 불완전해 보이면 문맥을 함께 고려하세요.\n"
            
            # ⭐ RAG: 과거 유사 사례 추가 (벡터DB 검색 결과)
            if similar_cases:
                context_info += "\n\n🔍 과거 유사 사례 (관리자가 확정한 판정):\n"
                for i, case in enumerate(similar_cases[:3], 1):  # 최대 3개만
                    confirmed_label = "✅ 위험 맞음" if case.get('confirmed') else "❌ 위험 아님"
                    similarity = case.get('similarity', 0) * 100
                    context_info += f"  {i}. \"{case['sentence'][:60]}...\"\n"
                    context_info += f"     → 최종 판정: {confirmed_label} (유사도: {similarity:.0f}%)\n"
                context_info += "\n⚠️ 위 사례들을 참고하여 일관되게 판단하세요.\n"
                print(f"[DEBUG] RAG: {len(similar_cases)}개 유사 사례를 프롬프트에 추가", flush=True)
            
            # 개선된 이탈 위험도 분석 프롬프트 (대상 명시 강화)
            prompt = f"""이 문장의 커뮤니티/서비스 이탈 위험도를 0.00~1.00 사이의 숫자로 평가하세요.
{context_info}
문장: "{sentence}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 평가 전 필수 확인사항:

⚠️ 1단계: **브랜드/제품명 확인** (최우선!)
   
   ❌ 다음 키워드가 있으면 음식점/제품 리뷰입니다 (점수 0.10~0.20):
      - 음식점: "피자", "치킨", "버거", "카페", "레스토랑", "음식점"
      - 브랜드: "도미노", "맥도날드", "스타벅스", "이재모" 등
      - 제품: "아이폰", "갤럭시", "맥북", "에어팟" 등
      - 장소: "영화관", "헬스장", "PC방", "노래방" 등
      
   ✅ 브랜드명 없이 서비스 명시:
      - "여기", "이 서비스", "이 커뮤니티", "이 사이트"
      - "탈퇴", "계정 삭제", "이 플랫폼"

⚠️ 2단계: **제목 확인**
   
   - 제목에 위 브랜드/제품명이 있으면 → 리뷰 글 (점수 0.10~0.20)
   - 제목에 "탈퇴", "그만둘까" 등이 있으면 → 이탈 글

⚠️ 3단계: **대상 명시 확인**
   
   ❌ 대상 불명확한 경우 (점수 0.00~0.30):
      - "다른 플랫폼 알아보는 중" → 공부/학습 플랫폼일 수도
      - "그만둘 때가 됐다" → 직장/학교일 수도
      - "나은 곳이 많더라" → 장소일 수도
      - 대상이 전혀 명시되지 않은 일반적 불만

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 평가 단계별 가이드:

1️⃣ 대상 명시 확인 (최우선!)
   ✅ 명시됨: 위에 열거한 키워드들
   ❌ 불명확: 대상 없는 일반적 감정 표현 → 위험도 최대 0.30

2️⃣ 이탈 단계 판단:
   [1단계] 활발 참여 (0.00-0.15): 긍정, 만족, 적극 참여
   [2단계] 소극 참여 (0.15-0.35): 무관심, 가끔 방문
   [3단계] 관계 단절 (0.35-0.60): 소통 안돼, 사람들 별로, 실망
   [4단계] 대안 탐색 (0.60-0.80): 다른 곳 알아봄, 갈아탈까 고민
   [5단계] 이탈 결정 (0.80-1.00): 탈퇴, 그만둠, 포기, 떠남

3️⃣ 핵심 키워드:
   🔴 HIGH (0.75+): 탈퇴, 떠남, 그만둠, 포기, 소용없, 의미없, 갈아타
   🟠 MEDIUM (0.50+): 다른 곳, 힘들어, 지쳐, 답답, 불만
   🟡 LOW (0.30+): 아쉬워, 불편해, 개선 필요

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 평가 예시 (브랜드/제품명 확인 최우선!):

❌ LOW - 브랜드명 감지 (음식점 리뷰):
[제목: "피자 맛집"] "도미노 피자가 더 나은듯??"
→ 브랜드명: "도미노", "피자" 감지
→ 음식점 리뷰 판정 → 점수: 0.15

❌ LOW - 브랜드명 감지 (음식점 리뷰):
[제목: "피자 맛집"] "이재모 피자 맛없음 ㅋㅋ"
→ 브랜드명: "이재모", "피자" 감지
→ 음식점 리뷰 판정 → 점수: 0.15

❌ LOW - 브랜드명 감지 + 불명확한 표현:
[제목: "피자 맛집"] "이제 바이바이임"
→ 제목에 "피자" 감지
→ "바이바이"만으로는 서비스 이탈 불명확
→ 음식점 맥락 → 점수: 0.20

✅ HIGH - 대상 명확 + 이탈 의도 명확:
[제목: "탈퇴 고민"] "여기 있어봐자 소용없을듯요"
→ 브랜드명: 없음
→ 대상: "여기" = 현재 서비스
→ 이탈 의도: 명확 → 점수: 0.85

✅ HIGH - 제목으로 대상 확인:
[제목: "더 이상은 못하겠습니다"] "이제 정말 그만둘 때가 된 것 같습니다"
→ 브랜드명: 없음
→ 제목에서 서비스 이탈 명시
→ 점수: 0.85

❌ LOW - 대상 불명확 (직장/학교일 수도):
"이제 정말 그만둘 때가 된 것 같습니다"
→ 브랜드명: 없음
→ 제목 없음, 대상 불명확
→ 점수: 0.30

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 중요 원칙 (반드시 준수):

1️⃣ **과거 유사 사례 최우선 참고!** ⭐ 가장 중요!
   - 위에 과거 사례가 있으면 그 판정을 따르세요
   - 유사도 70% 이상이면 거의 동일한 케이스입니다
   - 일관성 유지가 핵심입니다

2️⃣ **브랜드/제품명 확인**
   - 피자, 치킨, 버거, 카페 등 → 음식점 리뷰 (0.10~0.20)
   - 도미노, 맥도날드, 이재모 등 → 브랜드 리뷰 (0.10~0.20)
   - 아이폰, 갤럭시, 맥북 등 → 제품 리뷰 (0.10~0.20)
   - 영화관, 헬스장, PC방 등 → 장소 리뷰 (0.10~0.20)

3️⃣ **제목 확인**
   - 제목에 브랜드/제품명 있으면 → 리뷰 글 (0.10~0.20)
   - 제목에 "탈퇴", "그만둘까", "더 이상" 등 → 이탈 글

4️⃣ **대상 명시 필수**
   - 브랜드명 없어도 대상 불명확하면 → 최대 0.30
   - "여기", "이 서비스", "이 커뮤니티", "탈퇴" 등 필수

5️⃣ **보수적 평가**
   - 불명확하면 낮게 점수 부여
   - 의심스러우면 0.20 이하로

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 출력 형식 (반드시 준수):
- 반드시 0.00~1.00 사이의 숫자만 출력하세요
- 설명, 이유, 텍스트는 절대 포함하지 마세요
- 올바른 예: 0.75
- 잘못된 예: "이 문장은 이탈 의도가 있습니다", "0.75점", "점수: 0.75"

숫자만 답해 (예: 0.75):"""

            # 개선된 System 프롬프트
            system_prompt = """당신은 커뮤니티/서비스 이탈 징후를 정밀하게 분석하는 전문가입니다.

🚨 중요: 반드시 0.00~1.00 사이의 숫자만 출력하세요. 설명이나 텍스트는 절대 포함하지 마세요!

핵심 원칙:
1. 대상(서비스/커뮤니티) 명시 여부를 최우선 확인
2. 단순 불만과 이탈 의도를 명확히 구분
3. 문맥과 어조를 종합 고려
4. 0.75 이상은 명확한 이탈 의도만 부여
5. 반드시 숫자만 답변 (예: 0.75)

과대평가 방지:
- 대상 불명확 시 보수적 평가
- 운영 불만 ≠ 이탈 위험
- 일반적 감정 표현에 낮은 점수 부여

출력 예시: 0.75 (숫자만!)"""

            # OpenAI API 호출
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,  # ⭐ 10→20으로 증가 (숫자 응답에 충분)
                temperature=0,  # ⭐ 0으로 설정 (일관된 결과)
                seed=42  # ⭐ 고정된 seed로 재현 가능성 확보
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
                
                # ⭐ 캐시에 저장 (다음번에 같은 문장은 API 호출 없이 반환)
                self._analysis_cache[cache_key] = score
                
                print(f"[DEBUG] LLM 분석 결과 - 문장: '{sentence[:30]}...' -> 점수: {score:.3f}", flush=True)
                return score
            else:
                # ⚠️ LLM 파싱 실패 시 키워드 점수를 fallback으로 사용
                print(f"[WARN] LLM 응답에서 점수를 추출할 수 없습니다: {response_text[:100]}...", flush=True)
                keyword_score, _, keyword_reasons = self._calculate_risk_score(sentence)
                
                # 키워드 점수를 기반으로 fallback 점수 생성
                # 키워드 점수가 있으면 사용하고, 없으면 중간값(0.5) 사용
                fallback_score = max(0.5, keyword_score) if keyword_score > 0 else 0.5
                fallback_score = max(0.0, min(1.0, fallback_score))
                
                print(f"[WARN] Fallback: 키워드 점수 {keyword_score:.3f} -> 사용 점수 {fallback_score:.3f}", flush=True)
                print(f"[WARN] 키워드 요인: {keyword_reasons[:3]}", flush=True)  # 상위 3개만
                
                # 캐시에 fallback 점수 저장
                self._analysis_cache[cache_key] = fallback_score
                
                return fallback_score
                
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