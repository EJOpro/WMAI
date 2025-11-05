"""
데이터베이스 연결 관리
PyMySQL 기반 MySQL 연결 및 컨텍스트 매니저 제공
"""
import pymysql
from contextlib import contextmanager
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
load_dotenv('match_config.env')


def get_db_config():
    """환경 변수에서 데이터베이스 설정 읽기"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'wmai_db'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }


@contextmanager
def get_db_connection():
    """
    데이터베이스 연결 컨텍스트 매니저
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
    """
    conn = None
    try:
        config = get_db_config()
        conn = pymysql.connect(**config)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    쿼리 실행 헬퍼 함수
    
    Args:
        query: SQL 쿼리
        params: 쿼리 파라미터 (튜플 또는 딕셔너리)
        fetch_one: 단일 결과 반환
        fetch_all: 모든 결과 반환
    
    Returns:
        fetch_one이면 dict, fetch_all이면 list of dict, 아니면 lastrowid
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            return cursor.lastrowid


def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return True
    except Exception as e:
        print(f"[ERROR] 데이터베이스 연결 실패: {e}")
        return False

