"""
events 테이블의 모든 데이터 확인 (제한 없음)
"""
import pymysql
import os
from dotenv import load_dotenv

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

def check_all_events():
    """모든 이벤트 데이터 확인"""
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        print("=" * 60)
        print(f"MySQL: {config['database']} 데이터베이스의 events 테이블")
        print("=" * 60)
        
        # 전체 개수 확인
        cursor.execute("SELECT COUNT(*) as total FROM events")
        total = cursor.fetchone()['total']
        print(f"\n[전체 이벤트 수] {total:,}개\n")
        
        if total == 0:
            print("[경고] 데이터가 없습니다!")
            conn.close()
            return
        
        # 실제로 모든 데이터가 해시값인지 확인
        print("[해시값 확인]")
        cursor.execute("""
            SELECT 
                user_hash,
                LENGTH(user_hash) as hash_length,
                COUNT(*) as event_count
            FROM events
            GROUP BY user_hash
            ORDER BY event_count DESC
            LIMIT 10
        """)
        
        print("\n[상위 10명 사용자 해시 샘플]")
        users = cursor.fetchall()
        for i, user in enumerate(users, 1):
            hash_len = user['hash_length']
            is_valid_hash = hash_len == 64  # SHA-256은 64자
            status = "OK (SHA-256)" if is_valid_hash else f"경고: {hash_len}자"
            print(f"   {i}. {user['user_hash'][:16]}... ({len(user['user_hash'])}자) - {user['event_count']}개 이벤트 [{status}]")
        
        # 월별 상세 확인
        print("\n[월별 상세 통계]")
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%Y-%m') as month,
                COUNT(*) as total_events,
                COUNT(DISTINCT user_hash) as unique_users,
                MIN(created_at) as first_event,
                MAX(created_at) as last_event
            FROM events
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month
        """)
        
        monthly = cursor.fetchall()
        for row in monthly:
            print(f"\n   {row['month']}:")
            print(f"      - 총 이벤트: {row['total_events']:,}개")
            print(f"      - 고유 사용자: {row['unique_users']}명")
            print(f"      - 기간: {row['first_event']} ~ {row['last_event']}")
        
        # 해시값 형식 검증
        print("\n[해시값 형식 검증]")
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN LENGTH(user_hash) = 64 THEN 'SHA-256 (64자)'
                    WHEN LENGTH(user_hash) < 64 THEN '짧은 해시'
                    ELSE '긴 해시'
                END as hash_type,
                COUNT(*) as count
            FROM events
            GROUP BY hash_type
        """)
        
        hash_types = cursor.fetchall()
        for row in hash_types:
            print(f"   {row['hash_type']}: {row['count']:,}개")
        
        # 샘플 데이터 (최근 10개)
        print("\n[최근 이벤트 샘플 (10개)]")
        cursor.execute("""
            SELECT 
                id,
                LEFT(user_hash, 20) as user_hash_preview,
                action,
                channel,
                created_at
            FROM events
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        for i, row in enumerate(samples, 1):
            print(f"   {i}. ID={row['id']}, hash={row['user_hash_preview']}..., action={row['action']}, channel={row['channel']}, at={row['created_at']}")
        
        conn.close()
        print("\n[완료] 모든 데이터 확인 완료!")
        print(f"\n[참고] MySQL 클라이언트에서 모든 데이터를 보려면:")
        print("   SELECT * FROM events LIMIT 10000;  -- 제한을 높여서")
        print("   또는")
        print("   SELECT COUNT(*) FROM events;  -- 전체 개수만 확인")
        
    except Exception as e:
        print(f"[오류] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_events()

