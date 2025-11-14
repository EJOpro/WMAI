"""API 응답 상세 진단"""
import requests
import json

print("=" * 60)
print("API 응답 진단")
print("=" * 60)

try:
    response = requests.get('http://localhost:8000/api/trends', timeout=5)
    
    print(f"\n상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n데이터 소스: {data.get('source', 'N/A')}")
        print(f"타임스탬프: {data.get('timestamp', 'N/A')}")
        
        # Summary 확인
        if 'summary' in data:
            print(f"\n✓ summary 존재:")
            for key, value in data['summary'].items():
                print(f"  - {key}: {value}")
        else:
            print("\n✗ summary 없음")
        
        # Keywords 확인
        if 'keywords' in data and data['keywords']:
            print(f"\n✓ keywords 존재: {len(data['keywords'])}개")
            print("  상위 3개:")
            for kw in data['keywords'][:3]:
                print(f"    - {kw}")
        else:
            print("\n✗ keywords 비어있음 또는 없음")
        
        # Trends 확인
        if 'trends' in data and data['trends']:
            print(f"\n✓ trends 존재: {len(data['trends'])}개")
            print("  상위 3개:")
            for tr in data['trends'][:3]:
                print(f"    - {tr}")
        else:
            print("\n✗ trends 비어있음 또는 없음")
        
        # Timeline 확인
        if 'timeline' in data and data['timeline']:
            print(f"\n✓ timeline 존재: {len(data['timeline'])}개 포인트")
            print("  샘플:")
            for tl in data['timeline'][:2]:
                print(f"    - {tl}")
        else:
            print("\n✗ timeline 비어있음 또는 없음")
        
        # 에러 메시지 확인
        if 'error' in data:
            print(f"\n⚠ 에러 메시지: {data['error']}")
        
        print("\n" + "=" * 60)
        print("전체 응답 구조:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        
    else:
        print(f"에러: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n✗ 서버에 연결할 수 없습니다.")
    print("서버를 실행하세요: uvicorn app.main:app --reload")
except Exception as e:
    print(f"\n✗ 오류: {e}")


