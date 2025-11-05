"""
MySQL 데이터베이스 연결 관리
"""
import pymysql
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.connection_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'wmai_db'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
    
    def get_connection(self):
        """DB 연결 반환"""
        return pymysql.connect(**self.connection_config)
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """SELECT 쿼리 실행"""
        with self.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """INSERT 쿼리 실행, ID 반환"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """UPDATE 쿼리 실행, 영향받은 행 수 반환"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                return cursor.execute(query, params)

db_manager = DatabaseManager()
