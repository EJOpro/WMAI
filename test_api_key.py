#!/usr/bin/env python3
"""
OpenAI API 키 테스트 스크립트
"""

import os
from dotenv import load_dotenv

def test_api_key():
    print("🔍 OpenAI API 키 테스트")
    print("=" * 50)
    
    # 환경 변수 로드
    load_dotenv('match_config.env')
    
    # API 키 확인
    api_key = os.getenv('OPENAI_API_KEY', '')
    
    if not api_key:
        print("❌ API 키가 설정되지 않았습니다.")
        print("📝 해결 방법:")
        print("   1. match_config.env 파일이 있는지 확인")
        print("   2. OPENAI_API_KEY=your-actual-key 형태로 설정")
        return False
    
    if api_key == 'your-api-key-here':
        print("❌ API 키가 예시 값으로 설정되어 있습니다.")
        print("📝 해결 방법:")
        print("   1. https://platform.openai.com/api-keys 에서 실제 API 키 발급")
        print("   2. match_config.env 파일에 실제 키 입력")
        return False
    
    print(f"✅ API 키 로드 성공: {api_key[:10]}...{api_key[-4:]}")
    
    # OpenAI 라이브러리 테스트
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI 라이브러리 로드 성공")
        
        # 간단한 API 호출 테스트
        print("🧪 API 연결 테스트 중...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("✅ OpenAI API 연결 성공!")
        print(f"📝 응답: {response.choices[0].message.content}")
        return True
        
    except ImportError:
        print("❌ OpenAI 라이브러리가 설치되지 않았습니다.")
        print("📝 해결 방법: pip install openai")
        return False
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        print("📝 해결 방법:")
        print("   1. API 키가 유효한지 확인")
        print("   2. 인터넷 연결 확인")
        print("   3. OpenAI 계정에 크레딧이 있는지 확인")
        return False

if __name__ == "__main__":
    success = test_api_key()
    if success:
        print("\n🎉 모든 테스트 통과! WMAA 시스템을 사용할 수 있습니다.")
    else:
        print("\n❌ 설정을 완료한 후 다시 테스트해주세요.")
