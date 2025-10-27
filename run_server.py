"""
FastAPI 서버 실행 스크립트
시니어의 팁: 이 파일을 실행하면 서버가 시작됩니다!
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    import uvicorn
    
    print("="*60)
    print("  Community Admin FastAPI Server")
    print("="*60)
    print("")
    print("  서버 주소: http://localhost:8000")
    print("  API 문서: http://localhost:8000/docs")
    print("  헬스체크: http://localhost:8000/health")
    print("")
    print("  서버를 종료하려면 Ctrl+C를 누르세요")
    print("="*60)
    print("")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 서버를 종료합니다. 안녕히 가세요!")
    except Exception as e:
        print(f"\n\n❌ 서버 실행 중 오류 발생: {e}")
        print("\n🔍 문제 해결 방법:")
        print("  1. requirements.txt 설치 확인: pip install -r requirements.txt")
        print("  2. 포트 8000이 사용 중인지 확인")
        print("  3. Python 버전 확인: python --version (3.11+ 권장)")

