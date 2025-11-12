"""
churn_analyses 테이블의 results 컬럼을 LONGTEXT로 변경하는 마이그레이션 스크립트
"""
import os
import sys
from dotenv import load_dotenv
import pymysql

# 환경 변수 로드
load_dotenv()

# MySQL 연결 설정
config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'wmai'),
    'password': os.getenv('DB_PASSWORD', '1234'),
    'database': os.getenv('DB_NAME', 'wmai_db'),
    'charset': 'utf8mb4'
}

def run_migration():
    """마이그레이션 실행"""
    try:
        print("=" * 60)
        print("churn_analyses 테이블 마이그레이션 시작")
        print("=" * 60)
        
        # MySQL 연결
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        print(f"\n[연결 성공] MySQL: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        # 현재 컬럼 타입 확인
        cursor.execute("SHOW COLUMNS FROM churn_analyses LIKE 'results'")
        current_column = cursor.fetchone()
        
        if current_column:
            print(f"\n[현재 컬럼 정보]")
            print(f"  컬럼명: {current_column[0]}")
            print(f"  타입: {current_column[1]}")
            
            if 'longtext' in current_column[1].lower():
                print("\n[완료] results 컬럼이 이미 LONGTEXT 타입입니다.")
                return
        else:
            print("\n[경고] churn_analyses 테이블이 존재하지 않습니다.")
            print("테이블이 자동으로 생성될 때 LONGTEXT로 생성됩니다.")
            return
        
        # 컬럼 타입 변경
        print("\n[마이그레이션 실행] results 컬럼을 LONGTEXT로 변경 중...")
        cursor.execute("ALTER TABLE churn_analyses MODIFY COLUMN results LONGTEXT NULL")
        conn.commit()
        
        # 변경 확인
        cursor.execute("SHOW COLUMNS FROM churn_analyses LIKE 'results'")
        updated_column = cursor.fetchone()
        
        if updated_column and 'longtext' in updated_column[1].lower():
            print("[완료] results 컬럼이 LONGTEXT로 변경되었습니다.")
            print(f"  새 타입: {updated_column[1]}")
        else:
            print("[경고] 컬럼 타입 변경이 확인되지 않았습니다.")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("마이그레이션 완료!")
        print("=" * 60)
        
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1146:  # Table doesn't exist
            print("\n[정보] churn_analyses 테이블이 아직 존재하지 않습니다.")
            print("분석을 실행하면 테이블이 자동으로 생성되며 LONGTEXT로 생성됩니다.")
        else:
            print(f"\n[오류] 데이터베이스 연결 실패: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"\n[오류] 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migration()

