"""
이탈률 분석용 더미 이벤트 데이터 생성 및 삽입
"""
import random
from datetime import datetime, timedelta
import pymysql
import os
from dotenv import load_dotenv
from user_hash_utils import generate_user_hash

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

# 액션 및 채널 정의
ACTIONS = ['post', 'post_modify', 'post_delete', 'comment', 'comment_modify', 'comment_delete', 'view', 'like', 'login']
CHANNELS = ['web', 'app', 'Unknown']

# 사용자 생성 (300명) - user_id 기반으로 해시 생성
# 더미 user_id 1~300을 사용하여 일관된 해시 생성
# 충분한 데이터로 이탈 분석의 정확도를 높이기 위해 사용자 수 증가
USER_COUNT = 300
def generate_user_hashes(count=USER_COUNT):
    """사용자 해시 생성"""
    return {f'user_{i:03d}': generate_user_hash(i) for i in range(1, count + 1)}

users_data = generate_user_hashes(USER_COUNT)
users = list(users_data.keys())  # 원래 키 ('user_001', ...) - 그룹 분류용

# 이탈률 분석을 위한 사용자 그룹 분류
# 다양한 이탈 패턴을 만들어 실제 분석 시나리오를 반영
def classify_users():
    """사용자를 다양한 이탈 패턴으로 분류"""
    # 조기 이탈자: 6-7월에만 활동하고 8월에 이탈 (20%)
    early_churned = users[:60]
    
    # 중간 이탈자: 7-9월에 활동하고 10월에 이탈 (15%)
    mid_churned = users[60:105]
    
    # 최근 이탈자: 9-11월에 활동하고 12월에 이탈 (10%)
    recent_churned = users[105:135]
    
    # 일시 재활성: 8월에 이탈했다가 11월에 재활성 (10%)
    reactivated = users[135:165]
    
    # 충실 사용자: 계속 활동 (35%)
    retained = users[165:270]
    
    # 신규 사용자: 11-12월에만 가입한 사용자 (10%)
    new_users = users[270:300]
    
    return {
        'early_churned': early_churned,
        'mid_churned': mid_churned,
        'recent_churned': recent_churned,
        'reactivated': reactivated,
        'retained': retained,
        'new_users': new_users
    }

def generate_events_for_month(users_list, year, month, min_events=20, max_events=50):
    """특정 월의 이벤트 생성"""
    events = []
    start_date = datetime(year, month, 1)
    
    # 다음 달 1일 전까지
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
    
    for user_key in users_list:
        user_hash = users_data[user_key]  # 실제 해시값 사용 (같은 user_key는 같은 해시)
        num_events = random.randint(min_events, max_events)
        for _ in range(num_events):
            # 랜덤 날짜/시간 생성
            days_offset = random.randint(0, (end_date - start_date).days)
            hours_offset = random.randint(0, 23)
            minutes_offset = random.randint(0, 59)
            
            event_date = start_date + timedelta(
                days=days_offset,
                hours=hours_offset,
                minutes=minutes_offset
            )
            
            # 랜덤 액션 및 채널
            action = random.choice(ACTIONS)
            channel = random.choice(CHANNELS)
            
            events.append((user_hash, action, channel, event_date))  # 해시값 사용
    
    return events

def insert_events_batch(conn, events_batch):
    """이벤트 배치 삽입"""
    cursor = conn.cursor()
    
    sql = """
    INSERT INTO events (user_hash, action, channel, created_at)
    VALUES (%s, %s, %s, %s)
    """
    
    cursor.executemany(sql, events_batch)
    conn.commit()
    
    return cursor.rowcount

def main():
    print("=" * 60)
    print("더미 이벤트 데이터 생성 시작...")
    print("=" * 60)
    
    # 사용자 분류
    user_groups = classify_users()
    
    print(f"\n📊 사용자 그룹 분류:")
    print(f"   - 조기 이탈자 (6-7월 활동, 8월 이탈): {len(user_groups['early_churned'])}명")
    print(f"   - 중간 이탈자 (7-9월 활동, 10월 이탈): {len(user_groups['mid_churned'])}명")
    print(f"   - 최근 이탈자 (9-11월 활동, 12월 이탈): {len(user_groups['recent_churned'])}명")
    print(f"   - 재활성 사용자 (8월 이탈, 11월 재활성): {len(user_groups['reactivated'])}명")
    print(f"   - 충실 사용자 (계속 활동): {len(user_groups['retained'])}명")
    print(f"   - 신규 사용자 (11-12월 가입): {len(user_groups['new_users'])}명")
    print(f"   - 총 사용자: {USER_COUNT}명\n")
    
    all_events = []
    
    # 2024년 6월 데이터 (초기 사용자들)
    print("2024년 6월 데이터 생성 중...")
    june_users = user_groups['early_churned'] + user_groups['mid_churned'] + user_groups['retained']
    june_events = generate_events_for_month(june_users, 2024, 6, 20, 50)
    all_events.extend(june_events)
    
    # 2024년 7월 데이터
    print("2024년 7월 데이터 생성 중...")
    july_users = user_groups['early_churned'] + user_groups['mid_churned'] + user_groups['retained'] + user_groups['reactivated']
    july_events = generate_events_for_month(july_users, 2024, 7, 20, 50)
    all_events.extend(july_events)
    
    # 2024년 8월 데이터 (조기 이탈자 제외)
    print("2024년 8월 데이터 생성 중...")
    aug_users = user_groups['mid_churned'] + user_groups['retained'] + user_groups['reactivated']
    aug_events = generate_events_for_month(aug_users, 2024, 8, 20, 50)
    all_events.extend(aug_events)
    
    # 2024년 9월 데이터
    print("2024년 9월 데이터 생성 중...")
    sep_users = user_groups['mid_churned'] + user_groups['recent_churned'] + user_groups['retained']
    sep_events = generate_events_for_month(sep_users, 2024, 9, 20, 50)
    all_events.extend(sep_events)
    
    # 2024년 10월 데이터 (중간 이탈자 제외)
    print("2024년 10월 데이터 생성 중...")
    oct_users = user_groups['recent_churned'] + user_groups['retained']
    oct_events = generate_events_for_month(oct_users, 2024, 10, 20, 50)
    all_events.extend(oct_events)
    
    # 2024년 11월 데이터 (재활성 사용자 포함, 최근 이탈자 포함)
    print("2024년 11월 데이터 생성 중...")
    nov_users = user_groups['recent_churned'] + user_groups['reactivated'] + user_groups['retained'] + user_groups['new_users']
    nov_events = generate_events_for_month(nov_users, 2024, 11, 20, 50)
    all_events.extend(nov_events)
    
    # 2024년 12월 데이터 (최근 이탈자 제외, 재활성 + 충실 + 신규만)
    print("2024년 12월 데이터 생성 중...")
    dec_users = user_groups['reactivated'] + user_groups['retained'] + user_groups['new_users']
    dec_events = generate_events_for_month(dec_users, 2024, 12, 20, 50)
    all_events.extend(dec_events)
    
    print(f"\n✅ 총 {len(all_events):,}개의 이벤트 생성 완료")
    
    # MySQL 연결 및 삽입
    try:
        conn = pymysql.connect(**config)
        print(f"MySQL 연결 성공: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        # 배치 단위로 삽입 (1000개씩)
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(all_events), batch_size):
            batch = all_events[i:i + batch_size]
            inserted = insert_events_batch(conn, batch)
            total_inserted += inserted
            print(f"배치 {i // batch_size + 1}: {inserted}개 이벤트 삽입 완료")
        
        conn.close()
        print(f"\n✅ 총 {total_inserted:,}개의 더미 이벤트 데이터 삽입 완료!")
        print(f"\n📊 최종 데이터 요약:")
        print(f"   - 총 사용자: {USER_COUNT}명")
        print(f"   - 조기 이탈자: {len(user_groups['early_churned'])}명")
        print(f"   - 중간 이탈자: {len(user_groups['mid_churned'])}명")
        print(f"   - 최근 이탈자: {len(user_groups['recent_churned'])}명")
        print(f"   - 재활성 사용자: {len(user_groups['reactivated'])}명")
        print(f"   - 충실 사용자: {len(user_groups['retained'])}명")
        print(f"   - 신규 사용자: {len(user_groups['new_users'])}명")
        print(f"   - 데이터 기간: 2024년 6월 ~ 12월 (7개월)")
        print(f"   - 평균 이벤트 수: {total_inserted // USER_COUNT}개/사용자")
        print("\n💡 모든 user_hash는 실제 SHA-256 해시값으로 생성되었습니다.")
        print("   같은 user_id는 항상 같은 해시값을 가집니다 (일관성 보장).")
        print("\n📈 이탈 분석 권장 기간:")
        print("   - 전체 분석: 2024-06 ~ 2024-12")
        print("   - 최근 분석: 2024-10 ~ 2024-12")
        print("   - 트렌드 분석: 2024-06 ~ 2024-12 (월별 비교)")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

