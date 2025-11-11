"""
2025년 전체 자연스러운 이탈률 분석용 이벤트 데이터 생성
- events 테이블 재생성 (AUTO_INCREMENT 1부터)
- 2025년 1월~12월 전체 데이터 생성
- 모든 월에서 이탈률, 활성사용자, 재활성 사용자, 장기 미접속이 모두 0이 아닌 자연스러운 값 생성
- 일의자리가 0이나 5가 되지 않도록 조정
- 채널별 선호도를 사용자별로 차별화하여 의미 있는 세그먼트 분석 가능
"""
import random
from datetime import datetime, timedelta
import pymysql
import os
import hashlib
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

# 액션 및 채널 정의 (요구사항에 맞게 수정)
ACTIONS = ['login', 'post', 'post_delete', 'post_modify', 'comment', 'comment_modify', 'comment_delete', 'view', 'like']
CHANNELS = ['web', 'app', 'Unknown']

# 사용자 수 (자연스러운 값 생성을 위해 충분한 수)
USER_COUNT = 600

def generate_user_hashes(count=USER_COUNT):
    """사용자 해시 생성"""
    return {f'user_{i:04d}': generate_user_hash(i) for i in range(1, count + 1)}

users_data = generate_user_hashes(USER_COUNT)
users = list(users_data.keys())

def get_natural_number(min_val, max_val):
    """일의자리가 0이나 5가 아닌 자연스러운 숫자 생성"""
    while True:
        num = random.randint(min_val, max_val)
        if num % 10 not in [0, 5]:
            return num

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

def classify_users():
    """사용자를 다양한 이탈 패턴으로 분류 (2025년 전체 스토리)
    모든 월에서 이탈률, 재활성 사용자, 장기 미접속이 모두 0이 아닌 자연스러운 값이 나오도록 설계
    """
    
    # 1. 충실 사용자 (30% = 180명): 1월부터 12월까지 계속 활동
    retained = users[0:180]
    
    # 2. 1월 이탈자 (4% = 24명): 2024년 12월 활동, 2025년 1월 이탈
    jan_churned = users[180:204]
    
    # 3. 2월 이탈자 (3% = 18명): 1월 활동, 2월 이탈
    feb_churned = users[204:222]
    
    # 4. 3월 이탈자 (3% = 18명): 1-2월 활동, 3월 이탈
    mar_churned = users[222:240]
    
    # 5. 4월 이탈자 (3% = 18명): 2-3월 활동, 4월 이탈
    apr_churned = users[240:258]
    
    # 6. 5월 이탈자 (3% = 18명): 3-4월 활동, 5월 이탈
    may_churned = users[258:276]
    
    # 7. 6월 이탈자 (3% = 18명): 4-5월 활동, 6월 이탈
    jun_churned = users[276:294]
    
    # 8. 7월 이탈자 (3% = 18명): 5-6월 활동, 7월 이탈
    jul_churned = users[294:312]
    
    # 9. 8월 이탈자 (3% = 18명): 6-7월 활동, 8월 이탈
    aug_churned = users[312:330]
    
    # 10. 9월 이탈자 (3% = 18명): 7-8월 활동, 9월 이탈
    sep_churned = users[330:348]
    
    # 11. 10월 이탈자 (3% = 18명): 8-9월 활동, 10월 이탈
    oct_churned = users[348:366]
    
    # 12. 11월 이탈자 (3% = 18명): 9-10월 활동, 11월 이탈
    nov_churned = users[366:384]
    
    # 13. 12월 이탈자 (3% = 18명): 10-11월 활동, 12월 이탈
    dec_churned = users[384:402]
    
    # 14. 재활성 사용자 그룹들 (각 월마다 재활성 발생)
    # 2월 재활성 (2% = 12명): 2024년 12월 활동, 1월 이탈, 2월 재활성
    feb_reactivated = users[402:414]
    
    # 3월 재활성 (2% = 12명): 1월 활동, 2월 이탈, 3월 재활성
    mar_reactivated = users[414:426]
    
    # 4월 재활성 (2% = 12명): 2월 활동, 3월 이탈, 4월 재활성
    apr_reactivated = users[426:438]
    
    # 5월 재활성 (2% = 12명): 3월 활동, 4월 이탈, 5월 재활성
    may_reactivated = users[438:450]
    
    # 6월 재활성 (2% = 12명): 4월 활동, 5월 이탈, 6월 재활성
    jun_reactivated = users[450:462]
    
    # 7월 재활성 (2% = 12명): 5월 활동, 6월 이탈, 7월 재활성
    jul_reactivated = users[462:474]
    
    # 8월 재활성 (2% = 12명): 6월 활동, 7월 이탈, 8월 재활성
    aug_reactivated = users[474:486]
    
    # 9월 재활성 (2% = 12명): 7월 활동, 8월 이탈, 9월 재활성
    sep_reactivated = users[486:498]
    
    # 10월 재활성 (2% = 12명): 8월 활동, 9월 이탈, 10월 재활성
    oct_reactivated = users[498:510]
    
    # 11월 재활성 (2% = 12명): 9월 활동, 10월 이탈, 11월 재활성
    nov_reactivated = users[510:522]
    
    # 12월 재활성 (2% = 12명): 10월 활동, 11월 이탈, 12월 재활성
    dec_reactivated = users[522:534]
    
    # 15. 장기 미접속 사용자들
    # 장기 미접속 A (3% = 18명): 2024년 10월 활동, 2025년 1월부터 장기 미접속 (4월 분석 시 90일 경과)
    long_inactive_a = users[534:552]
    
    # 장기 미접속 B (3% = 18명): 2024년 11월 활동, 2025년 2월부터 장기 미접속 (5월 분석 시 90일 경과)
    long_inactive_b = users[552:570]
    
    # 장기 미접속 C (2% = 12명): 2024년 12월 활동, 2025년 3월부터 장기 미접속 (6월 분석 시 90일 경과)
    long_inactive_c = users[570:582]
    
    # 16. 신규 사용자들 (각 월마다 신규 가입)
    # 3월 신규 (1% = 6명)
    mar_new = users[582:588]
    
    # 6월 신규 (1% = 6명)
    jun_new = users[588:594]
    
    # 9월 신규 (1% = 6명)
    sep_new = users[594:600]
    
    return {
        'retained': retained,
        'jan_churned': jan_churned,
        'feb_churned': feb_churned,
        'mar_churned': mar_churned,
        'apr_churned': apr_churned,
        'may_churned': may_churned,
        'jun_churned': jun_churned,
        'jul_churned': jul_churned,
        'aug_churned': aug_churned,
        'sep_churned': sep_churned,
        'oct_churned': oct_churned,
        'nov_churned': nov_churned,
        'dec_churned': dec_churned,
        'feb_reactivated': feb_reactivated,
        'mar_reactivated': mar_reactivated,
        'apr_reactivated': apr_reactivated,
        'may_reactivated': may_reactivated,
        'jun_reactivated': jun_reactivated,
        'jul_reactivated': jul_reactivated,
        'aug_reactivated': aug_reactivated,
        'sep_reactivated': sep_reactivated,
        'oct_reactivated': oct_reactivated,
        'nov_reactivated': nov_reactivated,
        'dec_reactivated': dec_reactivated,
        'long_inactive_a': long_inactive_a,
        'long_inactive_b': long_inactive_b,
        'long_inactive_c': long_inactive_c,
        'mar_new': mar_new,
        'jun_new': jun_new,
        'sep_new': sep_new
    }

def generate_events_for_month(users_list, year, month, min_events=16, max_events=44):
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
        # 일의자리 0,5 방지: 자연스러운 값 생성
        num_events = get_natural_number(min_events, max_events)
        
        # 사용자별 채널 선호도 가져오기
        channel_preference = get_user_channel_preference(user_hash)
        channels = list(channel_preference.keys())
        weights = list(channel_preference.values())
        
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
            
            # 랜덤 액션 선택
            action = random.choice(ACTIONS)
            
            # 사용자 선호도에 따라 채널 선택 (가중치 적용)
            channel = random.choices(channels, weights=weights)[0]
            
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
    print("[완료] 기존 events 테이블 삭제 완료")
    
    # 테이블 재생성
    create_table_sql = """
    CREATE TABLE events (
      id         BIGINT AUTO_INCREMENT PRIMARY KEY,
      user_hash  VARCHAR(255) NOT NULL,
      action     ENUM('login','post','post_delete','post_modify','comment','comment_modify','comment_delete','view','like') NOT NULL,
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
    print("[완료] events 테이블 재생성 완료 (AUTO_INCREMENT 1부터 시작)")

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
    print("2025년 자연스러운 이탈률 분석용 이벤트 데이터 생성 시작...")
    print("=" * 60)
    
    # 사용자 분류
    user_groups = classify_users()
    
    print(f"\n[사용자 그룹 분류] (총 {USER_COUNT}명):")
    print(f"   - 충실 사용자 (1-12월 계속 활동): {len(user_groups['retained'])}명")
    print(f"   - 각 월별 이탈자: 각 {len(user_groups['jan_churned'])}명씩")
    print(f"   - 각 월별 재활성 사용자: 각 {len(user_groups['feb_reactivated'])}명씩")
    print(f"   - 장기 미접속 그룹들: 총 {len(user_groups['long_inactive_a']) + len(user_groups['long_inactive_b']) + len(user_groups['long_inactive_c'])}명")
    print(f"   - 신규 사용자들: 총 {len(user_groups['mar_new']) + len(user_groups['jun_new']) + len(user_groups['sep_new'])}명")
    
    # MySQL 연결 및 테이블 재생성
    try:
        conn = pymysql.connect(**config)
        print(f"\n[연결 성공] MySQL: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        # 테이블 재생성
        recreate_events_table(conn)
        
        all_events = []
        
        # 2024년 10월: 장기 미접속 A 그룹용
        print("\n[2024년 10월] 데이터 생성 중... (장기 미접속 A 그룹용)")
        oct2024_users = user_groups['long_inactive_a']
        oct2024_events = generate_events_for_month(oct2024_users, 2024, 10)
        all_events.extend(oct2024_events)
        print(f"   생성된 이벤트: {len(oct2024_events):,}개")
        
        # 2024년 11월: 장기 미접속 B 그룹용
        print("[2024년 11월] 데이터 생성 중... (장기 미접속 B 그룹용)")
        nov2024_users = user_groups['long_inactive_b']
        nov2024_events = generate_events_for_month(nov2024_users, 2024, 11)
        all_events.extend(nov2024_events)
        print(f"   생성된 이벤트: {len(nov2024_events):,}개")
        
        # 2024년 12월: 장기 미접속 C 그룹 + 1월 이탈자 + 2월 재활성 그룹
        print("[2024년 12월] 데이터 생성 중...")
        dec2024_users = user_groups['long_inactive_c'] + user_groups['jan_churned'] + user_groups['feb_reactivated']
        dec2024_events = generate_events_for_month(dec2024_users, 2024, 12)
        all_events.extend(dec2024_events)
        print(f"   생성된 이벤트: {len(dec2024_events):,}개")
        
        # 2025년 각 월별 데이터 생성
        months_data = [
            # (월, 활동 사용자 그룹들)
            (1, ['retained', 'feb_churned', 'mar_churned', 'apr_churned', 'may_churned', 'jun_churned', 'jul_churned', 'aug_churned', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'mar_reactivated', 'apr_reactivated', 'may_reactivated', 'jun_reactivated', 'jul_reactivated', 'aug_reactivated', 'sep_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated']),
            
            (2, ['retained', 'mar_churned', 'apr_churned', 'may_churned', 'jun_churned', 'jul_churned', 'aug_churned', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'feb_reactivated', 'apr_reactivated', 'may_reactivated', 'jun_reactivated', 'jul_reactivated', 'aug_reactivated', 'sep_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated']),
            
            (3, ['retained', 'apr_churned', 'may_churned', 'jun_churned', 'jul_churned', 'aug_churned', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'mar_reactivated', 'may_reactivated', 'jun_reactivated', 'jul_reactivated', 'aug_reactivated', 'sep_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated', 'mar_new']),
            
            (4, ['retained', 'may_churned', 'jun_churned', 'jul_churned', 'aug_churned', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'apr_reactivated', 'jun_reactivated', 'jul_reactivated', 'aug_reactivated', 'sep_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated', 'mar_new']),
            
            (5, ['retained', 'jun_churned', 'jul_churned', 'aug_churned', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'may_reactivated', 'jul_reactivated', 'aug_reactivated', 'sep_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated', 'mar_new']),
            
            (6, ['retained', 'jul_churned', 'aug_churned', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'jun_reactivated', 'aug_reactivated', 'sep_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated', 'mar_new', 'jun_new']),
            
            (7, ['retained', 'aug_churned', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'jul_reactivated', 'sep_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated', 'mar_new', 'jun_new']),
            
            (8, ['retained', 'sep_churned', 'oct_churned', 'nov_churned', 'dec_churned', 'aug_reactivated', 'oct_reactivated', 'nov_reactivated', 'dec_reactivated', 'mar_new', 'jun_new']),
            
            (9, ['retained', 'oct_churned', 'nov_churned', 'dec_churned', 'sep_reactivated', 'nov_reactivated', 'dec_reactivated', 'mar_new', 'jun_new', 'sep_new']),
            
            (10, ['retained', 'nov_churned', 'dec_churned', 'oct_reactivated', 'dec_reactivated', 'mar_new', 'jun_new', 'sep_new']),
            
            (11, ['retained', 'dec_churned', 'nov_reactivated', 'mar_new', 'jun_new', 'sep_new']),
            
            (12, ['retained', 'dec_reactivated', 'mar_new', 'jun_new', 'sep_new'])
        ]
        
        for month, active_groups in months_data:
            print(f"[2025년 {month}월] 데이터 생성 중...")
            
            # 해당 월에 활동하는 모든 사용자 수집
            month_users = []
            for group_name in active_groups:
                month_users.extend(user_groups[group_name])
            
            month_events = generate_events_for_month(month_users, 2025, month)
            all_events.extend(month_events)
            print(f"   활동 사용자: {len(month_users)}명, 생성된 이벤트: {len(month_events):,}개")
        
        print(f"\n[완료] 총 {len(all_events):,}개의 이벤트 생성 완료")
        
        # 배치 단위로 삽입 (1000개씩)
        batch_size = 1000
        total_inserted = 0
        
        print(f"\n[데이터베이스 삽입] 중...")
        for i in range(0, len(all_events), batch_size):
            batch = all_events[i:i + batch_size]
            inserted = insert_events_batch(conn, batch)
            total_inserted += inserted
            print(f"   배치 {i // batch_size + 1}: {inserted:,}개 이벤트 삽입 완료")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("[완료] 데이터 생성 완료!")
        print("=" * 60)
        print(f"\n[최종 데이터 요약]")
        print(f"   - 총 사용자: {USER_COUNT}명")
        print(f"   - 총 이벤트: {total_inserted:,}개")
        print(f"   - 데이터 기간: 2025년 1월 ~ 12월 (12개월)")
        print(f"   - 평균 이벤트 수: {total_inserted // USER_COUNT}개/사용자")
        
        print(f"\n[스토리 요약]")
        print(f"   1. 충실 사용자 {len(user_groups['retained'])}명이 1년 내내 꾸준히 활동")
        print(f"   2. 매월 {len(user_groups['jan_churned'])}명씩 이탈 발생 (자연스러운 이탈률)")
        print(f"   3. 매월 {len(user_groups['feb_reactivated'])}명씩 재활성 발생 (이전 월 이탈자가 재활성)")
        print(f"   4. 장기 미접속자들이 각기 다른 시점에서 90일 경과")
        print(f"   5. 3월, 6월, 9월에 신규 사용자 각 {len(user_groups['mar_new'])}명씩 가입")
        print(f"   6. 모든 액션 타입 포함: {', '.join(ACTIONS)}")
        
        print(f"\n[분석 결과 보장]")
        print(f"   - 이탈률: 매월 이탈자 발생")
        print(f"   - 활성 사용자: 충실 사용자 + 해당 월 활동자")
        print(f"   - 재활성 사용자: 매월 재활성자 발생")
        print(f"   - 장기 미접속: 90일 경과한 사용자들")
        print(f"\n[자연스러운 값 보장]")
        print(f"   - 모든 이벤트 수는 일의자리가 0이나 5가 아닌 자연스러운 값입니다!")
        
    except Exception as e:
        print(f"[오류] 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
