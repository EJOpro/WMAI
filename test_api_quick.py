"""빠른 API 테스트"""
import requests
import time
import json

print("서버 시작 대기 (5초)...")
time.sleep(5)

print("\n" + "=" * 60)
print("API 테스트 시작")
print("=" * 60)

try:
    print("\n1. API 호출 중...")
    response = requests.get('http://localhost:8000/api/trends', timeout=10)
    
    print(f"   상태: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n2. 데이터 소스: {data.get('source', 'UNKNOWN')}")
        
        if data.get('source') == 'mysql':
            print("   [OK] MySQL에서 데이터 가져옴!")
        elif data.get('source') == 'fallback':
            print("   [WARNING] Fallback 데이터 사용 중")
            if 'error' in data:
                print(f"   에러: {data['error'][:100]}")
        
        print(f"\n3. 데이터 구조 확인:")
        print(f"   - summary: {'OK' if 'summary' in data else 'MISSING'}")
        print(f"   - keywords: {len(data.get('keywords', []))}개")
        print(f"   - trends: {len(data.get('trends', []))}개")
        print(f"   - timeline: {len(data.get('timeline', []))}개")
        
        if data.get('keywords'):
            print(f"\n4. 상위 3개 키워드:")
            for kw in data['keywords'][:3]:
                print(f"   - {kw['word']}: {kw['count']}회")
        
        print(f"\n[결과] API 정상 작동!")
        
    else:
        print(f"   [ERROR] HTTP {response.status_code}")
        
except requests.exceptions.Timeout:
    print("   [ERROR] 타임아웃! 서버 응답이 너무 느립니다.")
    print("\n   가능한 원인:")
    print("   1. MySQL 쿼리가 느림")
    print("   2. 데이터베이스 연결 문제")
    print("   3. 서버 코드에 무한 루프나 블로킹")
except requests.exceptions.ConnectionError:
    print("   [ERROR] 서버에 연결할 수 없습니다.")
    print("   서버가 실행 중인지 확인하세요.")
except Exception as e:
    print(f"   [ERROR] {type(e).__name__}: {str(e)[:100]}")


