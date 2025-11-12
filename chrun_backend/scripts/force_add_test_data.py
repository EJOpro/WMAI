"""
강제로 테스트 데이터를 MySQL과 벡터DB에 추가
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import execute_query
from chrun_backend.rag_pipeline.high_risk_store import update_feedback
from datetime import datetime
import uuid

# 테스트 데이터
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
    ("치킨은 역시 교촌이 최고", 0.12, False),
    ("아이폰이 갤럭시보다 나은듯", 0.16, False),
    ("더 이상 의미가 없는 것 같아요 탈퇴 고민 중", 0.89, True),
]

print("=" * 60)
print("테스트 데이터 강제 추가")
print("=" * 60)

mysql_success = 0
vector_success = 0

for i, (sentence, risk_score, confirmed) in enumerate(test_cases, 1):
    try:
        chunk_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # 1. MySQL에 저장
        execute_query(
            "INSERT INTO high_risk_chunks (chunk_id, user_id, post_id, sentence, risk_score, created_at, confirmed) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (chunk_id, f"{i % 3}", f"test_post_{i}", sentence, risk_score, datetime.now().isoformat(), 1 if confirmed else 0)
        )
        
        mysql_success += 1
        print(f"[{i}/{len(test_cases)}] MySQL OK: \"{sentence[:40]}...\" [confirmed={confirmed}]")
        
        # 2. confirmed=True인 경우만 벡터DB에도 저장
        if confirmed:
            try:
                update_feedback(
                    chunk_id=chunk_id,
                    confirmed=True,
                    who_labeled="admin",
                    segment="test",
                    reason="test_data"
                )
                vector_success += 1
                print(f"  -> Vector OK!")
            except Exception as ve:
                print(f"  -> Vector FAIL: {ve}")
        
    except Exception as e:
        print(f"[{i}/{len(test_cases)}] FAIL: {e}")

print("\n" + "=" * 60)
print(f"완료!")
print(f"  MySQL 저장: {mysql_success}/{len(test_cases)}개")
print(f"  Vector 저장: {vector_success}개 (confirmed=True만)")
print("=" * 60)

