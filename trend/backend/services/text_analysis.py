"""텍스트 분석 서비스 - 워드클라우드 및 키워드 추출"""
from typing import List, Dict, Tuple, Optional
from collections import Counter
import re
from datetime import datetime
from loguru import logger

try:
    import konlpy
    KONLPY_AVAILABLE = True
except ImportError:
    KONLPY_AVAILABLE = False
    logger.warning("konlpy not available. Korean text analysis will be limited.")


class TextAnalysisService:
    """텍스트 분석 서비스"""
    
    def __init__(self):
        """초기화"""
        if KONLPY_AVAILABLE:
            try:
                from konlpy.tag import Okt
                self.okt = Okt()
                logger.info("KoNLPy initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize KoNLPy: {e}. Using simple tokenization.")
                self.okt = None
        else:
            self.okt = None
        
        # 불용어 목록 (한글)
        self.stopwords = {
            '이', '그', '저', '것', '수', '등', '들', '및', '또는', '하다', '되다', '있다', '없다',
            '같다', '다르다', '아니다', '이다', '그렇다', '아', '휴', '아이구', '아이고', '어', '나',
            '우리', '저희', '따라', '의해', '을', '를', '에', '의', '가', '으로', '로', '에게', '뿐',
            '의거하여', '근거하여', '입각하여', '기준으로', '예하면', '예를', '들면', '들자면',
            '저', '소인', '소생', '저희', '지말고', '하지마', '하지마라', '다른', '물론', '또한',
            '그리고', '비길수', '없다', '해서는', '안된다', '뿐만', '아니라', '만이', '아니다',
            '만은', '아니다', '막론하고', '관계없이', '그치지', '않다', '그러나', '그런데', '하지만',
            '든간에', '논하지', '않다', '따지지', '않다', '설사', '비록', '더라도', '아니면',
            '만', '못하다', '하는', '편이', '낫다', '불문하고', '향하여', '향해서', '향하다',
            '쪽으로', '틈타', '이용하여', '타다', '오르다', '제외하고', '이', '외에', '이', '밖에',
            '하여야', '비로소', '한다면', '몰라도', '외에도', '이곳', '여기', '부터', '기점으로',
            '따라서', '할', '생각이다', '하려고하다', '이리하여', '그리하여', '그렇게', '함으로써',
            '하지만', '일때', '할때', '앞에서', '중에서', '보는데서', '으로써', '로써', '까지',
            '해야한다', '일것이다', '반드시', '할줄알다', '할수있다', '할수있어', '임에', '틀림없다',
            '한다면', '등', '등등', '제', '겨우', '단지', '다만', '할뿐', '딩동', '댕그', '대해서',
            '대하여', '대하면', '훨씬', '얼마나', '얼마만큼', '얼마큼', '남짓', '여', '얼마간',
            '약간', '다소', '좀', '조금', '다수', '몇', '거의', '하마터면', '인젠', '이젠', '된바에야',
            '된이상', '만큼', '어찌됏든', '그위에', '게다가', '점에서', '보아', '비추어', '보아',
            '고려하면', '하게될것이다', '일것이다', '비교적', '좀', '보다더', '비하면', '시키다',
            '하게하다', '할만하다', '의해서', '연이서', '이어서', '잇따라', '뒤따라', '뒤이어',
            '결국', '의지하여', '기대여', '통하여', '자마자', '더욱더', '불구하고', '얼마든지',
            '마음대로', '주저하지', '않고', '곧', '즉시', '바로', '당장', '하자마자', '밖에', '안된다',
            '하면된다', '그래', '그렇지', '네', '예', '응', 'ㅋ', 'ㅎ', 'ㅠ', 'ㅜ'
        }
        
        # 영문 불용어
        self.stopwords_en = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your',
            'his', 'her', 'its', 'our', 'their'
        }
    
    def extract_keywords(
        self, 
        texts: List[str], 
        top_k: int = 100,
        min_length: int = 2
    ) -> List[Tuple[str, int]]:
        """
        텍스트에서 키워드 추출
        
        Args:
            texts: 텍스트 리스트
            top_k: 상위 K개 키워드
            min_length: 최소 단어 길이
            
        Returns:
            (단어, 빈도) 튜플 리스트
        """
        all_words = []
        
        for text in texts:
            if not text:
                continue
            
            # 한글 텍스트 처리
            if self._contains_korean(text):
                words = self._extract_korean_nouns(text)
            else:
                # 영어 및 기타 언어 처리
                words = self._extract_english_words(text)
            
            all_words.extend(words)
        
        # 불용어 제거 및 길이 필터링
        filtered_words = [
            word for word in all_words 
            if len(word) >= min_length 
            and word not in self.stopwords 
            and word not in self.stopwords_en
            and not self._is_special_char(word)
        ]
        
        # 빈도 계산
        word_counts = Counter(filtered_words)
        
        # 상위 K개 반환
        return word_counts.most_common(top_k)
    
    def _contains_korean(self, text: str) -> bool:
        """한글 포함 여부 확인"""
        return bool(re.search(r'[가-힣]', text))
    
    def _extract_korean_nouns(self, text: str) -> List[str]:
        """한글 명사 추출"""
        # konlpy 대신 간단한 한글 단어 분리 사용
        import re
        
        # 한글 단어만 추출 (2글자 이상)
        korean_words = re.findall(r'[가-힣]{2,}', text)
        
        # 중복 제거 및 불용어 필터링
        filtered_words = []
        for word in korean_words:
            if len(word) >= 2 and word not in self.stopwords:
                filtered_words.append(word)
        
        return filtered_words
    
    def _extract_english_words(self, text: str) -> List[str]:
        """영어 단어 추출"""
        # 소문자 변환 및 특수문자 제거
        text = text.lower()
        # 영문자와 숫자만 남기기
        words = re.findall(r'\b[a-z0-9]+\b', text)
        return words
    
    def _is_special_char(self, word: str) -> bool:
        """특수문자 여부 확인"""
        # 숫자로만 구성된 경우도 제외
        if word.isdigit():
            return True
        # 특수문자가 포함된 경우
        if re.search(r'[^\w\s가-힣]', word):
            return True
        return False
    
    def calculate_word_weights(
        self, 
        word_counts: List[Tuple[str, int]]
    ) -> List[Dict[str, any]]:
        """
        단어 가중치 계산 (워드클라우드용)
        
        Args:
            word_counts: (단어, 빈도) 튜플 리스트
            
        Returns:
            {word, frequency, weight} 딕셔너리 리스트
        """
        if not word_counts:
            return []
        
        max_count = word_counts[0][1]
        
        result = []
        for word, count in word_counts:
            weight = count / max_count if max_count > 0 else 0
            result.append({
                'word': word,
                'frequency': count,
                'weight': round(weight, 3)
            })
        
        return result
    
    def extract_keywords_by_timeframe(
        self,
        texts_with_timestamp: List[Tuple[datetime, str]],
        granularity: str = '1d',
        keywords: Optional[List[str]] = None
    ) -> Dict[datetime, Dict[str, int]]:
        """
        시간대별 키워드 추출
        
        Args:
            texts_with_timestamp: (타임스탬프, 텍스트) 튜플 리스트
            granularity: 집계 단위 ('1h', '1d', '1w')
            keywords: 특정 키워드만 추적 (None이면 자동 추출)
            
        Returns:
            {타임스탬프: {키워드: 빈도}} 딕셔너리
        """
        from datetime import timedelta
        
        # 시간 버킷 함수
        def get_bucket(dt: datetime) -> datetime:
            if granularity == '1h':
                return dt.replace(minute=0, second=0, microsecond=0)
            elif granularity == '1d':
                return dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif granularity == '1w':
                # 주의 시작 (월요일)
                days_since_monday = dt.weekday()
                monday = dt - timedelta(days=days_since_monday)
                return monday.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                return dt
        
        # 시간별로 텍스트 그룹화
        grouped_texts = {}
        for timestamp, text in texts_with_timestamp:
            bucket = get_bucket(timestamp)
            if bucket not in grouped_texts:
                grouped_texts[bucket] = []
            grouped_texts[bucket].append(text)
        
        # 각 시간대별로 키워드 추출
        result = {}
        for bucket, texts in sorted(grouped_texts.items()):
            if keywords:
                # 특정 키워드 빈도 계산
                keyword_counts = {}
                for text in texts:
                    text_lower = text.lower()
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        count = text_lower.count(keyword_lower)
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + count
                result[bucket] = keyword_counts
            else:
                # 모든 키워드 추출
                word_counts = self.extract_keywords(texts, top_k=50)
                result[bucket] = {word: count for word, count in word_counts}
        
        return result


# 싱글톤 인스턴스
text_analysis_service = TextAnalysisService()

