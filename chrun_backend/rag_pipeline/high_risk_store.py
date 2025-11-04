"""
로컬 테스트용 SQLite 고위험 문장 저장소
이탈 위험 사용자 리스트를 브라우저에서 확인할 수 있도록 더미 데이터를 제공합니다.
"""

import sqlite3
import uuid
from typing import List, Dict, Any
from datetime import datetime
import os

# SQLite 데이터베이스 파일 경로 (로컬 테스트용)
DB_PATH = "./risk_demo.sqlite3"

def init_db():
    """
    DB 파일 연결하고 테이블 없으면 만들고, 테이블이 비어있으면 샘플 더미 데이터 삽입
    로컬 테스트용 SQLite 초기화 함수
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 테이블 생성 (없으면)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS high_risk_chunks (
            chunk_id TEXT PRIMARY KEY,
            user_id TEXT,
            post_id TEXT,
            sentence TEXT,
            risk_score REAL,
            created_at TEXT,
            confirmed INTEGER  -- 0 또는 1
        )
    ''')
    
    # 테이블이 비어있는지 확인
    cursor.execute('SELECT COUNT(*) FROM high_risk_chunks')
    count = cursor.fetchone()[0]
    
    # 비어있으면 샘플 더미 데이터 삽입
    if count == 0:
        sample_data = [
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_001',
                'post_id': 'post_123',
                'sentence': '서비스 떠날까 고민 중이에요... 여기 있을 이유가 없어 보여서',
                'risk_score': 0.91,
                'created_at': '2025-10-31T14:00:00',
                'confirmed': 0
            },
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_017',
                'post_id': 'post_456',
                'sentence': '탈퇴할까 생각중입니다 진짜로 더 이상 의미가 없는 것 같아요',
                'risk_score': 0.87,
                'created_at': '2025-10-31T13:45:00',
                'confirmed': 1
            },
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_042',
                'post_id': 'post_789',
                'sentence': '여기 더 있어야 할 이유가 없다고 생각해요 떠날 때가 된 것 같습니다',
                'risk_score': 0.83,
                'created_at': '2025-10-31T13:30:00',
                'confirmed': 0
            },
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_088',
                'post_id': 'post_321',
                'sentence': '이 서비스 그만 쓸까 봐요 다른 곳으로 옮기는 게 나을 것 같아서',
                'risk_score': 0.79,
                'created_at': '2025-10-31T13:15:00',
                'confirmed': 1
            },
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_156',
                'post_id': 'post_654',
                'sentence': '계정 삭제하고 싶은데 어떻게 하나요? 더 이상 사용할 일이 없을 것 같아요',
                'risk_score': 0.75,
                'created_at': '2025-10-31T13:00:00',
                'confirmed': 0
            },
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_203',
                'post_id': 'post_987',
                'sentence': '이제 정말 그만둘 때가 된 것 같습니다 다른 대안을 찾아보고 있어요',
                'risk_score': 0.72,
                'created_at': '2025-10-31T12:45:00',
                'confirmed': 1
            },
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_299',
                'post_id': 'post_111',
                'sentence': '서비스 품질이 너무 떨어져서 이탈을 고려하고 있습니다',
                'risk_score': 0.68,
                'created_at': '2025-10-31T12:30:00',
                'confirmed': 0
            },
            {
                'chunk_id': str(uuid.uuid4()),
                'user_id': 'user_334',
                'post_id': 'post_222',
                'sentence': '다른 플랫폼으로 갈아탈까 생각 중입니다 여기는 한계가 있는 것 같아요',
                'risk_score': 0.65,
                'created_at': '2025-10-31T12:15:00',
                'confirmed': 1
            }
        ]
        
        # 샘플 데이터 삽입
        for data in sample_data:
            cursor.execute('''
                INSERT INTO high_risk_chunks 
                (chunk_id, user_id, post_id, sentence, risk_score, created_at, confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['chunk_id'],
                data['user_id'], 
                data['post_id'],
                data['sentence'],
                data['risk_score'],
                data['created_at'],
                data['confirmed']
            ))
        
        print(f"[INFO] 로컬 테스트용 더미 데이터 {len(sample_data)}개 삽입 완료")
    
    conn.commit()
    conn.close()
    print(f"[INFO] 로컬 테스트용 SQLite DB 초기화 완료: {DB_PATH}")

def get_recent_high_risk(limit: int = 5) -> List[Dict[str, Any]]:
    """
    created_at DESC로 정렬된 상위 limit개를 dict 리스트로 리턴
    로컬 테스트용 고위험 문장 조회 함수
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict 형태로 결과 반환
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT chunk_id, user_id, post_id, sentence, risk_score, created_at, confirmed
        FROM high_risk_chunks 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # dict 리스트로 변환
    result = []
    for row in rows:
        result.append({
            'chunk_id': row['chunk_id'],
            'user_id': row['user_id'],
            'post_id': row['post_id'],
            'sentence': row['sentence'],
            'risk_score': row['risk_score'],
            'created_at': row['created_at'],
            'confirmed': row['confirmed']
        })
    
    print(f"[INFO] 로컬 테스트용 고위험 문장 {len(result)}개 조회 완료")
    return result

def update_feedback(chunk_id: str, confirmed: bool) -> None:
    """
    해당 chunk_id의 confirmed 값을 1 또는 0으로 업데이트
    로컬 테스트용 피드백 업데이트 함수
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    confirmed_value = 1 if confirmed else 0
    
    cursor.execute('''
        UPDATE high_risk_chunks 
        SET confirmed = ? 
        WHERE chunk_id = ?
    ''', (confirmed_value, chunk_id))
    
    conn.commit()
    affected_rows = cursor.rowcount
    conn.close()
    
    if affected_rows > 0:
        print(f"[INFO] 로컬 테스트용 피드백 업데이트 완료: {chunk_id} -> confirmed={confirmed_value}")
    else:
        print(f"[WARN] 로컬 테스트용 chunk_id를 찾을 수 없음: {chunk_id}")

def save_high_risk_chunk(chunk_dict: Dict[str, Any]) -> None:
    """
    일단 지금은 안 써도 되지만, risk_scorer에서 쓸 수 있게 남겨둠
    로컬 테스트용 고위험 문장 저장 함수 (향후 확장용)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    chunk_id = chunk_dict.get('chunk_id', str(uuid.uuid4()))
    
    cursor.execute('''
        INSERT OR REPLACE INTO high_risk_chunks 
        (chunk_id, user_id, post_id, sentence, risk_score, created_at, confirmed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        chunk_id,
        chunk_dict.get('user_id', ''),
        chunk_dict.get('post_id', ''),
        chunk_dict.get('sentence', ''),
        chunk_dict.get('risk_score', 0.0),
        chunk_dict.get('created_at', datetime.now().isoformat()),
        chunk_dict.get('confirmed', 0)
    ))
    
    conn.commit()
    conn.close()
    print(f"[INFO] 로컬 테스트용 고위험 문장 저장 완료: {chunk_id}")