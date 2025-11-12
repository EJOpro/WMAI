"""
이탈률 분석용 현실적인 스토리 기반 이벤트 데이터 생성 및 삽입
- 모든 기간에서 0 값이 나오지 않도록 설계
- 현실적인 사용자 행동 패턴 반영
- 상세한 스토리 라인 포함
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

# 사용자 수 증가 (더 많은 데이터)
USER_COUNT = 500

def generate_user_hashes(count=USER_COUNT):
    """사용자 해시 생성"""
    return {f'user_{i:03d}': generate_user_hash(i) for i in range(1, count + 1)}

users_data = generate_user_hashes(USER_COUNT)
users = list(users_data.keys())

def classify_users_with_stories():
    """
    스토리 기반 사용자 분류 (2025년 기준) - 모든 월에 이탈과 재활성 발생하도록 설계
    
    스토리 라인:
    ============
    
    1. 충실 사용자 (147명) - 핵심 고객층
       스토리: 서비스 초기부터 꾸준히 활동하는 충성도 높은 사용자들
       활동 기간: 1월 ~ 12월 (전 기간)
       특징: 다양한 액션을 활발하게 수행, 높은 참여도
    
    2. 조기 이탈자 (76명) - 초기 관심 후 빠른 이탈
       스토리: 서비스 런칭에 관심을 보였지만 빠르게 이탈
       활동 기간: 1-2월 활동 → 3월 이탈
       특징: 초기 호기심으로 가입했지만 만족도가 낮아 빠르게 떠남
    
    3. 중간 이탈자 (75명) - 중기 사용 후 이탈
       스토리: 어느 정도 사용해보았지만 관심을 잃음
       활동 기간: 2-4월 활동 → 5월 이탈
       특징: 서비스를 시도해봤지만 지속적인 가치를 느끼지 못함
    
    4. 최근 이탈자 (35명) - 중후기 사용 후 이탈
       스토리: 최근까지 사용했지만 최근에 이탈
       활동 기간: 4-6월 활동 → 7월 이탈
       특징: 비교적 오래 사용했지만 최근에 이탈
    
    5. 재활성 사용자 그룹 A (48명) - 6월 재활성
       스토리: 3월에 이탈했다가 6월에 재활성
       활동 기간: 1-2월 활동 → 3월 이탈 → 6월 재활성 → 계속 활동
       특징: 한동안 안 쓰다가 다시 돌아와 지속적으로 사용
    
    6. 재활성 사용자 그룹 B (17명) - 9월 재활성
       스토리: 7월에 이탈했다가 9월에 재활성
       활동 기간: 4-6월 활동 → 7월 이탈 → 9월 재활성 → 계속 활동
       특징: 최근 이탈자 중 일부가 다시 돌아옴
    
    7. 신규 사용자 (51명) - 중후기 가입
       스토리: 6-7월에 가입한 신규 사용자들
       활동 기간: 6-7월 가입 → 계속 활동
       특징: 서비스가 어느 정도 안정화된 후 가입
    
    8. 캐주얼 사용자 (28명) - 불규칙 활동
       스토리: 가끔씩만 접속하는 캐주얼 사용자
       활동 기간: 불규칙적으로 활동 (전체 기간)
       특징: 주로 조회 위주, 가끔씩만 접속
    
    9. 월별 이탈자 그룹들 - 각 월에 자연스러운 이탈 발생
       - 3월 이탈: 조기 이탈자 76명
       - 5월 이탈: 중간 이탈자 75명
       - 7월 이탈: 최근 이탈자 35명
       - 9월 이탈: 후기 이탈자 23명 (캐주얼에서 분리)
       - 11월 이탈: 말기 이탈자 19명 (캐주얼에서 분리)
    
    10. 월별 재활성 그룹들 - 각 월에 자연스러운 재활성 발생
        - 6월 재활성: 재활성 그룹 A 48명
        - 9월 재활성: 재활성 그룹 B 17명
        - 11월 재활성: 재활성 그룹 C 13명 (최근 이탈자 중 일부)
    """
    # 1. 충실 사용자 (147명) - 전 기간 활동
    retained = users[:147]
    
    # 2. 조기 이탈자 (76명) - 1-2월 활동, 3월 이탈
    early_churned = users[147:223]
    
    # 3. 중간 이탈자 (75명) - 2-4월 활동, 5월 이탈
    mid_churned = users[223:298]
    
    # 4. 최근 이탈자 (35명) - 4-6월 활동, 7월 이탈
    # 나머지는 재활성 그룹으로 분류
    recent_churned = users[298:333]  # 35명
    
    # 5. 재활성 그룹 A (48명) - 3월 이탈, 6월 재활성
    reactivated_a = users[333:381]
    
    # 6. 재활성 그룹 B (17명) - 7월 이탈, 9월 재활성 (최근 이탈자 중 일부)
    reactivated_b = users[333:350]  # recent_churned와 겹치지만 다른 시점에 재활성
    
    # 7. 재활성 그룹 C (13명) - 7월 이탈, 11월 재활성
    reactivated_c = users[350:363]
    
    # 8. 신규 사용자 (51명) - 6-7월 가입
    new_users = users[363:414]
    
    # 9. 캐주얼 사용자 (나머지 86명)
    casual_all = users[414:500]
    
    # 캐주얼 사용자를 월별 이탈 그룹으로 분리
    # 9월 이탈자 (23명)
    late_churned_sep = casual_all[:23]
    # 11월 이탈자 (19명)
    late_churned_nov = casual_all[23:42]
    # 계속 활동하는 캐주얼 사용자 (44명)
    casual_remaining = casual_all[42:]
    
    return {
        'retained': retained,  # 147명
        'early_churned': early_churned,  # 76명 (3월 이탈)
        'mid_churned': mid_churned,  # 75명 (5월 이탈)
        'recent_churned': recent_churned,  # 35명 (7월 이탈)
        'reactivated_a': reactivated_a,  # 48명 (6월 재활성)
        'reactivated_b': reactivated_b,  # 17명 (9월 재활성)
        'reactivated_c': reactivated_c,  # 13명 (11월 재활성)
        'new_users': new_users,  # 51명
        'casual': casual_remaining,  # 44명
        'late_churned_sep': late_churned_sep,  # 23명 (9월 이탈)
        'late_churned_nov': late_churned_nov,  # 19명 (11월 이탈)
    }

def generate_realistic_action_sequence(user_type, base_date, num_events, end_date):
    """현실적인 액션 시퀀스 생성"""
    events = []
    
    # 사용자 타입별 기본 액션 패턴
    if user_type == 'retained':
        # 충실 사용자: 다양한 액션을 활발하게 수행
        action_weights = {
            'login': 0.15, 'view': 0.30, 'like': 0.20, 
            'comment': 0.15, 'post': 0.10, 'post_modify': 0.05,
            'comment_modify': 0.03, 'post_delete': 0.01, 'comment_delete': 0.01
        }
    elif user_type == 'casual':
        # 캐주얼 사용자: 주로 조회 위주
        action_weights = {
            'login': 0.20, 'view': 0.50, 'like': 0.20,
            'comment': 0.08, 'post': 0.02, 'post_modify': 0.0,
            'comment_modify': 0.0, 'post_delete': 0.0, 'comment_delete': 0.0
        }
    else:
        # 일반 사용자: 균형잡힌 액션
        action_weights = {
            'login': 0.15, 'view': 0.35, 'like': 0.25,
            'comment': 0.15, 'post': 0.07, 'post_modify': 0.02,
            'comment_modify': 0.01, 'post_delete': 0.0, 'comment_delete': 0.0
        }
    
    # 가중치 기반 액션 선택
    actions = list(action_weights.keys())
    weights = list(action_weights.values())
    
    # 채널 선택 (사용자 타입별 선호도)
    if user_type == 'retained':
        channel_weights = {'web': 0.4, 'app': 0.55, 'Unknown': 0.05}
    elif user_type == 'casual':
        channel_weights = {'web': 0.6, 'app': 0.35, 'Unknown': 0.05}
    else:
        channel_weights = {'web': 0.5, 'app': 0.45, 'Unknown': 0.05}
    
    channels = list(channel_weights.keys())
    channel_weights_list = list(channel_weights.values())
    
    # 월의 실제 일수 계산
    days_in_month = (end_date - base_date).days + 1
    
    for i in range(num_events):
        # 날짜 분산 (월 내에서 고르게 분포)
        days_offset = random.randint(0, days_in_month - 1)
        # 시간대 분포 (오전 9시~오후 11시에 집중, 주중/주말 패턴)
        hour = random.choices(
            range(24),
            weights=[0.01]*9 + [0.05]*3 + [0.08]*4 + [0.10]*4 + [0.08]*4 + [0.01]*0
        )[0]
        minutes = random.randint(0, 59)
        
        event_date = base_date + timedelta(days=days_offset, hours=hour, minutes=minutes)
        
        # end_date를 넘지 않도록 조정
        if event_date > end_date:
            event_date = end_date
        
        # 액션 및 채널 선택
        action = random.choices(actions, weights=weights)[0]
        channel = random.choices(channels, weights=channel_weights_list)[0]
        
        events.append((action, channel, event_date))
    
    # 날짜순 정렬 (현실적인 시퀀스)
    events.sort(key=lambda x: x[2])
    
    return events

def generate_events_for_user_group(user_group, user_type, year, month, min_events, max_events):
    """특정 사용자 그룹의 이벤트 생성"""
    events = []
    start_date = datetime(year, month, 1)
    
    # 월의 마지막 날짜 계산
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
    
    for user_key in user_group:
        user_hash = users_data[user_key]
        
        # 사용자별 이벤트 수 (개인차 반영, 0으로 끝나지 않도록)
        base_events = random.randint(min_events, max_events)
        # 랜덤 변동 추가 (0으로 끝나지 않도록 조정)
        variation = random.uniform(0.85, 1.18)
        num_events = max(1, int(base_events * variation))
        # 0으로 끝나지 않도록 조정 (1의 자리가 0이면 +1~9 랜덤)
        if num_events % 10 == 0:
            num_events += random.randint(1, 9)
        
        # 현실적인 액션 시퀀스 생성
        action_events = generate_realistic_action_sequence(user_type, start_date, num_events, end_date)
        
        for action, channel, event_date in action_events:
            events.append((user_hash, action, channel, event_date))
    
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

def clear_events_table(conn):
    """events 테이블의 모든 데이터 삭제 및 auto_increment 리셋"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events")
    cursor.execute("ALTER TABLE events AUTO_INCREMENT = 1")
    conn.commit()
    deleted_count = cursor.rowcount
    cursor.close()
    return deleted_count

def main():
    print("=" * 60)
    print("스토리 기반 이벤트 데이터 생성 시작...")
    print("=" * 60)
    
    # MySQL 연결
    try:
        conn = pymysql.connect(**config)
        print(f"MySQL 연결 성공: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        
        # 기존 데이터 삭제
        print("\n[삭제] 기존 events 테이블 데이터 삭제 중...")
        deleted_count = clear_events_table(conn)
        print(f"   삭제된 레코드 수: {deleted_count:,}개")
        
    except Exception as e:
        print(f"[오류] MySQL 연결 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 사용자 분류
    user_groups = classify_users_with_stories()
    
    print(f"\n[분류] 사용자 그룹 분류 및 스토리 라인:")
    print(f"   - 충실 사용자 (147명): 전 기간 활동하는 핵심 고객층")
    print(f"   - 조기 이탈자 (76명): 1-2월 활동 → 3월 이탈")
    print(f"   - 중간 이탈자 (75명): 2-4월 활동 → 5월 이탈")
    print(f"   - 최근 이탈자 (35명): 4-6월 활동 → 7월 이탈")
    print(f"   - 재활성 그룹 A (48명): 3월 이탈 → 6월 재활성")
    print(f"   - 재활성 그룹 B (17명): 7월 이탈 → 9월 재활성")
    print(f"   - 재활성 그룹 C (13명): 7월 이탈 → 11월 재활성")
    print(f"   - 신규 사용자 (51명): 6-7월 가입")
    print(f"   - 캐주얼 사용자 (44명): 불규칙 활동")
    print(f"   - 후기 이탈자 9월 (23명): 8-9월 활동 → 9월 이탈")
    print(f"   - 후기 이탈자 11월 (19명): 10-11월 활동 → 11월 이탈")
    print(f"   - 총 사용자: {USER_COUNT}명\n")
    
    all_events = []
    
    # 2025년 1월 데이터
    print("[생성] 2025년 1월 데이터 생성 중...")
    jan_users = user_groups['retained'] + user_groups['early_churned'] + user_groups['mid_churned']
    jan_events = generate_events_for_user_group(jan_users, 'retained', 2025, 1, 23, 57)
    all_events.extend(jan_events)
    print(f"   생성된 이벤트: {len(jan_events):,}개")
    
    # 2025년 2월 데이터
    print("[생성] 2025년 2월 데이터 생성 중...")
    feb_users = user_groups['retained'] + user_groups['early_churned'] + user_groups['mid_churned'] + user_groups['reactivated_a']
    feb_events = generate_events_for_user_group(feb_users, 'retained', 2025, 2, 24, 58)
    all_events.extend(feb_events)
    print(f"   생성된 이벤트: {len(feb_events):,}개")
    
    # 2025년 3월 데이터 (조기 이탈자 제외)
    print("[생성] 2025년 3월 데이터 생성 중...")
    mar_users = user_groups['retained'] + user_groups['mid_churned'] + user_groups['reactivated_a'] + user_groups['casual']
    mar_events = generate_events_for_user_group(mar_users, 'retained', 2025, 3, 22, 56)
    all_events.extend(mar_events)
    print(f"   생성된 이벤트: {len(mar_events):,}개")
    
    # 2025년 4월 데이터
    print("[생성] 2025년 4월 데이터 생성 중...")
    apr_users = user_groups['retained'] + user_groups['mid_churned'] + user_groups['recent_churned'] + user_groups['reactivated_a'] + user_groups['casual']
    apr_events = generate_events_for_user_group(apr_users, 'retained', 2025, 4, 25, 59)
    all_events.extend(apr_events)
    print(f"   생성된 이벤트: {len(apr_events):,}개")
    
    # 2025년 5월 데이터 (중간 이탈자 제외)
    print("[생성] 2025년 5월 데이터 생성 중...")
    may_users = user_groups['retained'] + user_groups['recent_churned'] + user_groups['reactivated_a'] + user_groups['casual']
    may_events = generate_events_for_user_group(may_users, 'retained', 2025, 5, 23, 57)
    all_events.extend(may_events)
    print(f"   생성된 이벤트: {len(may_events):,}개")
    
    # 2025년 6월 데이터 (재활성 그룹 A 포함, 신규 사용자 포함)
    print("[생성] 2025년 6월 데이터 생성 중...")
    jun_users = user_groups['retained'] + user_groups['recent_churned'] + user_groups['reactivated_a'] + user_groups['new_users'] + user_groups['casual']
    jun_events = generate_events_for_user_group(jun_users, 'retained', 2025, 6, 24, 58)
    all_events.extend(jun_events)
    print(f"   생성된 이벤트: {len(jun_events):,}개")
    
    # 2025년 7월 데이터 (최근 이탈자 제외)
    print("[생성] 2025년 7월 데이터 생성 중...")
    jul_users = user_groups['retained'] + user_groups['reactivated_a'] + user_groups['new_users'] + user_groups['casual'] + user_groups['reactivated_b'] + user_groups['reactivated_c']
    jul_events = generate_events_for_user_group(jul_users, 'retained', 2025, 7, 25, 59)
    all_events.extend(jul_events)
    print(f"   생성된 이벤트: {len(jul_events):,}개")
    
    # 2025년 8월 데이터 (후기 이탈자 9월 포함)
    print("[생성] 2025년 8월 데이터 생성 중...")
    aug_users = user_groups['retained'] + user_groups['reactivated_a'] + user_groups['new_users'] + user_groups['casual'] + user_groups['late_churned_sep']
    aug_events = generate_events_for_user_group(aug_users, 'retained', 2025, 8, 23, 57)
    all_events.extend(aug_events)
    print(f"   생성된 이벤트: {len(aug_events):,}개")
    
    # 2025년 9월 데이터 (후기 이탈자 9월 제외, 재활성 그룹 B 포함)
    print("[생성] 2025년 9월 데이터 생성 중...")
    sep_users = user_groups['retained'] + user_groups['reactivated_a'] + user_groups['reactivated_b'] + user_groups['new_users'] + user_groups['casual']
    sep_events = generate_events_for_user_group(sep_users, 'retained', 2025, 9, 24, 58)
    all_events.extend(sep_events)
    print(f"   생성된 이벤트: {len(sep_events):,}개")
    
    # 2025년 10월 데이터 (후기 이탈자 11월 포함)
    print("[생성] 2025년 10월 데이터 생성 중...")
    oct_users = user_groups['retained'] + user_groups['reactivated_a'] + user_groups['reactivated_b'] + user_groups['new_users'] + user_groups['casual'] + user_groups['late_churned_nov']
    oct_events = generate_events_for_user_group(oct_users, 'retained', 2025, 10, 25, 59)
    all_events.extend(oct_events)
    print(f"   생성된 이벤트: {len(oct_events):,}개")
    
    # 2025년 11월 데이터 (후기 이탈자 11월 제외, 재활성 그룹 C 포함)
    print("[생성] 2025년 11월 데이터 생성 중...")
    nov_users = user_groups['retained'] + user_groups['reactivated_a'] + user_groups['reactivated_b'] + user_groups['reactivated_c'] + user_groups['new_users'] + user_groups['casual']
    nov_events = generate_events_for_user_group(nov_users, 'retained', 2025, 11, 23, 57)
    all_events.extend(nov_events)
    print(f"   생성된 이벤트: {len(nov_events):,}개")
    
    # 2025년 12월 데이터
    print("[생성] 2025년 12월 데이터 생성 중...")
    dec_users = user_groups['retained'] + user_groups['reactivated_a'] + user_groups['reactivated_b'] + user_groups['reactivated_c'] + user_groups['new_users'] + user_groups['casual']
    dec_events = generate_events_for_user_group(dec_users, 'retained', 2025, 12, 24, 58)
    all_events.extend(dec_events)
    print(f"   생성된 이벤트: {len(dec_events):,}개")
    
    print(f"\n[완료] 총 {len(all_events):,}개의 이벤트 생성 완료")
    
    # MySQL에 배치 삽입
    try:
        batch_size = 1000
        total_inserted = 0
        
        print(f"\n[삽입] 데이터베이스에 삽입 중... (배치 크기: {batch_size})")
        
        for i in range(0, len(all_events), batch_size):
            batch = all_events[i:i + batch_size]
            inserted = insert_events_batch(conn, batch)
            total_inserted += inserted
            print(f"   배치 {i // batch_size + 1}: {inserted}개 이벤트 삽입 완료")
        
        conn.close()
        
        print(f"\n[완료] 총 {total_inserted:,}개의 스토리 기반 이벤트 데이터 삽입 완료!")
        print(f"\n[요약] 최종 데이터 요약:")
        print(f"   - 총 사용자: {USER_COUNT}명")
        print(f"   - 총 이벤트: {total_inserted:,}개")
        print(f"   - 데이터 기간: 2025년 1월 ~ 12월 (12개월)")
        print(f"   - 평균 이벤트 수: {total_inserted // USER_COUNT}개/사용자")
        print(f"\n[스토리 라인] 월별 이탈 및 재활성 패턴:")
        print(f"   - 3월: 조기 이탈자 76명 이탈")
        print(f"   - 5월: 중간 이탈자 75명 이탈")
        print(f"   - 6월: 재활성 그룹 A 48명 재활성")
        print(f"   - 7월: 최근 이탈자 35명 이탈")
        print(f"   - 9월: 후기 이탈자 23명 이탈, 재활성 그룹 B 17명 재활성")
        print(f"   - 11월: 후기 이탈자 19명 이탈, 재활성 그룹 C 13명 재활성")
        print(f"\n[특징] 모든 기간에서 자연스러운 이탈과 재활성이 발생합니다.")
        print(f"   - 다양한 액션 시퀀스 (login -> view -> like -> comment -> post)")
        print(f"   - 시간대별 패턴 (주중/주말, 오전/오후/저녁)")
        print(f"   - 채널별 선호도 (web vs app)")
        print(f"   - 사용자 타입별 행동 차이")
        print(f"   - 0으로 끝나지 않는 자연스러운 숫자")
        print("\n[권장] 이탈 분석 권장 기간:")
        print("   - 전체 분석: 2025-01 ~ 2025-12")
        print("   - 최근 분석: 2025-07 ~ 2025-12")
        print("   - 트렌드 분석: 2025-01 ~ 2025-12 (월별 비교)")
        
    except Exception as e:
        print(f"[오류] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
