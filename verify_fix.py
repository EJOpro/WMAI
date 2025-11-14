"""수정 사항 검증 스크립트"""
import requests
import time

print("=" * 70)
print("트렌드 시스템 수정 검증")
print("=" * 70)

# 1. API 테스트
print("\n[1/3] API 응답 테스트...")
try:
    response = requests.get('http://localhost:8000/api/trends', timeout=10)
    if response.status_code == 200:
        data = response.json()
        source = data.get('source', 'UNKNOWN')
        keywords_count = len(data.get('keywords', []))
        trends_count = len(data.get('trends', []))
        
        print(f"  [OK] API 정상 작동")
        print(f"  [OK] 데이터 소스: {source}")
        print(f"  [OK] 키워드: {keywords_count}개")
        print(f"  [OK] 트렌드: {trends_count}개")
        
        if source == 'mysql':
            print("  [OK] MySQL에서 데이터 가져옴 - 성공!")
        else:
            print(f"  [WARNING] source가 '{source}'입니다. 'mysql'이어야 합니다.")
    else:
        print(f"  [ERROR] API 오류: HTTP {response.status_code}")
except Exception as e:
    print(f"  [ERROR] API 테스트 실패: {e}")

# 2. trends.html 파일 확인
print("\n[2/3] trends.html 수정 확인...")
try:
    with open('app/templates/pages/trends.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
        if 'fetch(endpoint)' in content:
            print("  [OK] apiRequest 함수 수정됨")
        else:
            print("  [ERROR] apiRequest 함수가 수정되지 않았습니다")
        
        if 'localhost:8001/api/v1/community/wordcloud' in content:
            print("  [WARNING] 여전히 잘못된 API 호출이 있습니다")
        else:
            print("  [OK] 잘못된 API 호출 제거됨")
except Exception as e:
    print(f"  [ERROR] 파일 확인 실패: {e}")

# 3. 데이터베이스 확인
print("\n[3/3] 데이터베이스 확인...")
try:
    from app.database import get_db_connection
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as cnt FROM trend_keywords")
        result = cursor.fetchone()
        count = result['cnt']
        
        print(f"  [OK] trend_keywords: {count}개 레코드")
        
        if count >= 10:
            print("  [OK] 충분한 데이터 존재")
        else:
            print(f"  [WARNING] 데이터가 부족합니다 (최소 10개 필요)")
        
        cursor.close()
except Exception as e:
    print(f"  [ERROR] 데이터베이스 확인 실패: {e}")

print("\n" + "=" * 70)
print("검증 완료!")
print("=" * 70)
print("\n다음 단계:")
print("1. 브라우저에서 http://localhost:8000/trends 접속")
print("2. Ctrl + Shift + R 로 강력 새로고침")
print("3. F12로 개발자 도구를 열고 Console 탭 확인")
print("4. '[OK] API 응답 성공: mysql' 메시지 확인")

