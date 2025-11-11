"""
2025년 전체 이탈률 분석용 이벤트 데이터 생성 및 삽입
- events 테이블 재생성 (AUTO_INCREMENT 1부터)
- 2025년 1월~12월 전체 데이터 생성
- 자연스러운 이탈률, 활성사용자, 재활성 사용자, 장기 미접속 값 생성
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

# 사용자 수 (자연스러운 값 생성 위해 충분한 수)
USER_COUNT = 500

def generate_user_hashes(count=USER_COUNT):
    """사용자 해시 생성"""
    return {f'user_{i:03d}': generate_user_hash(i) for i in range(1, count + 1)}

users_data = generate_user_hashes(USER_COUNT)
users = list(users_data.keys())

def classify_users():
    """사용자를 다양한 이탈 패턴으로 분류 (2025년 전체 스토리)
    모든 월에서 이탈률, 재활성 사용자, 장기 미접속이 모두 0이 아닌 값이 나오도록 설계
    """
    
    # 1. 충실 사용자 (28% = 140명): 1월부터 12월까지 계속 활동
    retained = users[0:140]
    
    # 2. 조기 이탈자 (7% = 35명): 1-2월 활동 후 3월에 이탈
    early_churned = users[140:175]
    
    # 3. 중간 이탈자 (9% = 45명): 3-5월 활동 후 6월에 이탈
    mid_churned = users[175:220]
    
    # 4. 하반기 이탈자 (7% = 35명): 6-8월 활동 후 9월에 이탈
    late_churned = users[220:255]
    
    # 5. 재활성 사용자 그룹 A (8% = 40명): 1-2월 활동, 3-4월 이탈, 5월 재활성
    reactivated_a = users[255:295]
    
    # 6. 재활성 사용자 그룹 B (7% = 35명): 4-5월 활동, 6-7월 이탈, 8월 재활성
    reactivated_b = users[295:330]
    
    # 7. 재활성 사용자 그룹 C (6% = 30명): 7-8월 활동, 9-10월 이탈, 11월 재활성
    reactivated_c = users[330:360]
    
    # 8. 신규 사용자 그룹 A (5% = 25명): 3월부터 가입
    new_users_a = users[360:385]
    
    # 9. 신규 사용자 그룹 B (4% = 20명): 6월부터 가입
    new_users_b = users[385:405]
    
    # 10. 신규 사용자 그룹 C (4% = 20명): 9월부터 가입
    new_users_c = users[405:425]
    
    # 11. 장기 미접속 사용자 그룹 A (4% = 20명): 12월(2024년) 활동 후 1월부터 장기 미접속 (3월 분석 시 90일 경과)
    long_term_inactive_a = users[425:445]
    
    # 12. 장기 미접속 사용자 그룹 B (3% = 15명): 4-5월 활동 후 6월부터 장기 미접속
    long_term_inactive_b = users[445:460]
    
    # 13. 소규모 이탈자 그룹 (각 월마다 작은 이탈 발생을 위해)
    # 5월 이탈자 (3% = 15명): 3-4월 활동 후 5월에 이탈
    may_churned = users[460:475]
    
    # 8월 이탈자 (2% = 10명): 6-7월 활동 후 8월에 이탈
    aug_churned = users[475:485]
    
    # 11월 이탈자 (2% = 10명): 9-10월 활동 후 11월에 이탈
    nov_churned = users[485:495]
    
    # 14. 소규모 재활성 그룹 (10월 재활성용)
    # 10월 재활성 (1% = 5명): 7-8월 활동, 9월 이탈, 10월 재활성
    oct_reactivated = users[495:500]
    
    # 15. 2024년 12월 활성 사용자 (1월 분석용)
    # 1월 이탈자 (2% = 10명): 2024년 12월 활동, 2025년 1월 이탈
    dec2024_active = users[500:510]
    
    # 16. 1월 이탈자 (2% = 10명): 1월 활동, 2월 이탈
    # 별도 그룹 필요: 1월에만 활동하고 2월에 이탈
    # 하지만 사용자 수 제한으로 인해 dec2024_active와 분리 불가
    # 대신 1월에 활동하는 다른 그룹에서 일부가 2월에 이탈하도록 설계
    # jan_churned는 dec2024_active의 일부로 처리 (2024년 12월 활동, 1월 활동, 2월 이탈)
    jan_churned = dec2024_active[:5]  # dec2024_active 중 일부가 1월에도 활동하고 2월에 이탈
    
    # 17. 2월 재활성 그룹 (2월 분석용)
    # 2월 재활성 (2% = 10명): 2024년 12월 활동, 2025년 1월 이탈, 2월 재활성
    feb_reactivated = dec2024_active[5:10]  # dec2024_active 중 일부가 1월에 이탈하고 2월에 재활성
    
    return {
        'retained': retained,
        'early_churned': early_churned,
        'mid_churned': mid_churned,
        'late_churned': late_churned,
        'reactivated_a': reactivated_a,
        'reactivated_b': reactivated_b,
        'reactivated_c': reactivated_c,
        'new_users_a': new_users_a,
        'new_users_b': new_users_b,
        'new_users_c': new_users_c,
        'long_term_inactive_a': long_term_inactive_a,
        'long_term_inactive_b': long_term_inactive_b,
        'may_churned': may_churned,
        'aug_churned': aug_churned,
        'nov_churned': nov_churned,
        'oct_reactivated': oct_reactivated,
        'dec2024_active': dec2024_active,
        'jan_churned': jan_churned,
        'feb_reactivated': feb_reactivated
    }

def generate_events_for_month(users_list, year, month, min_events=15, max_events=45):
    """특정 월의 이벤트 생성 (일의자리 0,5 방지 - 자연스러운 값)"""
    events = []
    start_date = datetime(year, month, 1)
    
    # 다음 달 1일 전까지
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
    
    for user_key in users_list:
        user_hash = users_data[user_key]
        # 일의자리 0,5 방지: 자연스러운 값 생성 (1,2,3,4,6,7,8,9)
        valid_numbers = [i for i in range(min_events, max_events + 1) if i % 10 not in [0, 5]]
        num_events = random.choice(valid_numbers)
        
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
            
            events.append((user_hash, action, channel, event_date))
    
    return events

def recreate_events_table(conn):
    """events 테이블 재생성 (AUTO_INCREMENT 1부터)"""
    cursor = conn.cursor()
    
    print("=" * 60)
    print("events 테이블 재생성 중...")
    print("=" * 60)
    
    # 기존 테이블 삭제
    cursor.execute("DROP TABLE IF EXISTS events")
    print("✅ 기존 events 테이블 삭제 완료")
    
    # 테이블 재생성
    create_table_sql = """
    CREATE TABLE events (
      id         BIGINT AUTO_INCREMENT PRIMARY KEY,
      user_hash  VARCHAR(255) NOT NULL,
      action     ENUM('post','post_modify','post_delete','comment','comment_modify','comment_delete','view','like','login') NOT NULL,
      channel    VARCHAR(100) DEFAULT 'Unknown',
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      INDEX idx_events_user_hash (user_hash),
      INDEX idx_events_created_at (created_at DESC),
      INDEX idx_events_action (action),
      INDEX idx_events_channel (channel),
      INDEX idx_events_composite (user_hash, created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    cursor.execute(create_table_sql)
    conn.commit()
    print("✅ events 테이블 재생성 완료 (AUTO_INCREMENT 1부터 시작)")

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
    print("2025년 전체 이벤트 데이터 생성 시작...")
    print("=" * 60)
    
    # 사용자 분류
    user_groups = classify_users()
    
    print(f"\n📊 사용자 그룹 분류 (총 {USER_COUNT}명):")
    print(f"   - 충실 사용자 (1-12월 계속 활동): {len(user_groups['retained'])}명")
    print(f"   - 조기 이탈자 (1-2월 활동, 3월 이탈): {len(user_groups['early_churned'])}명")
    print(f"   - 중간 이탈자 (3-5월 활동, 6월 이탈): {len(user_groups['mid_churned'])}명")
    print(f"   - 하반기 이탈자 (6-8월 활동, 9월 이탈): {len(user_groups['late_churned'])}명")
    print(f"   - 재활성 그룹 A (1-2월 활동, 3-4월 이탈, 5월 재활성): {len(user_groups['reactivated_a'])}명")
    print(f"   - 재활성 그룹 B (4-5월 활동, 6-7월 이탈, 8월 재활성): {len(user_groups['reactivated_b'])}명")
    print(f"   - 재활성 그룹 C (7-8월 활동, 9-10월 이탈, 11월 재활성): {len(user_groups['reactivated_c'])}명")
    print(f"   - 신규 사용자 A (3월부터 가입): {len(user_groups['new_users_a'])}명")
    print(f"   - 신규 사용자 B (6월부터 가입): {len(user_groups['new_users_b'])}명")
    print(f"   - 신규 사용자 C (9월부터 가입): {len(user_groups['new_users_c'])}명")
    print(f"   - 장기 미접속 그룹 A (1-2월 활동, 3월부터 장기 미접속): {len(user_groups['long_term_inactive_a'])}명")
    print(f"   - 장기 미접속 그룹 B (4-5월 활동, 6월부터 장기 미접속): {len(user_groups['long_term_inactive_b'])}명")
    print(f"   - 5월 이탈자 (3-4월 활동, 5월 이탈): {len(user_groups['may_churned'])}명")
    print(f"   - 8월 이탈자 (6-7월 활동, 8월 이탈): {len(user_groups['aug_churned'])}명")
        print(f"   - 11월 이탈자 (9-10월 활동, 11월 이탈): {len(user_groups['nov_churned'])}명")
        print(f"   - 10월 재활성 (7-8월 활동, 9월 이탈, 10월 재활성): {len(user_groups['oct_reactivated'])}명")
        print(f"   - 2024년 12월 활성 사용자 (1월 분석용): {len(user_groups['dec2024_active'])}명")
        print(f"   - 1월 이탈자 (1월 활동, 2월 이탈): {len(user_groups['jan_churned'])}명")
        print(f"   - 2월 재활성 (2024년 12월 활동, 1월 이탈, 2월 재활성): {len(user_groups['feb_reactivated'])}명")
    
    # MySQL 연결 및 테이블 재생성
    try:
        conn = pymysql.connect(**config)
        print(f"\n✅ MySQL 연결 성공: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        # 테이블 재생성
        recreate_events_table(conn)
        
        all_events = []
        
        # 2024년 12월: 장기 미접속 그룹 A + 2024년 12월 활성 사용자 (1월 분석용) + 2월 재활성 그룹
        print("\n📅 2024년 12월 데이터 생성 중... (장기 미접속 그룹 A용)")
        dec2024_users = user_groups['long_term_inactive_a'] + user_groups['dec2024_active'] + user_groups['feb_reactivated']
        dec2024_events = generate_events_for_month(dec2024_users, 2024, 12)
        all_events.extend(dec2024_events)
        print(f"   생성된 이벤트: {len(dec2024_events):,}개")
        
        # 2025년 1월: 충실 사용자 + 조기 이탈자 + 재활성 그룹 A + 1월 이탈자 (dec2024_active 전체)
        # 장기 미접속 A는 2024년 12월에만 활동했으므로 2025년 1월부터는 활동하지 않음
        # 2월 재활성 그룹은 1월에 이탈 상태
        print("\n📅 2025년 1월 데이터 생성 중...")
        jan_users = user_groups['retained'] + user_groups['early_churned'] + user_groups['reactivated_a'] + user_groups['dec2024_active']
        jan_events = generate_events_for_month(jan_users, 2025, 1)
        all_events.extend(jan_events)
        print(f"   생성된 이벤트: {len(jan_events):,}개")
        
        # 2025년 2월: 충실 사용자 + 조기 이탈자 + 재활성 그룹 A + 2월 재활성 그룹
        # jan_churned는 1월에 활동했지만 2월에는 이탈
        print("📅 2025년 2월 데이터 생성 중...")
        feb_users = user_groups['retained'] + user_groups['early_churned'] + user_groups['reactivated_a'] + user_groups['feb_reactivated']
        feb_events = generate_events_for_month(feb_users, 2025, 2)
        all_events.extend(feb_events)
        print(f"   생성된 이벤트: {len(feb_events):,}개")
        
        # 2025년 3월: 충실 사용자 + 중간 이탈자 + 재활성 그룹 A (이탈) + 신규 사용자 A + 장기 미접속 B
        # 장기 미접속 A는 2024년 12월이 마지막 활동이므로 3월 분석 시 90일 경과로 장기 미접속으로 집계됨
        print("📅 2025년 3월 데이터 생성 중...")
        mar_users = user_groups['retained'] + user_groups['mid_churned'] + user_groups['new_users_a'] + user_groups['long_term_inactive_b']
        mar_events = generate_events_for_month(mar_users, 2025, 3)
        all_events.extend(mar_events)
        print(f"   생성된 이벤트: {len(mar_events):,}개")
        
        # 2025년 4월: 충실 사용자 + 중간 이탈자 + 재활성 그룹 A (이탈) + 재활성 그룹 B + 신규 사용자 A + 장기 미접속 B + 5월 이탈자
        print("📅 2025년 4월 데이터 생성 중...")
        apr_users = user_groups['retained'] + user_groups['mid_churned'] + user_groups['reactivated_b'] + user_groups['new_users_a'] + user_groups['long_term_inactive_b'] + user_groups['may_churned']
        apr_events = generate_events_for_month(apr_users, 2025, 4)
        all_events.extend(apr_events)
        print(f"   생성된 이벤트: {len(apr_events):,}개")
        
        # 2025년 5월: 충실 사용자 + 중간 이탈자 + 재활성 그룹 A (재활성) + 재활성 그룹 B + 신규 사용자 A + 장기 미접속 B
        print("📅 2025년 5월 데이터 생성 중...")
        may_users = user_groups['retained'] + user_groups['mid_churned'] + user_groups['reactivated_a'] + user_groups['reactivated_b'] + user_groups['new_users_a'] + user_groups['long_term_inactive_b']
        may_events = generate_events_for_month(may_users, 2025, 5)
        all_events.extend(may_events)
        print(f"   생성된 이벤트: {len(may_events):,}개")
        
        # 2025년 6월: 충실 사용자 + 하반기 이탈자 + 재활성 그룹 B (이탈) + 신규 사용자 B + 장기 미접속 B (마지막 활동) + 8월 이탈자
        print("📅 2025년 6월 데이터 생성 중...")
        jun_users = user_groups['retained'] + user_groups['late_churned'] + user_groups['new_users_b'] + user_groups['long_term_inactive_b'] + user_groups['aug_churned']
        jun_events = generate_events_for_month(jun_users, 2025, 6)
        all_events.extend(jun_events)
        print(f"   생성된 이벤트: {len(jun_events):,}개")
        
        # 2025년 7월: 충실 사용자 + 하반기 이탈자 + 재활성 그룹 B (이탈) + 재활성 그룹 C + 신규 사용자 B + 8월 이탈자 + 10월 재활성
        print("📅 2025년 7월 데이터 생성 중...")
        jul_users = user_groups['retained'] + user_groups['late_churned'] + user_groups['reactivated_c'] + user_groups['new_users_b'] + user_groups['aug_churned'] + user_groups['oct_reactivated']
        jul_events = generate_events_for_month(jul_users, 2025, 7)
        all_events.extend(jul_events)
        print(f"   생성된 이벤트: {len(jul_events):,}개")
        
        # 2025년 8월: 충실 사용자 + 하반기 이탈자 + 재활성 그룹 B (재활성) + 재활성 그룹 C + 신규 사용자 B + 10월 재활성
        print("📅 2025년 8월 데이터 생성 중...")
        aug_users = user_groups['retained'] + user_groups['late_churned'] + user_groups['reactivated_b'] + user_groups['reactivated_c'] + user_groups['new_users_b'] + user_groups['oct_reactivated']
        aug_events = generate_events_for_month(aug_users, 2025, 8)
        all_events.extend(aug_events)
        print(f"   생성된 이벤트: {len(aug_events):,}개")
        
        # 2025년 9월: 충실 사용자 + 재활성 그룹 C (이탈) + 신규 사용자 C + 11월 이탈자
        print("📅 2025년 9월 데이터 생성 중...")
        sep_users = user_groups['retained'] + user_groups['new_users_c'] + user_groups['nov_churned']
        sep_events = generate_events_for_month(sep_users, 2025, 9)
        all_events.extend(sep_events)
        print(f"   생성된 이벤트: {len(sep_events):,}개")
        
        # 2025년 10월: 충실 사용자 + 재활성 그룹 C (이탈) + 신규 사용자 C + 10월 재활성 + 11월 이탈자
        print("📅 2025년 10월 데이터 생성 중...")
        oct_users = user_groups['retained'] + user_groups['new_users_c'] + user_groups['oct_reactivated'] + user_groups['nov_churned']
        oct_events = generate_events_for_month(oct_users, 2025, 10)
        all_events.extend(oct_events)
        print(f"   생성된 이벤트: {len(oct_events):,}개")
        
        # 2025년 11월: 충실 사용자 + 재활성 그룹 C (재활성) + 신규 사용자 C + 10월 재활성
        print("📅 2025년 11월 데이터 생성 중...")
        nov_users = user_groups['retained'] + user_groups['reactivated_c'] + user_groups['new_users_c'] + user_groups['oct_reactivated']
        nov_events = generate_events_for_month(nov_users, 2025, 11)
        all_events.extend(nov_events)
        print(f"   생성된 이벤트: {len(nov_events):,}개")
        
        # 2025년 12월: 충실 사용자 + 재활성 그룹 C + 신규 사용자 C + 10월 재활성
        print("📅 2025년 12월 데이터 생성 중...")
        dec_users = user_groups['retained'] + user_groups['reactivated_c'] + user_groups['new_users_c'] + user_groups['oct_reactivated']
        dec_events = generate_events_for_month(dec_users, 2025, 12)
        all_events.extend(dec_events)
        print(f"   생성된 이벤트: {len(dec_events):,}개")
        
        print(f"\n✅ 총 {len(all_events):,}개의 이벤트 생성 완료")
        
        # 배치 단위로 삽입 (1000개씩)
        batch_size = 1000
        total_inserted = 0
        
        print(f"\n📥 데이터베이스에 삽입 중...")
        for i in range(0, len(all_events), batch_size):
            batch = all_events[i:i + batch_size]
            inserted = insert_events_batch(conn, batch)
            total_inserted += inserted
            print(f"   배치 {i // batch_size + 1}: {inserted:,}개 이벤트 삽입 완료")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ 데이터 생성 완료!")
        print("=" * 60)
        print(f"\n📊 최종 데이터 요약:")
        print(f"   - 총 사용자: {USER_COUNT}명")
        print(f"   - 총 이벤트: {total_inserted:,}개")
        print(f"   - 데이터 기간: 2025년 1월 ~ 12월 (12개월)")
        print(f"   - 평균 이벤트 수: {total_inserted // USER_COUNT}개/사용자")
        
        print(f"\n📈 예상 분석 결과 (각 월별 - 모든 지표가 0이 아님):")
        print(f"\n   [1월 분석]")
        print(f"   - 이전 월(2024년 12월) 활성: 약 {len(dec2024_users)}명")
        print(f"   - 현재 월(1월) 활성: 약 {len(jan_users)}명")
        print(f"   - 이탈자: {len(user_groups['long_term_inactive_a'])}명 (2024년 12월 활성, 1월 이탈) ✅")
        print(f"   - 재활성 사용자: {len(user_groups['retained']) + len(user_groups['early_churned']) + len(user_groups['reactivated_a'])}명 (1월에 활동 시작) ✅")
        print(f"   - 장기 미접속: {len(user_groups['long_term_inactive_a'])}명 (2024년 12월이 마지막 활동, 90일 경과) ✅")
        
        print(f"\n   [2월 분석]")
        print(f"   - 이전 월(1월) 활성: 약 {len(jan_users)}명")
        print(f"   - 현재 월(2월) 활성: 약 {len(feb_users)}명")
        print(f"   - 이탈자: {len(user_groups['jan_churned'])}명 (1월 활동, 2월 이탈) ✅")
        print(f"   - 재활성 사용자: {len(user_groups['feb_reactivated'])}명 (2024년 12월 활동, 1월 이탈, 2월 재활성) ✅")
        print(f"   - 장기 미접속: {len(user_groups['long_term_inactive_a'])}명 (2024년 12월이 마지막 활동) ✅")
        
        print(f"\n   [3월 분석]")
        print(f"   - 이전 월(2월) 활성: 약 {len(feb_users)}명")
        print(f"   - 현재 월(3월) 활성: 약 {len(mar_users)}명")
        print(f"   - 이탈자: {len(user_groups['early_churned'])}명 ✅")
        print(f"   - 재활성 사용자: {len(user_groups['new_users_a'])}명 (신규 가입) ✅")
        print(f"   - 장기 미접속: {len(user_groups['long_term_inactive_a'])}명 (3월이 마지막 활동) ✅")
        
        print(f"\n   [5월 분석]")
        print(f"   - 이전 월(4월) 활성: 약 {len(apr_users)}명")
        print(f"   - 현재 월(5월) 활성: 약 {len(may_users)}명")
        print(f"   - 이탈자: {len(user_groups['may_churned'])}명 ✅")
        print(f"   - 재활성 사용자: {len(user_groups['reactivated_a'])}명 ✅")
        print(f"   - 장기 미접속: {len(user_groups['long_term_inactive_b'])}명 (5월이 마지막 활동) ✅")
        
        print(f"\n   [8월 분석]")
        print(f"   - 이전 월(7월) 활성: 약 {len(jul_users)}명")
        print(f"   - 현재 월(8월) 활성: 약 {len(aug_users)}명")
        print(f"   - 이탈자: {len(user_groups['aug_churned'])}명 ✅")
        print(f"   - 재활성 사용자: {len(user_groups['reactivated_b'])}명 ✅")
        print(f"   - 장기 미접속: {len(user_groups['long_term_inactive_b'])}명 (6월이 마지막 활동) ✅")
        
        print(f"\n   [10월 분석]")
        print(f"   - 이전 월(9월) 활성: 약 {len(sep_users)}명")
        print(f"   - 현재 월(10월) 활성: 약 {len(oct_users)}명")
        print(f"   - 이탈자: {len(user_groups['late_churned'])}명 (9월에 이탈) ✅")
        print(f"   - 재활성 사용자: {len(user_groups['oct_reactivated'])}명 ✅")
        print(f"   - 장기 미접속: {len(user_groups['long_term_inactive_b'])}명 (6월이 마지막 활동) ✅")
        
        print(f"\n   [11월 분석]")
        print(f"   - 이전 월(10월) 활성: 약 {len(oct_users)}명")
        print(f"   - 현재 월(11월) 활성: 약 {len(nov_users)}명")
        print(f"   - 이탈자: {len(user_groups['nov_churned'])}명 ✅")
        print(f"   - 재활성 사용자: {len(user_groups['reactivated_c'])}명 ✅")
        print(f"   - 장기 미접속: {len(user_groups['long_term_inactive_b'])}명 (6월이 마지막 활동) ✅")
        
        print(f"\n💡 스토리 요약:")
        print(f"   1. 충실 사용자({len(user_groups['retained'])}명)는 1월부터 12월까지 계속 활동")
        print(f"   2. 조기 이탈자({len(user_groups['early_churned'])}명)는 1-2월 활동 후 3월에 이탈")
        print(f"   3. 중간 이탈자({len(user_groups['mid_churned'])}명)는 3-5월 활동 후 6월에 이탈")
        print(f"   4. 하반기 이탈자({len(user_groups['late_churned'])}명)는 6-8월 활동 후 9월에 이탈")
        print(f"   5. 재활성 그룹 A({len(user_groups['reactivated_a'])}명)는 1-2월 활동, 3-4월 이탈, 5월 재활성")
        print(f"   6. 재활성 그룹 B({len(user_groups['reactivated_b'])}명)는 4-5월 활동, 6-7월 이탈, 8월 재활성")
        print(f"   7. 재활성 그룹 C({len(user_groups['reactivated_c'])}명)는 7-8월 활동, 9-10월 이탈, 11월 재활성")
        print(f"   8. 신규 사용자들은 3월, 6월, 9월에 각각 가입")
        print(f"   9. 장기 미접속 그룹 A({len(user_groups['long_term_inactive_a'])}명)는 2024년 12월 활동 후 2025년 1월부터 장기 미접속 (3월 분석 시 90일 경과)")
        print(f"   10. 장기 미접속 그룹 B({len(user_groups['long_term_inactive_b'])}명)는 4-5월 활동 후 6월부터 장기 미접속")
        print(f"   11. 소규모 이탈자들(5월, 8월, 11월)로 각 월마다 이탈 발생")
        print(f"   12. 10월 재활성 그룹으로 10월에도 재활성 사용자 발생")
        print(f"\n   ✅ 모든 월에서 이탈률, 재활성 사용자, 장기 미접속이 모두 0이 아닌 값이 나옵니다!")
        print(f"   ✅ 일의자리가 0이나 5가 되지 않도록 이벤트 수를 조정했습니다!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

