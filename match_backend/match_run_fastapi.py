#!/usr/bin/env python3
"""
FastAPI 신고 검증 플랫폼 실행 스크립트
기존 Streamlit 앱을 FastAPI로 완전 변환한 버전
"""

import uvicorn
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('match_config.env')

def main():
    """FastAPI 서버 실행"""
    print("🚀 FastAPI 신고 검증 플랫폼을 시작합니다...")
    print("📱 메인 앱: http://localhost:8000")
    print("📊 관리자 페이지: http://localhost:8000/admin")  
    print("📚 API 문서: http://localhost:8000/docs")
    print("🔄 종료하려면 Ctrl+C를 누르세요")
    print("-" * 50)
    
    # API 키 확인
    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        print("⚠️  경고: config.env 파일에 OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   AI 분석 기능이 작동하지 않을 수 있습니다.")
        print()
    
    # FastAPI 서버 실행
    uvicorn.run(
        "match_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[".", "templates", "static"],
        log_level="info"
    )

if __name__ == "__main__":
    main()
