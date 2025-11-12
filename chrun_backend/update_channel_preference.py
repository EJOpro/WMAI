"""
기존 이벤트 데이터의 채널 정보만 사용자 선호도에 맞게 업데이트
- 기존 이벤트 유지 (id, 날짜, 액션 등)
- 채널만 사용자별 선호도에 따라 재할당
- 40% 웹 선호, 40% 앱 선호, 20% 혼합 사용
"""
import random
import pymysql
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'wmai'),
    'password': os.getenv('DB_PASSWORD', '1234'),
    'database': os.getenv('DB_NAME', 'wmai_db'),
    'charset': 'utf8mb4'
}

def get_user_channel_preference(user_hash):
    """사용자별 채널 선호도 결정 (해시 기반으로 일관성 유지)"""
    # 사용자 해시를 기반으로 숫자 생성
    hash_int = int(hashlib.md5(user_hash.encode()).hexdigest()[:8], 16)
    
    # 60% 웹 선호, 20% 앱 선호, 20% 혼합 사용 (전체 웹 비율 ~63.4%)
    preference_type = hash_int % 10
    
    if preference_type < 6:  # 0-5: 웹 선호 (60%)
        return {'web': 0.81, 'app': 0.16, 'Unknown': 0.03}
    elif preference_type < 8:  # 6-7: 앱 선호 (20%)
        return {'web': 0.27, 'app': 0.68, 'Unknown': 0.05}
    else:  # 8-9: 혼합 사용 (20%)
        return {'web': 0.52, 'app': 0.43, 'Unknown': 0.05}

def main():
    print("=" * 70)
    print("이벤트 채널 선호도 기반 업데이트 시작")
    print("=" * 70)
    
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    try:
        # 기존 채널 분포 확인
        print("\n[업데이트 전] 채널 분포:")
        cursor.execute("""
            SELECT channel, COUNT(*) as count 
            FROM events 
            GROUP BY channel 
            ORDER BY count DESC
        """)
        before_results = cursor.fetchall()
        total_events = sum(count for _, count in before_results)
        
        for channel, count in before_results:
            print(f"  {channel}: {count:,}개 ({count/total_events*100:.1f}%)")
        
        # 모든 이벤트 조회
        print(f"\n총 {total_events:,}개 이벤트 채널 업데이트 중...")
        cursor.execute("SELECT id, user_hash FROM events ORDER BY id")
        events = cursor.fetchall()
        
        # 배치 업데이트
        batch_size = 1000
        total_updated = 0
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i+batch_size]
            updates = []
            
            for event_id, user_hash in batch:
                # 사용자 선호도에 따라 채널 선택
                channel_pref = get_user_channel_preference(user_hash)
                channels = list(channel_pref.keys())
                weights = list(channel_pref.values())
                new_channel = random.choices(channels, weights=weights)[0]
                updates.append((new_channel, event_id))
            
            # 배치 업데이트 실행
            cursor.executemany(
                "UPDATE events SET channel = %s WHERE id = %s",
                updates
            )
            conn.commit()
            
            total_updated += len(updates)
            progress = total_updated / len(events) * 100
            print(f"  진행: {total_updated:,}/{len(events):,} ({progress:.1f}%)", end='\r')
        
        print(f"\n\n[완료] {total_updated:,}개 이벤트 채널 업데이트")
        
        # 업데이트 후 채널 분포 확인
        print("\n[업데이트 후] 채널 분포:")
        cursor.execute("""
            SELECT channel, COUNT(*) as count 
            FROM events 
            GROUP BY channel 
            ORDER BY count DESC
        """)
        after_results = cursor.fetchall()
        
        for channel, count in after_results:
            print(f"  {channel}: {count:,}개 ({count/total_events*100:.1f}%)")
        
        # 사용자별 주요 채널 확인 (샘플)
        print("\n[사용자별 채널 선호도 확인] (샘플 10명)")
        cursor.execute("""
            SELECT 
                user_hash,
                SUM(CASE WHEN channel = 'web' THEN 1 ELSE 0 END) as web_count,
                SUM(CASE WHEN channel = 'app' THEN 1 ELSE 0 END) as app_count,
                SUM(CASE WHEN channel = 'Unknown' THEN 1 ELSE 0 END) as unknown_count,
                COUNT(*) as total_count
            FROM events
            GROUP BY user_hash
            LIMIT 10
        """)
        sample_users = cursor.fetchall()
        
        for user_hash, web, app, unknown, total in sample_users:
            print(f"  {user_hash[:16]}...: web={web}({web/total*100:.0f}%), app={app}({app/total*100:.0f}%), unknown={unknown}({unknown/total*100:.0f}%)")
        
        print("\n" + "=" * 70)
        print("채널 업데이트 완료!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[오류] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()

