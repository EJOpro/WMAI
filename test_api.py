"""API 테스트 스크립트"""
import requests
import json
import time

print("서버 시작 대기 중...")
time.sleep(3)

print("\nAPI 테스트: http://localhost:8000/api/trends")
print("=" * 60)

try:
    response = requests.get('http://localhost:8000/api/trends')
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n[OK] API 응답 성공!")
        print(f"데이터 소스: {data.get('source', 'N/A')}")
        
        if 'summary' in data:
            print(f"\n통계:")
            print(f"  - 게시글: {data['summary'].get('total_posts', 0):,}개")
            print(f"  - 댓글: {data['summary'].get('total_comments', 0):,}개")
            print(f"  - 키워드: {data['summary'].get('unique_keywords', 0)}개")
        
        if 'keywords' in data and data['keywords']:
            print(f"\n상위 5개 키워드:")
            for i, kw in enumerate(data['keywords'][:5], 1):
                print(f"  {i}. {kw['word']}: {kw['count']}회")
        
        if 'trends' in data and data['trends']:
            print(f"\n트렌드 (상위 3개):")
            for i, trend in enumerate(data['trends'][:3], 1):
                print(f"  {i}. {trend['keyword']}: {trend['change']:+.1f}% ({trend['category']})")
        
        print(f"\n[성공] 데이터가 정상적으로 표시됩니다!")
        print(f"\n브라우저에서 확인하세요:")
        print(f"  http://localhost:8000/trends")
        
    else:
        print(f"[오류] HTTP {response.status_code}")
        print(response.text[:200])
        
except requests.exceptions.ConnectionError:
    print("[오류] 서버에 연결할 수 없습니다.")
    print("서버를 실행하세요: uvicorn app.main:app --reload")
except Exception as e:
    print(f"[오류] {e}")

