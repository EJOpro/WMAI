"""
Vision API 테스트 스크립트
이미지 분석이 제대로 작동하는지 확인
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def test_vision_api():
    """Vision API 테스트"""
    print("=" * 60)
    print("Vision API 테스트")
    print("=" * 60)
    
    # 1. OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다!")
        print("\n.env 파일에 다음을 추가하세요:")
        print("OPENAI_API_KEY=sk-...")
        return
    
    print(f"✅ API 키 확인: {api_key[:20]}...")
    
    # 2. Vision Analyzer 로드
    try:
        from ethics.vision_analyzer import VisionEthicsAnalyzer
        print("✅ Vision Analyzer 모듈 로드 성공")
    except ImportError as e:
        print(f"❌ Vision Analyzer 모듈 로드 실패: {e}")
        print("\npip install openai 실행 필요")
        return
    
    # 3. Analyzer 초기화
    try:
        analyzer = VisionEthicsAnalyzer()
        print("✅ Vision Analyzer 초기화 성공")
    except Exception as e:
        print(f"❌ Vision Analyzer 초기화 실패: {e}")
        return
    
    # 4. 업로드된 이미지 찾기
    upload_dir = Path("app/static/uploads/board")
    if not upload_dir.exists():
        print(f"❌ 업로드 디렉토리가 없습니다: {upload_dir}")
        return
    
    images = list(upload_dir.glob("*"))
    if not images:
        print(f"⚠️ 업로드된 이미지가 없습니다: {upload_dir}")
        print("\n게시글에 이미지를 업로드한 후 다시 시도하세요.")
        return
    
    print(f"\n✅ 이미지 발견: {len(images)}개")
    test_image = images[0]
    print(f"테스트 이미지: {test_image.name}")
    
    # 5. Vision API 테스트
    print("\n" + "=" * 60)
    print("Vision API 호출 중... (최대 10초 소요)")
    print("=" * 60)
    
    try:
        result = analyzer.analyze_image(str(test_image))
        
        print("\n✅ Vision API 호출 성공!")
        print("\n📊 분석 결과:")
        print(f"  비윤리 점수: {result.get('immoral_score', 'N/A')}")
        print(f"  스팸 점수: {result.get('spam_score', 'N/A')}")
        print(f"  신뢰도: {result.get('confidence', 'N/A')}")
        print(f"  감지된 유형: {result.get('types', [])}")
        print(f"  차단 여부: {result.get('is_blocked', False)}")
        print(f"  판단 근거: {result.get('reasoning', 'N/A')[:100]}...")
        
        if result.get('has_text'):
            print(f"  텍스트 포함: {result.get('has_text')}")
            print(f"  추출된 텍스트: {result.get('extracted_text', '')[:100]}...")
        
        # 6. 점수 확인
        if result.get('immoral_score') is None and result.get('spam_score') is None:
            print("\n⚠️ 경고: 점수가 없습니다!")
            print("원본 응답 확인:")
            print(result)
        else:
            print("\n✅ 모든 점수가 정상적으로 반환되었습니다!")
        
    except Exception as e:
        print(f"\n❌ Vision API 호출 실패: {e}")
        print("\n가능한 원인:")
        print("  1. OpenAI API 크레딧 부족")
        print("  2. 네트워크 연결 문제")
        print("  3. API 키 권한 문제")
        print("  4. 이미지 파일 손상")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == '__main__':
    test_vision_api()

