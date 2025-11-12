"""
OpenAI Vision API를 활용한 이미지 윤리/스팸 분석 모듈
"""
import base64
import os
import json
from typing import Dict, Tuple
from pathlib import Path
from dotenv import load_dotenv

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[WARN] OpenAI 모듈 로드 실패")

load_dotenv()


class VisionEthicsAnalyzer:
    """이미지 윤리/스팸 분석기 (OpenAI Vision API)"""
    
    def __init__(self):
        """Vision API 초기화"""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai 라이브러리가 설치되지 않았습니다")
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다")
        
        self.client = OpenAI(api_key=api_key)
        print("[INFO] Vision API 초기화 완료")
    
    def analyze_image(self, image_path: str) -> Dict:
        """
        이미지 윤리/스팸 분석
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            {
                'immoral_score': 0-100,
                'spam_score': 0-100,
                'confidence': 0-100,
                'types': ['욕설', '음란물', '광고', ...],
                'has_text': True/False,
                'extracted_text': '이미지 내 텍스트',
                'is_blocked': True/False
            }
        """
        try:
            # 이미지를 base64로 인코딩
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 파일 확장자 확인
            ext = Path(image_path).suffix.lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(ext, 'image/jpeg')
            
            # Vision API 호출 (비용 절감: reasoning 필드 제거)
            response = self.client.chat.completions.create(
                model="gpt-4o",  # GPT-4 Omni (Vision 지원)
                messages=[
                    {
                        "role": "system",
                        "content": """You are an image content moderation expert. Analyze images efficiently.

Analyze the image for:
1. Immoral content: pornography, violence, hate speech, profanity/slander text, etc.
2. Spam content: advertisements, promotions, commercial spam, etc.
3. Extract and analyze text within the image

Scoring criteria:
- immoral_score: 0 (safe) ~ 100 (very dangerous)
- spam_score: 0 (safe) ~ 100 (definitely spam)
- confidence: 0 (uncertain) ~ 100 (certain)

Respond ONLY with valid JSON format. Do not include any other text.
Response format:
{
  "immoral_score": 0,
  "spam_score": 0,
  "confidence": 80,
  "types": ["욕설", "음란물", "광고"],
  "has_text": false,
  "extracted_text": "이미지 내 텍스트가 있다면 한글로 추출"
}"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this image and respond with JSON only."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}",
                                    "detail": "low"  # 비용 절감을 위해 low detail 사용
                                }
                            }
                        ]
                    }
                ],
                max_tokens=400,  # reasoning 제거로 토큰 절약 (800 -> 400)
                temperature=0.1,  # 더 일관된 응답을 위해 낮춤
                response_format={"type": "json_object"}  # JSON 모드 강제
            )
            
            # 결과 파싱
            content = response.choices[0].message.content
            
            # JSON 파싱 시도
            try:
                # 마크다운 코드 블록 제거
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                # JSON 파싱
                result = json.loads(content)
                
                # 필수 필드 확인 및 기본값 설정
                result['immoral_score'] = float(result.get('immoral_score', 0))
                result['spam_score'] = float(result.get('spam_score', 0))
                result['confidence'] = float(result.get('confidence', 50))
                result['types'] = result.get('types', [])
                result['has_text'] = bool(result.get('has_text', False))
                result['extracted_text'] = result.get('extracted_text', '')
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                # JSON 파싱 실패 시 상세 로그 출력
                print(f"[ERROR] Vision API 응답 파싱 실패: {e}")
                print(f"[ERROR] 원본 응답: {content[:500]}")  # 처음 500자만
                
                # 텍스트에서 수동으로 점수 추출 시도
                try:
                    import re
                    immoral = re.search(r'"immoral_score"\s*:\s*(\d+\.?\d*)', content)
                    spam = re.search(r'"spam_score"\s*:\s*(\d+\.?\d*)', content)
                    conf = re.search(r'"confidence"\s*:\s*(\d+\.?\d*)', content)
                    
                    result = {
                        'immoral_score': float(immoral.group(1)) if immoral else 0,
                        'spam_score': float(spam.group(1)) if spam else 0,
                        'confidence': float(conf.group(1)) if conf else 50,
                        'types': [],
                        'has_text': False,
                        'extracted_text': ''
                    }
                    print(f"[INFO] 수동 추출 성공: 비윤리={result['immoral_score']}, 스팸={result['spam_score']}")
                except Exception as extract_error:
                    print(f"[ERROR] 수동 추출도 실패: {extract_error}")
                    result = {
                        'immoral_score': 0,
                        'spam_score': 0,
                        'confidence': 50,
                        'types': [],
                        'has_text': False,
                        'extracted_text': ''
                    }
            
            # 차단 여부 추가
            result['is_blocked'] = self._should_block(result)
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Vision API 분석 실패: {e}")
            return {
                'immoral_score': 0,
                'spam_score': 0,
                'confidence': 0,
                'types': [],
                'has_text': False,
                'extracted_text': '',
                'is_blocked': False
            }
    
    def _should_block(self, result: Dict) -> bool:
        """
        이미지 차단 여부 결정 (내부 메서드)
        
        Args:
            result: analyze_image() 결과
            
        Returns:
            차단 여부
        """
        immoral_score = result.get('immoral_score', 0)
        spam_score = result.get('spam_score', 0)
        confidence = result.get('confidence', 0)
        
        # 차단 기준 (텍스트 필터와 동일)
        if immoral_score >= 80 and confidence >= 80:
            return True
        
        if immoral_score >= 90 and confidence >= 70:
            return True
        
        if spam_score >= 70 and confidence >= 70:
            return True
        
        return False
    
    def should_block_image(self, analysis_result: Dict) -> Tuple[bool, str]:
        """
        이미지 차단 여부 결정 (외부 API)
        
        Args:
            analysis_result: analyze_image() 결과
            
        Returns:
            (차단 여부, 차단 사유)
        """
        is_blocked = analysis_result.get('is_blocked', False)
        
        if not is_blocked:
            return False, ""
        
        # 차단 사유 생성
        types = analysis_result.get('types', [])
        if types:
            reason = f"부적절한 이미지가 감지되었습니다: {', '.join(types)}"
        else:
            immoral = analysis_result.get('immoral_score', 0)
            spam = analysis_result.get('spam_score', 0)
            if immoral >= spam:
                reason = "부적절한 이미지가 포함되어 있습니다"
            else:
                reason = "스팸성 이미지가 포함되어 있습니다"
        
        return True, reason


# 싱글톤 인스턴스
_analyzer_instance = None


def get_vision_analyzer():
    """Vision 분석기 싱글톤 패턴"""
    global _analyzer_instance
    if not OPENAI_AVAILABLE:
        return None
    if _analyzer_instance is None:
        try:
            _analyzer_instance = VisionEthicsAnalyzer()
        except Exception as e:
            print(f"[ERROR] Vision 분석기 초기화 실패: {e}")
            return None
    return _analyzer_instance

