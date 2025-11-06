"""
events 테이블 데이터 확인 스크립트
"""
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 로드
load_dotenv()

# MySQL 연결 설정 (generate_dummy_events.py와 동일한 설정)
config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'wmai'),
    'password': os.getenv('DB_PASSWORD', '1234'),
    'database': os.getenv('DB_NAME', 'wmai_db'),
    'charset': 'utf8mb4'
}

def check_events_data():
    """events 테이블 데이터 확인"""
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        print("=" * 60)
        print(f"MySQL 연결 정보:")
        print(f"   호스트: {config['host']}:{config['port']}")
        print(f"   데이터베이스: {config['database']}")
        print(f"   사용자: {config['user']}")
        print("=" * 60)
        
        # 1. 전체 이벤트 수
        cursor.execute("SELECT COUNT(*) as total FROM events")
        total = cursor.fetchone()['total']
        print(f"\n[전체 통계]")
        print(f"   총 이벤트 수: {total:,}개")
        
        if total == 0:
            print("\n[경고] events 테이블에 데이터가 없습니다!")
            print("   generate_dummy_events.py를 실행해주세요.")
            conn.close()
            return
        
        # 2. 고유 사용자 수
        cursor.execute("SELECT COUNT(DISTINCT user_hash) as unique_users FROM events")
        unique_users = cursor.fetchone()['unique_users']
        print(f"   고유 사용자 수: {unique_users:,}명")
        
        # 3. 월별 데이터 분포
        print(f"\n[월별 데이터 분포]")
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%Y-%m') as month,
                COUNT(*) as event_count,
                COUNT(DISTINCT user_hash) as user_count
            FROM events
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month
        """)
        monthly_data = cursor.fetchall()
        for row in monthly_data:
            print(f"   {row['month']}: {row['event_count']:,}개 이벤트, {row['user_count']}명 사용자")
        
        # 4. 액션별 통계
        print(f"\n[액션별 통계]")
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM events
            GROUP BY action
            ORDER BY count DESC
        """)
        actions = cursor.fetchall()
        for row in actions:
            print(f"   {row['action']}: {row['count']:,}개")
        
        # 5. 채널별 통계
        print(f"\n[채널별 통계]")
        cursor.execute("""
            SELECT channel, COUNT(*) as count
            FROM events
            GROUP BY channel
            ORDER BY count DESC
        """)
        channels = cursor.fetchall()
        for row in channels:
            print(f"   {row['channel']}: {row['count']:,}개")
        
        # 6. 최신 이벤트 날짜
        cursor.execute("SELECT MAX(created_at) as latest, MIN(created_at) as earliest FROM events")
        date_range = cursor.fetchone()
        print(f"\n[데이터 기간]")
        print(f"   최초: {date_range['earliest']}")
        print(f"   최신: {date_range['latest']}")
        
        # 7. 샘플 데이터 (최근 5개)
        print(f"\n[최근 이벤트 샘플 (5개)]")
        cursor.execute("""
            SELECT user_hash, action, channel, created_at
            FROM events
            ORDER BY created_at DESC
            LIMIT 5
        """)
        samples = cursor.fetchall()
        for i, row in enumerate(samples, 1):
            print(f"   {i}. user_hash={row['user_hash'][:16]}... action={row['action']} channel={row['channel']} at={row['created_at']}")
        
        conn.close()
        print("\n[완료] 데이터 확인 완료!")
        
    except Exception as e:
        print(f"[오류] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_events_data()

