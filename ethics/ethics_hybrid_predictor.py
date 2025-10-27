"""
하이브리드 비윤리 판단 시스템
기존 BERT 모델 + OpenAI LLM 결합
"""
import os
import json
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from ethics.ethics_predict import EthicsPredictor

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
                 model_path='models/binary_classifier.pth',
                 config_path='models/config.json',
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
        self.model_name = model_name or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        self.client = OpenAI(api_key=self.api_key)
        print(f"[INFO] LLM 모델 연결 완료: {self.model_name}")
    
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
        
        # 6. 짧은 텍스트는 스팸 가능성 낮음
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
    
    def analyze(self, text: str) -> Dict:
        """하이브리드 분석 수행 (LLM 필수 사용)"""
        # 1. BERT 모델 분석
        bert_result = self.bert_predictor.predict(text)
        bert_score = bert_result['probabilities']['비윤리적'] * 100
        bert_confidence = bert_result['confidence'] * 100
        
        result = {
            'text': text,
            'bert_score': bert_score,
            'bert_confidence': bert_confidence,
        }
        
        # 2. LLM 분석 (필수)
        llm_result = self._analyze_with_llm(text)
        llm_score = llm_result['immoral_score']
        llm_confidence = llm_result['confidence']
        llm_spam_score = llm_result['spam_score']
        
        # 3. 규칙 기반 스팸 점수 계산
        rule_spam_score = self._calculate_rule_based_spam_score(text)
        
        # 4. 욕설 감지 및 부스트 계산
        profanity_info = self._calculate_profanity_boost(text)
        profanity_boost = profanity_info['boost_score']
        
        # 5. 스팸 점수 결합
        final_spam_score = (llm_spam_score * 0.6) + (rule_spam_score * 0.4)
        
        result.update({
            'llm_score': llm_score,
            'llm_confidence': llm_confidence,
            'llm_spam_score': llm_spam_score,
            'rule_spam_score': rule_spam_score,
            'spam_score': final_spam_score,
            'types': llm_result['types'],
            'profanity_detected': profanity_info['profanity_detected'],
            'profanity_count': profanity_info['profanity_count'],
            'profanity_severity': profanity_info['severity'],
            'profanity_boost': profanity_boost
        })
        
        # 6. 신뢰도 기반 가중치 계산
        bert_weight = bert_confidence
        llm_weight = llm_confidence
        total_weight = bert_weight + llm_weight
        
        if total_weight > 0:
            bert_weight_norm = bert_weight / total_weight
            llm_weight_norm = llm_weight / total_weight
        else:
            bert_weight_norm = 0.5
            llm_weight_norm = 0.5
        
        # 7. 가중 평균으로 기본 비윤리 점수 계산
        base_score = (bert_score * bert_weight_norm) + (llm_score * llm_weight_norm)
        final_confidence = (bert_confidence * bert_weight_norm) + (llm_confidence * llm_weight_norm)
        
        # 8. 욕설 부스트 적용하여 최종 점수 계산
        final_score = min(base_score + profanity_boost, 100.0)
        
        result.update({
            'base_score': base_score,
            'final_score': final_score,
            'final_confidence': final_confidence,
            'weights': {
                'bert': bert_weight_norm,
                'llm': llm_weight_norm
            }
        })
        
        return result
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """여러 텍스트 일괄 분석 (LLM 필수 사용)"""
        results = []
        for text in texts:
            results.append(self.analyze(text))
        return results

