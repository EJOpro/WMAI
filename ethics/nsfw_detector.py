"""
NSFW 이미지 감지 모듈
Hugging Face의 사전 학습된 모델을 사용한 부적절한 이미지 감지
"""
from typing import Dict
from pathlib import Path

try:
    from transformers import pipeline
    from PIL import Image
    NSFW_AVAILABLE = True
except ImportError:
    NSFW_AVAILABLE = False
    print("[WARN] NSFW 모듈 로드 실패: transformers 또는 Pillow 미설치")


class NSFWDetector:
    """NSFW(Not Safe For Work) 이미지 감지기"""
    
    def __init__(self):
        """NSFW 감지 모델 초기화"""
        if not NSFW_AVAILABLE:
            raise ImportError("transformers 또는 Pillow가 설치되지 않았습니다")
        
        try:
            # Falconsai의 NSFW 감지 모델 사용
            self.classifier = pipeline(
                "image-classification",
                model="Falconsai/nsfw_image_detection",
                device=-1  # CPU 사용 (GPU 있으면 0으로 변경)
            )
            print("[INFO] NSFW 감지 모델 로드 완료")
        except Exception as e:
            print(f"[ERROR] NSFW 모델 로드 실패: {e}")
            raise
    
    def analyze(self, image_path: str) -> Dict:
        """
        이미지 NSFW 여부 분석
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            {
                'is_nsfw': bool,
                'confidence': float (0-100),
                'label': str ('nsfw' or 'normal'),
                'raw_scores': [{'label': str, 'score': float}, ...]
            }
        """
        try:
            # 이미지 로드
            image = Image.open(image_path)
            
            # RGB로 변환 (RGBA나 다른 모드 대응)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 분석 실행
            results = self.classifier(image)
            
            # 가장 높은 점수의 결과 사용
            top_result = max(results, key=lambda x: x['score'])
            
            return {
                'is_nsfw': top_result['label'].lower() == 'nsfw',
                'confidence': top_result['score'] * 100,
                'label': top_result['label'],
                'raw_scores': results
            }
            
        except Exception as e:
            print(f"[ERROR] NSFW 분석 실패: {e}")
            return {
                'is_nsfw': False,
                'confidence': 0,
                'label': 'error',
                'raw_scores': []
            }
    
    def should_block(self, analysis_result: Dict, threshold: float = 80.0) -> bool:
        """
        차단 여부 결정
        
        Args:
            analysis_result: analyze() 결과
            threshold: NSFW 차단 임계값 (기본 80%)
            
        Returns:
            차단 여부
        """
        return (
            analysis_result.get('is_nsfw', False) and 
            analysis_result.get('confidence', 0) >= threshold
        )


# 싱글톤 인스턴스
_detector_instance = None


def get_nsfw_detector():
    """NSFW 감지기 싱글톤 패턴"""
    global _detector_instance
    if not NSFW_AVAILABLE:
        return None
    if _detector_instance is None:
        try:
            _detector_instance = NSFWDetector()
        except Exception as e:
            print(f"[ERROR] NSFW 감지기 초기화 실패: {e}")
            return None
    return _detector_instance

