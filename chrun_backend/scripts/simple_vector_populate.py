"""
간단한 벡터DB 데이터 추가 스크립트 (MySQL high_risk_chunks 테이블에서 읽어서 벡터DB에 저장)
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import execute_query
from chrun_backend.rag_pipeline.high_risk_store import update_feedback

print("=" * 60)
print("MySQL → 벡터DB 데이터 마이그레이션")
print("=" * 60)

# MySQL에서 confirmed=1인 데이터 조회
confirmed_data = execute_query(
    "SELECT chunk_id, sentence, risk_score FROM high_risk_chunks WHERE confirmed = 1",
    fetch_all=True
)

if not confirmed_data:
    print("\n[INFO] confirmed=1인 데이터가 없습니다.")
    print("[INFO] 테스트 데이터를 직접 추가하겠습니다...\n")
    
    # 테스트 데이터 삽입
    test_cases = [
        ("여기 있어봐자 소용없을듯요", 0.85, True),
        ("이 서비스 탈퇴하고 다른 곳으로 갈아탈게요", 0.92, True),
        ("도미노 피자가 훨씬 나은듯??", 0.15, False),
        ("이재모 피자 맛없음 ㅋㅋ", 0.18, False),
        ("맥도날드 버거가 더 나은 것 같아요", 0.20, False),
        ("여기 더 있어야 할 이유가 없다고 생각해요", 0.88, True),
        ("계정 삭제하려고 하는데 어디서 하나요", 0.90, True),
        ("이 커뮤니티 떠날 준비 중입니다", 0.87, True),
        ("다른 플랫폼으로 옮길까 봐요 여기는 한계네요", 0.84, True),
        ("운영자 맘대로 판단하더니 정지 먹였어요", 0.45, False),
        ("회사 일이 너무 많아서 그만두고 싶다", 0.35, False),
        ("스타벅스보다 투썸이 낫네", 0.17, False),
        ("이 사이트 그만 쓸거에요 실망했습니다", 0.86, True),
        ("여기 정말 좋네요 계속 이용할게요", 0.05, False),
    ]
    
    from datetime import datetime
    import uuid
    
    for i, (sentence, risk_score, confirmed) in enumerate(test_cases, 1):
        try:
            chunk_id = f"test_{uuid.uuid4().hex[:8]}"
            
            # MySQL에 먼저 저장
            execute_query(
                "INSERT INTO high_risk_chunks (chunk_id, user_id, post_id, sentence, risk_score, created_at, confirmed) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (chunk_id, f"test_user_{i % 3}", f"test_post_{i}", sentence, risk_score, datetime.now().isoformat(), 1 if confirmed else 0)
            )
            
            confirmed_label = "[위험 맞음]" if confirmed else "[위험 아님]"
            print(f"[{i}/{len(test_cases)}] MySQL 저장 성공: \"{sentence[:40]}...\" {confirmed_label}")
            
        except Exception as e:
            print(f"[{i}/{len(test_cases)}] 실패: {e}")
    
    print(f"\n[INFO] 테스트 데이터 {len(test_cases)}개 추가 완료!")
    
    # 다시 confirmed=1 데이터 조회
    confirmed_data = execute_query(
        "SELECT chunk_id, sentence, risk_score FROM high_risk_chunks WHERE confirmed = 1",
        fetch_all=True
    )

print(f"\n[INFO] 총 {len(confirmed_data)}개의 confirmed=1 데이터를 벡터DB로 마이그레이션합니다.\n")

# 각 데이터를 벡터DB에 저장
success = 0
fail = 0

for i, data in enumerate(confirmed_data, 1):
    chunk_id = data['chunk_id']
    sentence = data['sentence']
    risk_score = data['risk_score']
    
    try:
        print(f"[{i}/{len(confirmed_data)}] 처리 중: \"{sentence[:50]}...\"")
        
        # update_feedback 함수가 confirmed=True일 때 자동으로 벡터DB에 저장
        update_feedback(
            chunk_id=chunk_id,
            confirmed=True,
            who_labeled="admin",
            segment="migration",
            reason="batch_migration"
        )
        
        print(f"  [OK] 벡터DB 저장 성공!\n")
        success += 1
        
    except Exception as e:
        print(f"  [FAIL] 실패: {e}\n")
        fail += 1

print("=" * 60)
print(f"마이그레이션 완료!")
print(f"  성공: {success}개")
print(f"  실패: {fail}개")
print("=" * 60)

