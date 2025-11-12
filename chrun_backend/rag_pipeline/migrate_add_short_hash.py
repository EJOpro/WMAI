"""
데이터베이스 마이그레이션: feedback_events에 short_hash 컬럼 추가

실행 방법:
    python migrate_add_short_hash.py
"""

import os
import sys
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def get_db_engine():
    """DB 엔진 생성 (간단 버전, chromadb import 회피)"""
    # 실제 서버가 사용하는 DB 경로
    db_path = "c:/Users/201/wmai/WMAI/risk_demo.sqlite3"
    print(f"[마이그레이션] DB 경로: {db_path}")
    return create_engine(f"sqlite:///{db_path}")

def migrate():
    """feedback_events 테이블 생성 및 short_hash 컬럼 추가"""
    engine = get_db_engine()
    
    print("[마이그레이션] 시작...")
    print(f"[마이그레이션] DB 연결: {engine.url}")
    
    # 테이블 정의
    metadata = MetaData()
    feedback_events = Table(
        "feedback_events",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("chunk_id", String(64)),
        Column("user_hash", String(64)),
        Column("sentence", String(2048)),
        Column("pred_score", Float),
        Column("final_label", String(32)),
        Column("confirmed", Integer),
        Column("created_at", String(64)),
        Column("short_hash", String(32), nullable=True),
    )
    
    with engine.connect() as conn:
        # 1. 테이블 존재 여부 확인
        try:
            result = conn.execute(text("SELECT 1 FROM feedback_events LIMIT 1"))
            print("[마이그레이션] feedback_events 테이블이 이미 존재합니다.")
            
            # 2. short_hash 컬럼 존재 확인
            try:
                result = conn.execute(text("SELECT short_hash FROM feedback_events LIMIT 1"))
                print("[마이그레이션] short_hash 컬럼이 이미 존재합니다. 스킵합니다.")
                return
            except Exception:
                print("[마이그레이션] short_hash 컬럼이 없습니다. 추가합니다...")
                
                # 3. 컬럼 추가
                try:
                    conn.execute(text("ALTER TABLE feedback_events ADD COLUMN short_hash TEXT"))
                    conn.commit()
                    print("[마이그레이션] [OK] short_hash 컬럼 추가 완료!")
                except Exception as e:
                    print(f"[마이그레이션] [ERROR] 컬럼 추가 실패: {e}")
                    conn.rollback()
                    raise
                    
        except Exception:
            # 테이블이 없으면 생성
            print("[마이그레이션] feedback_events 테이블이 없습니다. 생성합니다...")
            metadata.create_all(engine)
            print("[마이그레이션] [OK] feedback_events 테이블 생성 완료!")
    
    print("[마이그레이션] 완료!")

if __name__ == "__main__":
    try:
        migrate()
        print("\n[SUCCESS] 마이그레이션 성공!")
        print("이제 uvicorn 서버를 재시작하세요.")
    except Exception as e:
        print(f"\n[ERROR] 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

