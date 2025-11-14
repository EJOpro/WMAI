"""트렌드 테이블 자동 생성 스크립트"""
from app.database import get_db_connection

print("=" * 60)
print("트렌드 테이블 생성 중...")
print("=" * 60)

# SQL 파일 읽기
try:
    with open('db/migration_add_trend_keywords.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # USE wmai_db; 제거 (이미 연결되어 있음)
    sql_content = sql_content.replace('USE wmai_db;', '')
    
    # SQL 문을 세미콜론으로 분리
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for i, statement in enumerate(statements, 1):
            # SELECT 문과 주석은 건너뛰기
            if statement.upper().startswith('SELECT') or not statement:
                continue
                
            try:
                print(f"\n{i}. 실행 중: {statement[:50]}...")
                cursor.execute(statement)
                print(f"   [OK] 성공")
            except Exception as e:
                # 이미 존재하는 테이블은 무시
                if 'already exists' in str(e) or '1050' in str(e):
                    print(f"   [INFO] 이미 존재함 (건너뜀)")
                else:
                    print(f"   [ERROR] 실패: {e}")
        
        cursor.close()
    
    print("\n" + "=" * 60)
    print("[OK] 테이블 생성 완료!")
    print("=" * 60)
    
    # 이제 더미 데이터 삽입
    print("\n트렌드 더미 데이터 삽입 중...")
    print("=" * 60)
    
    with open('db/trend_dummy_data.sql', 'r', encoding='utf-8') as f:
        dummy_sql = f.read()
    
    dummy_sql = dummy_sql.replace('USE wmai_db;', '')
    dummy_statements = [stmt.strip() for stmt in dummy_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for i, statement in enumerate(dummy_statements, 1):
            if statement.upper().startswith('SELECT') or not statement or statement.startswith('DELETE'):
                continue
            
            try:
                # INSERT 문만 진행 상황 표시
                if statement.upper().startswith('INSERT'):
                    print(f"{i}. 데이터 삽입 중...")
                    cursor.execute(statement)
                    print(f"   [OK] {cursor.rowcount}개 행 삽입")
            except Exception as e:
                if 'Duplicate entry' in str(e):
                    print(f"   [INFO] 중복 데이터 (건너뜀)")
                else:
                    print(f"   [ERROR] {e}")
        
        cursor.close()
    
    print("\n" + "=" * 60)
    print("[OK] 모든 설정 완료!")
    print("=" * 60)
    print("\n다음 단계:")
    print("1. 서버 실행: uvicorn app.main:app --reload")
    print("2. 브라우저에서 확인:")
    print("   - http://localhost:8000/trends")
    print("   - http://localhost:8000/api/trends")
    
except FileNotFoundError as e:
    print(f"[ERROR] 파일을 찾을 수 없습니다: {e}")
except Exception as e:
    print(f"[ERROR] 오류 발생: {e}")
    import traceback
    traceback.print_exc()

