"""
하이브리드 비윤리 판단 시스템
기존 BERT 모델 + OpenAI LLM 결합
"""
import os
import json
import re
import threading
from typing import Dict, List, Optional
from collections import Counter
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from ethics.ethics_predict import EthicsPredictor
from ethics.ethics_vector_db import get_client, search_similar_cases, upsert_confirmed_case, build_chunk_id
from ethics.ethics_embedding import get_embedding, get_embeddings_batch
from ethics.ethics_text_splitter import split_to_sentences

# .env 파일 로드
load_dotenv()


class HybridEthicsAnalyzer:
    """하이브리드 비윤리 분석기 (BERT 모델 + LLM + 규칙 기반)"""
    
    # 욕설 키워드 정의
    PROFANITY_KEYWORDS = {
        'severe': [  # 심한 욕설 (각 +25점)
            # 기본 욕설
            '씨발', '시발', 'ㅅㅂ', 'ㅆㅂ', '병신', 'ㅂㅅ', '개새끼', '개쉐', '개색',
            '좆', '좃', 'ㅈ같', '지랄', 'ㅈㄹ', '엿먹', '꺼져', '죽어', '죽을래',
            '미친놈', '미친년', '또라이', '싸가지', '쓰레기같은', '찌질', '개돼지',
            '븅신', '병쉰', '시바', '씹', '개같은', '개소리', '새끼',
            # 추가 욕설
            '씹새끼', '씹년', '씹놈', '개년', '개놈', '개자식', '개새', '개쓰레기',
            '미친새끼', '미친자식', '미친것', '미친X', '돌았', '돌아버',
            '좆까', '좃까', '닥쳐', '닥치세요', '꺼지세요', '죽어버려', '뒤져', '뒤질',
            '엿이나', '엿드셔', '개빡', '빡친', '빡쳐', '좆밥', '잡놈', '잡년',
            '망할', '망할놈', '개망', '지랄하네', '지랄맞', '짜져', '짜증남',
            '씨팔', 'sibal', 'sival', 'fuck', 'shit', 'bitch', 'asshole',
            '애미', '애비', '느금', '느개비', '개드립', '개웃', '게새',
            '호로', '호로자식', '호로새끼', '창놈', '창녀', '썅', '썅년',
            '병맛', '병크', '꼴값', '꼴좋', '개독', '급식충', '틀딱', '한남충',
            '김치녀', '맘충', '틀니딱딱', '급식', '급삽', '등신', '멍텅구리',
            '명청', 'ㅁㅊ', '개차반', '개판', '개지랄', '염병', '씨부랄', '씨부럴',
            '좆같네', '좆밥', '개쪽', '개소리', '개드립', '개소', 'ㄱㅅㄲ', '개막장', 
            '좌빨'
        ],
        'moderate': [  # 중간 수위 욕설/비방 (각 +15점)
            # 기본 비방
            '바보', '멍청', '멍청이', '한심', '한심한', '못났', '못난',
            '짜증', '짜증나', '꼴불견', '꼴사납', '지겨', '지긋지긋',
            '역겹', '역겨운', '징그럽', '추악한', '더럽', '후진',
            '쓰레기', '쪽팔', '쪽팔려', '창피', '부끄럽', '철면피', '뻔뻔',
            '어이없', '황당', '맥빠', '한심하다', '저질', '저급', '수준낮',
            '닥쳐', '입닥', '입 닥쳐', '조용히 해',
            # 추가 비방
            '무식', '무식한', '모자라', '모자란', '멍청한', '답없', '답이없',
            '꼴보기싫', '보기싫', '거슬려', '거슬리', '미개', '미개한',
            '수준', '수준이하', '수준미달', '최악', '최악의', '형편없',
            '한심스럽', '부족', '부족한', '모자람', '문제있', '문제많',
            '정신없', '정신차려', '생각없', '생각이없', '뇌없', '뇌가없',
            '무능', '무능한', '무능력', '쓸모없', '쓸데없', '가치없',
            '쪽팔린', '망신', '망신당', '체면', '염치없', '염치',
            '비열', '비열한', '치사', '치사한', '찌질', '찌질이', '루저',
            '패배자', '낙오자', '찐따', '왕따', '아싸', '인싸못', '허접',
            '허접한', '구제불', '구제불능', '희망없', '가망없', '안습',
            '안타까', '불쌍', '측은', '가엾', '불행', '비참',
            '우스워', '우스운', '웃기', '웃긴', '코미디', '개그', '개그맨',
            '애새끼', '애송이', '애기', '꼬마', '중딩', '초딩', '유치',
            '유치한', '유치해', '어리석', '어리석은', '우매', '우매한',
            '천박', '천박한', '저속', '저속한', '저급스럽', '조잡', '조잡한',
            '형편없는', '볼품없', '시시한', '따분한', '지루한', '재미없',
            '맹하', '둔하', '둔감', '느리', '굼뜨', '굼뜬', '답답',
            '무안', '무안한', '무례', '무례한', '버릇없', '싸가지없', '예의없',
            '뒤진다', '뒤질래', "뒤지고"
        ],
        'patterns': [  # 욕설 패턴
            r'[ㄱ-ㅎ]+[ㅅㅆ][ㅂㅃ][ㄱ-ㅎ]*',
            r'[ㄱ-ㅎ]*[ㅂㅃ][ㅅㅆ][ㄱ-ㅎ]*',
            r'[ㄱ-ㅎ]+[ㅈㅉ][ㄹㄴ][ㄱ-ㅎ]*',
            r'[시씨][1l|!iI\*@#발팔빨]',
            r'개\s*[새쉐색섹]+',
            r'[좆좃][같갔]',
            r'[느늬니]금\s*마',
            r'[ㅄ]{2,}',
            r'[ㅅㅆ]{2,}[ㅂㅃ]',
            r'[병븅빙][신쉰]',
            r'[개][\*\-_\s]*[새쉐]',
            r'[씨시][8\*@#발빨팔]',
            r'[죽쥭][어어]',
            r'[지ㅈ][랄ㄹ]',
            r'미[친ㅊ][놈년]',
            r'[엿엇][먹먹]',
            r'[꺼꺼][져지]',
            r'[닥닥][쳐쳐]',
            r'[개][같갇]',
            r'씹[\s]*[새년놈]',
        ]
    }
    
    # 스팸 키워드 정의
    SPAM_KEYWORDS = {
        'high': ['대출', '당첨', '무료', '공짜', '현금', '적립', '클릭', '접속', 
                 '선착순', '한정', '이벤트', '특가', '세일', '할인', '쿠폰',
                 '부업', '재택', '투자', '수익', '도박', '카지노', '성인',
                 '환급', '지급', '즉시', '긴급', '마감', '축하', '당첨',
                 '체험', '보조제', '비법', '자동', '결제', '취소', '국세청',
                 '정부지원', '저신용', '계좌', '입력', '링크', '확인', '방문'],
        'medium': ['광고', '홍보', '판매', '구매', '가입', '회원', '등록',
                  '참여', '신청', '문의', '안내', '제공', '공개', '강의',
                  '택배', '배송', '지연'],
        'patterns': [
            r'http[s]?://[^\s]+',
            r'bit\.ly/[^\s]+',
            r'\w+\.(kr|com|net|co\.kr|info)/\w+',
            r'\d{3}-\d{3,4}-\d{4}',
            r'\d{2,3}-\d{3,4}-\d{4}',
            r'080-\d{3,4}-\d{4}',
            r'카톡.*[Ii][Dd]',
            r'[A-Z]{3,}',
            r'\[광고\]',
            r'\[Web발신\]',
            r'▶|👉|⏩|➡',
            r'★|☆|🔥|💰|🎉|🎊',
            r'\d{1,3}%\s*할인',
            r'\d{1,3}만원',
        ]
    }
    
    def __init__(self, 
                 model_path='ethics/models/binary_classifier.pth',
                 config_path='ethics/models/config.json',
                 api_key: Optional[str] = None,
                 model_name: Optional[str] = None):
        """
        Args:
            model_path: BERT 모델 경로
            config_path: 설정 파일 경로
            api_key: OpenAI API 키 (None이면 환경변수에서 로드)
            model_name: OpenAI 모델 이름 (None이면 환경변수에서 로드)
        """
        # BERT 모델 초기화
        print("[INFO] BERT 모델 로딩 중...")
        self.bert_predictor = EthicsPredictor(model_path, config_path)
        
        # OpenAI 클라이언트 초기화
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model_name = model_name or 'gpt-4.1-nano'
        
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        self.client = OpenAI(api_key=self.api_key)
        print(f"[INFO] LLM 모델 연결 완료: {self.model_name}")
        
        # RAG 기능 초기화 (선택적, 실패해도 계속 진행)
        try:
            self.vector_client = get_client()
            print("[INFO] RAG 벡터DB 연결 완료")
            self.rag_enabled = True
        except Exception as e:
            print(f"[WARN] RAG 벡터DB 연결 실패: {e}. RAG 기능이 비활성화됩니다.")
            self.rag_enabled = False
            self.vector_client = None
    
    def _calculate_profanity_boost(self, text: str) -> Dict:
        """욕설 감지 및 점수 부스트 계산"""
        boost_score = 0.0
        profanity_count = 0
        detected_profanities = []
        
        # 1. 심한 욕설 체크 (각 +25점)
        for keyword in self.PROFANITY_KEYWORDS['severe']:
            if keyword in text:
                boost_score += 25
                profanity_count += 1
                detected_profanities.append(keyword)
        
        # 2. 중간 수위 욕설/비방 체크 (각 +15점)
        for keyword in self.PROFANITY_KEYWORDS['moderate']:
            if keyword in text:
                boost_score += 15
                profanity_count += 1
                detected_profanities.append(keyword)
        
        # 3. 욕설 패턴 매칭
        for pattern in self.PROFANITY_KEYWORDS['patterns']:
            matches = re.findall(pattern, text)
            if matches:
                pattern_count = min(len(matches), 3)
                boost_score += pattern_count * 20
                profanity_count += pattern_count
        
        # 4. 욕설 반복 감지
        if profanity_count > 3:
            boost_score += 10
        
        # 최대 부스트는 50점으로 제한
        boost_score = min(boost_score, 50.0)
        
        # 심각도 판단
        if boost_score >= 40:
            severity = 'severe'
        elif boost_score >= 20:
            severity = 'moderate'
        elif boost_score > 0:
            severity = 'mild'
        else:
            severity = 'none'
        
        return {
            'boost_score': boost_score,
            'profanity_detected': profanity_count > 0,
            'profanity_count': profanity_count,
            'severity': severity
        }
    
    def _calculate_rule_based_spam_score(self, text: str) -> float:
        """규칙 기반 스팸 점수 계산"""
        score = 0.0
        text_lower = text.lower()
        
        # 1. 고위험 키워드 체크 (각 +20점)
        for keyword in self.SPAM_KEYWORDS['high']:
            if keyword in text_lower:
                score += 20
        
        # 2. 중위험 키워드 체크 (각 +5점)
        for keyword in self.SPAM_KEYWORDS['medium']:
            if keyword in text_lower:
                score += 5
        
        # 3. 패턴 매칭 체크
        pattern_match_count = 0
        for pattern in self.SPAM_KEYWORDS['patterns']:
            if re.search(pattern, text):
                pattern_match_count += 1
        
        if pattern_match_count >= 3:
            score += 40
        elif pattern_match_count >= 2:
            score += 30
        elif pattern_match_count >= 1:
            score += 20
        
        # 4. 특수문자/이모티콘 비율 체크
        special_chars = len(re.findall(r'[!@#$%^&*()_+=\[\]{}|\\:;"\'<>,.?/~`🎉🎊🔥💰💯]', text))
        if len(text) > 0:
            special_ratio = special_chars / len(text)
            if special_ratio > 0.15:
                score += 15
        
        # 5. 대문자 비율 체크
        uppercase_count = sum(1 for c in text if c.isupper() and c.isalpha())
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count > 0:
            uppercase_ratio = uppercase_count / alpha_count
            if uppercase_ratio > 0.5:
                score += 10
        
        # 6. 문장/구문 반복 감지 (100자 이상)
        if len(text) >= 100:
            max_repeat = 0
            
            # 방법 1: 줄바꿈으로 분할하여 체크
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 3:
                normalized_lines = [line.lower().replace(' ', '') for line in lines if len(line) > 5]
                if normalized_lines:
                    line_counts = Counter(normalized_lines)
                    max_repeat = max(line_counts.values())
            
            # 방법 2: 단어/구문 단위 반복 체크 (공백이나 구두점으로 분할)
            words = re.split(r'[\s,.!?;]+', text.lower())
            words = [w.strip() for w in words if len(w.strip()) > 3]
            if len(words) >= 5:
                word_counts = Counter(words)
                word_repeat = max(word_counts.values()) if word_counts else 0
                max_repeat = max(max_repeat, word_repeat)
            
            # 방법 3: 연속된 동일 패턴 감지 (sliding window)
            # 5-15자 길이의 패턴을 찾아서 반복 체크
            for pattern_len in [5, 10, 15]:
                if len(text) >= pattern_len * 3:
                    patterns = []
                    for i in range(0, len(text) - pattern_len + 1, pattern_len):
                        pattern = text[i:i+pattern_len].lower().replace(' ', '').strip()
                        if len(pattern) >= pattern_len * 0.8:  # 최소 80% 길이
                            patterns.append(pattern)
                    
                    if patterns:
                        pattern_counts = Counter(patterns)
                        pattern_repeat = max(pattern_counts.values())
                        max_repeat = max(max_repeat, pattern_repeat)
            
            # 5회 이상 반복 체크
            if max_repeat >= 5:
                # 기본 +50점 + 추가 반복마다 +6점
                repeat_score = 50 + ((max_repeat - 5) * 6)
                
                # 15회 이상 극심한 반복 시 추가 보너스
                if max_repeat >= 15:
                    repeat_score += 20
                
                score += min(repeat_score, 100)  # 최대 100점
        
        # 7. 짧은 텍스트는 스팸 가능성 낮음
        if len(text) < 20 and score < 20:
            score *= 0.5
        
        return min(score, 100.0)
        
    def _analyze_with_llm(self, text: str) -> Dict:
        """LLM을 사용한 비윤리 및 스팸 분석"""
        prompt = f"""다음 텍스트의 비윤리성과 스팸 여부를 분석해주세요.

텍스트: "{text}"

아래 JSON 형식으로 정확히 답변해주세요:
{{
    "immoral_score": 0-100 사이의 숫자 (0=완전 윤리적, 100=매우 비윤리적),
    "spam_score": 0-100 사이의 숫자 (스팸 확실성: 100=명백히 스팸, 50=애매함, 0=명백히 정상),
    "confidence": 0-100 사이의 숫자 (판단의 확신도),
    "types": ["유형1", "유형2", ...]
}}

분석 유형 목록:
- "욕설 및 비방": 비속어, 욕설, 타인을 비난하는 표현
- "도배 및 광고": 상업적 광고, 스팸, 도배성 메시지
- "없음": 해당 유형이 없는 경우

JSON 형식으로만 답변하세요."""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "당신은 텍스트의 비윤리성과 스팸 여부를 정확하게 판단하는 전문가입니다. 항상 JSON 형식으로만 답변합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            # 값 검증 및 정규화
            result['immoral_score'] = max(0, min(100, float(result.get('immoral_score', 50))))
            result['spam_score'] = max(0, min(100, float(result.get('spam_score', 0))))
            result['confidence'] = max(0, min(100, float(result.get('confidence', 50))))
            result['types'] = result.get('types', ['없음'])
            
            return result
            
        except Exception as e:
            print(f"[WARN] LLM 분석 오류: {e}")
            return {
                'immoral_score': 50.0,
                'spam_score': 0.0,
                'confidence': 30.0,
                'types': ['분석 실패']
            }
    
    def _search_similar_cases(self, text: str) -> List[Dict]:
        """
        벡터DB에서 유사한 비윤리/스팸 케이스 검색
        ⚡ 배치 임베딩을 사용하여 여러 문장을 한 번에 처리 (속도 4-6배 향상)
        
        Args:
            text (str): 검색할 텍스트
            
        Returns:
            List[Dict]: 유사 케이스 리스트
        """
        if not self.rag_enabled or not self.vector_client:
            return []
        
        try:
            # 텍스트를 문장 단위로 청킹
            sentences = split_to_sentences(text, min_length=10)
            
            if not sentences:
                return []
            
            # ⚡ 배치 임베딩 생성 (한 번의 API 호출로 모든 문장 처리)
            embeddings = get_embeddings_batch(sentences)
            
            # 각 임베딩별로 유사 케이스 검색
            all_similar_cases = []
            seen_ids = set()  # 중복 제거용
            
            for embedding in embeddings:
                # 유사 케이스 검색 (신뢰도 80 이상만)
                similar_cases = search_similar_cases(
                    client=self.vector_client,
                    embedding=embedding,
                    top_k=3,  # 문장당 최대 3개
                    min_score=0.5,
                    min_confidence=80.0,
                    prefer_confirmed=True
                )
                
                # 중복 제거 및 추가
                for case in similar_cases:
                    case_id = case.get('id')
                    if case_id and case_id not in seen_ids:
                        seen_ids.add(case_id)
                        all_similar_cases.append(case)
            
            # 유사도 점수 기준으로 정렬
            all_similar_cases.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # 상위 5개만 반환
            return all_similar_cases[:5]
            
        except Exception as e:
            print(f"[WARN] 유사 케이스 검색 중 오류: {e}")
            return []
    
    def _adjust_scores_with_similarity(
        self,
        base_immoral_score: float,
        base_spam_score: float,
        similar_cases: List[Dict]
    ) -> Dict[str, float]:
        """
        유사 케이스들의 점수를 가중 평균하여 보정 점수 계산
        
        Args:
            base_immoral_score: 기존 비윤리 점수
            base_spam_score: 기존 스팸 점수
            similar_cases: 유사 케이스 리스트
        
        Returns:
            Dict: 보정 점수 및 메타데이터
        """
        if not similar_cases:
            return {
                'adjusted_immoral_score': base_immoral_score,
                'adjusted_spam_score': base_spam_score,
                'confidence_boost': 0.0,
                'similar_case_count': 0,
                'max_similarity': 0.0
            }
        
        # 관리자 확인된 케이스 우선 사용
        confirmed_cases = [c for c in similar_cases if c.get('confirmed', False)]
        confirmed_count = len(confirmed_cases)  # 실제 확정 케이스 수 저장
        
        if not confirmed_cases:
            # 확인된 케이스가 없으면 확인되지 않은 케이스 사용 (가중치 낮춤)
            confirmed_cases = similar_cases
        
        # 유사도 기반 가중 평균 계산
        total_weight_immoral = 0.0
        weighted_sum_immoral = 0.0
        
        total_weight_spam = 0.0
        weighted_sum_spam = 0.0
        
        for case in confirmed_cases:
            similarity = case.get('score', 0.0)
            metadata = case.get('metadata', {})
            
            # 유사도가 높을수록 높은 가중치 (제곱 사용)
            weight = similarity ** 2
            
            # 비윤리 점수 가중 합
            immoral_score = float(metadata.get('immoral_score', 0.0))
            weighted_sum_immoral += immoral_score * weight
            total_weight_immoral += weight
            
            # 스팸 점수 가중 합
            spam_score = float(metadata.get('spam_score', 0.0))
            weighted_sum_spam += spam_score * weight
            total_weight_spam += weight
        
        # 가중 평균 계산
        adjusted_immoral = (
            weighted_sum_immoral / total_weight_immoral 
            if total_weight_immoral > 0 else base_immoral_score
        )
        adjusted_spam = (
            weighted_sum_spam / total_weight_spam 
            if total_weight_spam > 0 else base_spam_score
        )
        
        # 신뢰도 증가량 계산 (확정된 케이스 기준)
        confirmed_max_similarity = max([c.get('score', 0.0) for c in confirmed_cases]) if confirmed_cases else 0.0
        case_count_factor = min(len(confirmed_cases) / 3.0, 1.0)  # 최대 3개 기준
        confidence_boost = confirmed_max_similarity * case_count_factor * 0.2  # 최대 20% 증가
        
        # 전체 유사 케이스에서 최대 유사도 계산 (화면 표시용)
        overall_max_similarity = max([c.get('score', 0.0) for c in similar_cases]) if similar_cases else 0.0
        
        return {
            'adjusted_immoral_score': adjusted_immoral,
            'adjusted_spam_score': adjusted_spam,
            'confidence_boost': confidence_boost,
            'similar_case_count': len(confirmed_cases),
            'confirmed_case_count': confirmed_count,  # 실제 확정 케이스 수
            'max_similarity': overall_max_similarity  # 전체 케이스 기준으로 변경
        }
    
    def _combine_scores(
        self,
        base_immoral_score: float,
        base_spam_score: float,
        adjusted_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        기존 점수와 보정 점수를 결합
        
        Args:
            base_immoral_score: 기존 비윤리 점수
            base_spam_score: 기존 스팸 점수
            adjusted_scores: 보정 점수 딕셔너리
        
        Returns:
            Dict: 최종 점수 및 메타데이터
        """
        similar_count = adjusted_scores.get('similar_case_count', 0)
        confirmed_count = adjusted_scores.get('confirmed_case_count', 0)
        max_similarity = adjusted_scores.get('max_similarity', 0.0)
        
        # 보정 점수 비중 결정
        if max_similarity >= 0.8:
            if confirmed_count >= 1:
                # 확정 케이스 1개 이상 & 유사도 80% 이상 → 최고 가중치
                adjustment_weight = 0.6
            elif similar_count >= 2:
                # 일반 케이스 2개 이상 & 유사도 80% 이상 → 높은 가중치
                adjustment_weight = 0.5
            elif similar_count >= 1:
                # 일반 케이스 1개 이상 & 유사도 80% 이상 → 중간 가중치
                adjustment_weight = 0.3
            else:
                adjustment_weight = 0.1
        elif max_similarity >= 0.7:
            if confirmed_count >= 1:
                # 확정 케이스 1개 이상 & 유사도 70~80% → 중간 가중치
                adjustment_weight = 0.4
            elif similar_count >= 1:
                # 일반 케이스 1개 이상 & 유사도 70~80% → 낮은 가중치
                adjustment_weight = 0.2
            else:
                adjustment_weight = 0.1
        else:
            # 그 외 → 최소 가중치
            adjustment_weight = 0.1
        
        # 최종 점수 계산
        final_immoral = (
            base_immoral_score * (1 - adjustment_weight) +
            adjusted_scores['adjusted_immoral_score'] * adjustment_weight
        )
        
        final_spam = (
            base_spam_score * (1 - adjustment_weight) +
            adjusted_scores['adjusted_spam_score'] * adjustment_weight
        )
        
        return {
            'final_immoral_score': min(100.0, final_immoral),
            'final_spam_score': min(100.0, final_spam),
            'adjustment_applied': adjustment_weight > 0.1,
            'adjustment_weight': adjustment_weight
        }
    
    def _auto_save_high_confidence_case(
        self,
        text: str,
        immoral_score: float,
        spam_score: float,
        confidence: float,
        spam_confidence: float,
        post_id: str = "",
        user_id: str = ""
    ) -> None:
        """
        신뢰도 80 이상인 케이스를 벡터DB에 자동 저장 (동기 버전)
        
        Args:
            text: 저장할 텍스트
            immoral_score: 비윤리 점수
            spam_score: 스팸 점수
            confidence: 비윤리 신뢰도
            spam_confidence: 스팸 신뢰도
            post_id: 게시물 ID (선택)
            user_id: 사용자 ID (선택)
        """
        if not self.rag_enabled or not self.vector_client:
            return
        
        # 신뢰도 80 이상인 경우만 저장
        if confidence < 80.0 and spam_confidence < 80.0:
            return
        
        try:
            # 텍스트를 문장 단위로 청킹
            sentences = split_to_sentences(text, min_length=10)
            
            if not sentences:
                return
            
            # ⚡ 배치 임베딩 생성 (한 번의 API 호출)
            embeddings = get_embeddings_batch(sentences)
            
            # 각 문장별로 저장
            for sentence, embedding in zip(sentences, embeddings):
                # 메타데이터 준비
                metadata = {
                    "sentence": sentence,
                    "immoral_score": immoral_score,
                    "spam_score": spam_score,
                    "immoral_confidence": confidence,
                    "spam_confidence": spam_confidence,
                    "confidence": max(confidence, spam_confidence),  # 높은 신뢰도 사용
                    "confirmed": False,  # 관리자 확인 전
                    "post_id": post_id,
                    "user_id": user_id,
                    "created_at": datetime.now().isoformat(),
                    "feedback_type": "auto_saved"
                }
                
                # 벡터DB에 저장
                upsert_confirmed_case(
                    client=self.vector_client,
                    embedding=embedding,
                    metadata=metadata
                )
            
            print(f"[INFO] 고신뢰도 케이스 자동 저장 완료: {len(sentences)}개 문장")
            
        except Exception as e:
            print(f"[WARN] 자동 저장 중 오류: {e}")
    
    def _auto_save_high_confidence_case_async(
        self,
        text: str,
        immoral_score: float,
        spam_score: float,
        confidence: float,
        spam_confidence: float,
        post_id: str = "",
        user_id: str = ""
    ) -> None:
        """
        신뢰도 80 이상인 케이스를 벡터DB에 비동기로 자동 저장
        ⚡ 백그라운드 스레드에서 실행되어 사용자 응답 시간 단축 (1~5초 개선)
        
        Args:
            text: 저장할 텍스트
            immoral_score: 비윤리 점수
            spam_score: 스팸 점수
            confidence: 비윤리 신뢰도
            spam_confidence: 스팸 신뢰도
            post_id: 게시물 ID (선택)
            user_id: 사용자 ID (선택)
        """
        def save_task():
            """백그라운드에서 실행될 저장 작업"""
            self._auto_save_high_confidence_case(
                text=text,
                immoral_score=immoral_score,
                spam_score=spam_score,
                confidence=confidence,
                spam_confidence=spam_confidence,
                post_id=post_id,
                user_id=user_id
            )
        
        # 데몬 스레드로 실행 (메인 프로그램 종료 시 자동 종료)
        thread = threading.Thread(target=save_task, daemon=True)
        thread.start()
        print(f"[INFO] 벡터DB 저장 백그라운드 시작 (비동기)")
    
    def analyze(self, text: str) -> Dict:
        """하이브리드 분석 수행 (즉시 차단 시 LLM 미사용)"""
        # 1. BERT 모델 분석
        bert_result = self.bert_predictor.predict(text)
        bert_score = bert_result['probabilities']['비윤리적'] * 100
        bert_confidence = bert_result['confidence'] * 100
        
        result = {
            'text': text,
            'bert_score': bert_score,
            'bert_confidence': bert_confidence,
        }
        
        # 2. 규칙 기반 스팸 점수 계산 (LLM 없이도 가능)
        rule_spam_score = self._calculate_rule_based_spam_score(text)
        
        # 3. 욕설 감지 및 부스트 계산 (LLM 없이도 가능)
        profanity_info = self._calculate_profanity_boost(text)
        profanity_boost = profanity_info['boost_score']
        
        # 4. RAG 기반 즉시 차단 체크 (LLM 분석 전에 먼저 확인)
        similar_cases = []
        rag_case_summaries = []
        
        adjustment_applied = False
        similar_cases_count = 0
        max_similarity = 0.0
        adjustment_weight = 0.0
        auto_blocked = False
        auto_block_reason = None

        if self.rag_enabled:
            try:
                # 유사 케이스 검색
                similar_cases = self._search_similar_cases(text)
                
                if similar_cases:
                    # 즉시 차단 조건 체크: 유사도 95% 이상, 점수 90 이상인 관리자 확정 사례
                    for case in similar_cases:
                        metadata = case.get('metadata', {})
                        similarity = case.get('score', 0.0) * 100  # 0-1 범위를 0-100으로 변환
                        confidence = float(metadata.get('confidence', 0.0))
                        immoral_confidence = float(metadata.get('immoral_confidence', confidence))
                        spam_confidence_val = float(metadata.get('spam_confidence', confidence))
                        confirmed = bool(metadata.get('confirmed', False))
                        immoral_score = float(metadata.get('immoral_score', 0.0))
                        spam_score = float(metadata.get('spam_score', 0.0))
                        
                        # 관리자 확정 사례이고, 유사도 90% 이상, 점수 90 이상인 경우
                        if confirmed and similarity >= 90.0:
                            # 비윤리 확정 사례
                            if immoral_score >= 90 and immoral_confidence >= 80:
                                auto_blocked = True
                                auto_block_reason = 'immoral'
                                
                                # LLM 분석 없이 즉시 차단 결과 반환
                                print(f"[INFO] 즉시 차단 (LLM 미사용): 비윤리 확정 사례와 유사도 {similarity:.1f}%, 점수 {immoral_score:.1f}, 신뢰도 {immoral_confidence:.1f}")
                                
                                # 즉시 차단 케이스는 벡터DB에 저장하지 않음 (이미 유사한 확정 사례가 존재)
                                
                                result.update({
                                    'base_score': bert_score,
                                    'final_score': None,  # 즉시 차단: 비윤리 점수 null (BERT 단독 정확도 낮음)
                                    'final_confidence': None,  # 즉시 차단: 비윤리 신뢰도 null
                                    'spam_score': None,  # 즉시 차단: 스팸 점수 null
                                    'spam_confidence': None,  # 즉시 차단: 스팸 신뢰도 null
                                    'base_spam_score': None,  # 즉시 차단: 스팸 점수 null
                                    'rule_spam_score': rule_spam_score,
                                    'profanity_detected': profanity_info['profanity_detected'],
                                    'profanity_count': profanity_info['profanity_count'],
                                    'profanity_severity': profanity_info['severity'],
                                    'profanity_boost': profanity_boost,
                                    'types': metadata.get('types', ['욕설 및 비방']),  # 유사 사례의 타입 사용
                                    'weights': {
                                        'bert': 1.0,
                                        'llm': 0.0  # LLM 사용 안함
                                    },
                                    'rag_enabled': self.rag_enabled,
                                    'similar_cases_count': len(similar_cases),
                                    'max_similarity': similarity / 100.0,  # 0-1 범위로 변환
                                    'adjustment_applied': False,  # 즉시 차단은 RAG 보정 미적용
                                    'adjustment_weight': 0.0,
                                    'auto_blocked': True,
                                    'auto_block_reason': auto_block_reason,
                                    'adjusted_immoral_score': None,  # 즉시 차단은 보정 점수 없음
                                    'adjusted_spam_score': None,  # 즉시 차단은 보정 점수 없음
                                    'rag_similar_cases': [{
                                        'sentence': case.get('document', ''),
                                        'similarity': similarity,
                                        'immoral_score': immoral_score,
                                        'spam_score': spam_score,
                                        'confidence': confidence,
                                        'confirmed': True,
                                        'feedback_type': 'admin_confirmed',
                                        'created_at': metadata.get('created_at', '')
                                    }]
                                })
                                return result
                            
                            # 스팸 확정 사례
                            elif spam_score >= 90 and spam_confidence_val >= 80:
                                auto_blocked = True
                                auto_block_reason = 'spam'
                                
                                # LLM 분석 없이 즉시 차단 결과 반환
                                print(f"[INFO] 즉시 차단 (LLM 미사용): 스팸 확정 사례와 유사도 {similarity:.1f}%, 점수 {spam_score:.1f}, 신뢰도 {spam_confidence_val:.1f}")
                                
                                # 즉시 차단 케이스는 벡터DB에 저장하지 않음 (이미 유사한 확정 사례가 존재)
                                
                                result.update({
                                    'base_score': bert_score,
                                    'final_score': None,  # 즉시 차단: 비윤리 점수 null (BERT 단독 정확도 낮음)
                                    'final_confidence': None,  # 즉시 차단: 비윤리 신뢰도 null
                                    'spam_score': None,  # 즉시 차단: 스팸 점수 null
                                    'spam_confidence': None,  # 즉시 차단: 스팸 신뢰도 null
                                    'base_spam_score': None,  # 즉시 차단: 스팸 점수 null
                                    'rule_spam_score': rule_spam_score,
                                    'profanity_detected': profanity_info['profanity_detected'],
                                    'profanity_count': profanity_info['profanity_count'],
                                    'profanity_severity': profanity_info['severity'],
                                    'profanity_boost': profanity_boost,
                                    'types': metadata.get('types', ['도배 및 광고']),  # 유사 사례의 타입 사용
                                    'weights': {
                                        'bert': 1.0,
                                        'llm': 0.0  # LLM 사용 안함
                                    },
                                    'rag_enabled': self.rag_enabled,
                                    'similar_cases_count': len(similar_cases),
                                    'max_similarity': similarity / 100.0,  # 0-1 범위로 변환
                                    'adjustment_applied': False,  # 즉시 차단은 RAG 보정 미적용
                                    'adjustment_weight': 0.0,
                                    'auto_blocked': True,
                                    'auto_block_reason': auto_block_reason,
                                    'adjusted_immoral_score': None,  # 즉시 차단은 보정 점수 없음
                                    'adjusted_spam_score': None,  # 즉시 차단은 보정 점수 없음
                                    'rag_similar_cases': [{
                                        'sentence': case.get('document', ''),
                                        'similarity': similarity,
                                        'immoral_score': immoral_score,
                                        'spam_score': spam_score,
                                        'confidence': confidence,
                                        'confirmed': True,
                                        'feedback_type': 'admin_confirmed',
                                        'created_at': metadata.get('created_at', '')
                                    }]
                                })
                                return result
                    
                    # 유사 사례 요약 생성 (최대 5개)
                    for case in similar_cases[:5]:
                        metadata = case.get('metadata', {})
                        rag_case_summaries.append({
                            'sentence': case.get('document', ''),
                            'similarity': case.get('score', 0.0) * 100,  # 0-100 범위로 변환
                            'immoral_score': float(metadata.get('immoral_score', 0.0)),
                            'spam_score': float(metadata.get('spam_score', 0.0)),
                            'confidence': float(metadata.get('confidence', 0.0)),
                            'confirmed': bool(metadata.get('confirmed', False)),
                            'feedback_type': metadata.get('feedback_type', ''),
                            'created_at': metadata.get('created_at', '')
                        })

                    # 점수 보정 계산
                    adjusted_scores = self._adjust_scores_with_similarity(
                        base_immoral_score=base_final_score,
                        base_spam_score=base_final_spam_score,
                        similar_cases=similar_cases
                    )
                    
                    # 점수 결합
                    combined_scores = self._combine_scores(
                        base_immoral_score=base_final_score,
                        base_spam_score=base_final_spam_score,
                        adjusted_scores=adjusted_scores
                    )
                    
                    adjusted_immoral_score = combined_scores['final_immoral_score']
                    adjusted_spam_score = combined_scores['final_spam_score']
                    adjustment_applied = combined_scores['adjustment_applied']
                    similar_cases_count = adjusted_scores['similar_case_count']
                    max_similarity = adjusted_scores['max_similarity']
                    adjustment_weight = combined_scores.get('adjustment_weight', 0.0)

                    # 신뢰도 부스트 적용
                    if adjustment_applied:
                        final_confidence = min(100.0, final_confidence + adjusted_scores['confidence_boost'])
                        spam_confidence = min(100.0, spam_confidence + adjusted_scores['confidence_boost'] * 0.5)
            except Exception as e:
                print(f"[WARN] RAG 보정 중 오류: {e}")
        
        # 즉시 차단되지 않은 경우에만 LLM 분석 수행
        if not auto_blocked:
            print(f"[INFO] LLM 분석 수행 중...")
            
            # LLM 분석
            llm_result = self._analyze_with_llm(text)
            llm_score = llm_result['immoral_score']
            llm_confidence = llm_result['confidence']
            llm_spam_score = llm_result['spam_score']
            
            # 스팸 점수 결합
        if rule_spam_score >= 80:
            final_spam_score = (llm_spam_score * 0.3) + (rule_spam_score * 0.7)
        else:
            final_spam_score = (llm_spam_score * 0.6) + (rule_spam_score * 0.4)
        
            # 스팸 신뢰도 계산
        if rule_spam_score > 60:
                rule_confidence = 95.0
        elif rule_spam_score > 30:
                rule_confidence = 85.0
        else:
                rule_confidence = 70.0
        
        spam_confidence = (llm_confidence * 0.6) + (rule_confidence * 0.4)
        
        result.update({
            'llm_score': llm_score,
            'llm_confidence': llm_confidence,
            'llm_spam_score': llm_spam_score,
            'rule_spam_score': rule_spam_score,
            'spam_score': final_spam_score,
            'spam_confidence': spam_confidence,
            'types': llm_result['types'],
            'profanity_detected': profanity_info['profanity_detected'],
            'profanity_count': profanity_info['profanity_count'],
            'profanity_severity': profanity_info['severity'],
            'profanity_boost': profanity_boost
        })
        
        # 신뢰도 기반 가중치 계산
        bert_weight = bert_confidence
        llm_weight = llm_confidence
        total_weight = bert_weight + llm_weight
        
        if total_weight > 0:
            bert_weight_norm = bert_weight / total_weight
            llm_weight_norm = llm_weight / total_weight
        else:
            bert_weight_norm = 0.5
            llm_weight_norm = 0.5
        
        # 가중 평균으로 기본 비윤리 점수 계산
        base_score = (bert_score * bert_weight_norm) + (llm_score * llm_weight_norm)
        final_confidence = (bert_confidence * bert_weight_norm) + (llm_confidence * llm_weight_norm)
        
        # 욕설 부스트 적용
        base_final_score = min(base_score + profanity_boost, 100.0)
        base_final_spam_score = final_spam_score
        
        # RAG 보정이 있었다면 재계산
        if self.rag_enabled and similar_cases and not auto_blocked:
            try:
                # 점수 보정 계산
                adjusted_scores = self._adjust_scores_with_similarity(
                    base_immoral_score=base_final_score,
                    base_spam_score=base_final_spam_score,
                    similar_cases=similar_cases
                )
                
                # 점수 결합
                combined_scores = self._combine_scores(
                    base_immoral_score=base_final_score,
                    base_spam_score=base_final_spam_score,
                    adjusted_scores=adjusted_scores
                )
                
                adjusted_immoral_score = combined_scores['final_immoral_score']
                adjusted_spam_score = combined_scores['final_spam_score']
                adjustment_applied = combined_scores['adjustment_applied']
                similar_cases_count = adjusted_scores['similar_case_count']
                max_similarity = adjusted_scores['max_similarity']
                adjustment_weight = combined_scores.get('adjustment_weight', 0.0)
                
                # 신뢰도 부스트 적용
                if adjustment_applied:
                    final_confidence = min(100.0, final_confidence + adjusted_scores['confidence_boost'])
                    spam_confidence = min(100.0, spam_confidence + adjusted_scores['confidence_boost'] * 0.5)
            except Exception as e:
                print(f"[WARN] RAG 점수 보정 중 오류: {e}")
        
        # 최종 점수 결정
        final_score = adjusted_immoral_score if adjustment_applied else base_final_score
        final_spam_score_result = adjusted_spam_score if adjustment_applied else base_final_spam_score
        
        # ⚡ 고신뢰도 케이스 자동 저장 (신뢰도 80 이상) - 비동기로 백그라운드 처리
        if final_confidence >= 80.0 or spam_confidence >= 80.0:
            try:
                self._auto_save_high_confidence_case_async(
                    text=text,
                    immoral_score=final_score,
                    spam_score=final_spam_score_result,
                    confidence=final_confidence,
                    spam_confidence=spam_confidence
                )
            except Exception as e:
                print(f"[WARN] 고신뢰도 케이스 자동 저장 실패: {e}")
        
        result.update({
            'base_score': base_score,
            'final_score': final_score,
            'final_confidence': final_confidence,
            'spam_score': final_spam_score_result,
            'spam_confidence': spam_confidence,
            'base_spam_score': base_final_spam_score,  # RAG 보정 전 스팸 점수 추가
            'weights': {
                'bert': bert_weight_norm,
                'llm': llm_weight_norm
            },
            'rag_enabled': self.rag_enabled,
            'similar_cases_count': similar_cases_count,
            'max_similarity': max_similarity,
            'adjustment_applied': adjustment_applied,
            'adjustment_weight': adjustment_weight if adjustment_applied else 0.0,
            'adjusted_immoral_score': adjusted_immoral_score if adjustment_applied else None,
            'adjusted_spam_score': adjusted_spam_score if adjustment_applied else None,
                'rag_similar_cases': rag_case_summaries,
                'auto_blocked': False
        })
        
        return result
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """여러 텍스트 일괄 분석 (LLM 필수 사용)"""
        results = []
        for text in texts:
            results.append(self.analyze(text))
        return results

