"""
API 로그 데이터베이스 관리
MySQL을 사용한 로그 저장 및 조회
"""
import pymysql
from datetime import datetime
from typing import List, Dict, Optional
import json
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class DatabaseLogger:
    """데이터베이스 로그 관리 클래스"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """
        Args:
            host: MySQL 서버 호스트 (환경변수 DB_HOST 또는 기본값 'localhost')
            port: MySQL 서버 포트 (환경변수 DB_PORT 또는 기본값 3306)
            user: MySQL 사용자명 (환경변수 DB_USER 또는 기본값 'root')
            password: MySQL 비밀번호 (환경변수 DB_PASSWORD)
            database: MySQL 데이터베이스명 (환경변수 DB_NAME 또는 기본값 'ethics_logs')
        """
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.port = port or int(os.getenv('DB_PORT', '3306'))
        self.user = user or os.getenv('DB_USER', 'root')
        self.password = password or os.getenv('DB_PASSWORD', '')
        self.database = database or os.getenv('DB_NAME', 'ethics_logs')
        
        # 데이터베이스 초기화
        self._init_database()
    
    def _get_connection(self):
        """MySQL 연결 생성"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def _init_database(self):
        """데이터베이스 테이블 생성"""
        # 먼저 데이터베이스가 있는지 확인하고 없으면 생성
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4'
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARN] 데이터베이스 생성 확인 중 오류: {e}")
        
        # 테이블 생성
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 분석 로그 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                text TEXT NOT NULL,
                score DOUBLE NOT NULL,
                confidence DOUBLE NOT NULL,
                spam DOUBLE NOT NULL,
                spam_confidence DOUBLE,
                types TEXT,
                ip_address VARCHAR(50),
                user_agent TEXT,
                response_time DOUBLE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_timestamp (timestamp),
                INDEX idx_score (score),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 기존 테이블에 types 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE analysis_logs ADD COLUMN types TEXT")
        except pymysql.err.OperationalError:
            # types 컬럼이 이미 있으면 무시
            pass
        
        # 기존 테이블에 spam_confidence 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE analysis_logs ADD COLUMN spam_confidence DOUBLE")
        except pymysql.err.OperationalError:
            # spam_confidence 컬럼이 이미 있으면 무시
            pass
        
        conn.commit()
        conn.close()
        
        print(f"[INFO] 데이터베이스 초기화 완료: {self.user}@{self.host}:{self.port}/{self.database}")
    
    def log_analysis(
        self,
        text: str,
        score: float,
        confidence: float,
        spam: float,
        types: List[str],
        spam_confidence: float = None,
        ip_address: str = None,
        user_agent: str = None,
        response_time: float = None
    ) -> int:
        """
        분석 로그 저장
        
        Args:
            text: 분석한 텍스트
            score: 비윤리 점수
            confidence: 비윤리 신뢰도
            spam: 스팸 지수
            types: 유형 리스트
            spam_confidence: 스팸 신뢰도
            ip_address: 클라이언트 IP
            user_agent: User Agent
            response_time: 응답 시간(초)
        
        Returns:
            생성된 로그 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        types_json = json.dumps(types, ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO analysis_logs 
            (text, score, confidence, spam, spam_confidence, types, ip_address, user_agent, response_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (text, score, confidence, spam, spam_confidence, types_json, ip_address, user_agent, response_time))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return log_id
    
    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        min_score: float = None,
        max_score: float = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """
        로그 조회
        
        Args:
            limit: 최대 조회 개수
            offset: 시작 위치
            min_score: 최소 점수 필터
            max_score: 최대 점수 필터
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
        
        Returns:
            로그 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM analysis_logs WHERE 1=1"
        params = []
        
        if min_score is not None:
            query += " AND score >= %s"
            params.append(min_score)
        
        if max_score is not None:
            query += " AND score <= %s"
            params.append(max_score)
        
        if start_date:
            query += " AND DATE(created_at) >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(created_at) <= %s"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            log = dict(row)
            log['types'] = json.loads(log['types']) if log['types'] else []
            logs.append(log)
        
        conn.close()
        return logs
    
    def get_statistics(self, days: int = 7) -> Dict:
        """
        통계 정보 조회
        
        Args:
            days: 조회할 일수
        
        Returns:
            통계 정보
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 전체 로그 수
        cursor.execute("""
            SELECT COUNT(*) as count FROM analysis_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        total_count = cursor.fetchone()['count']
        
        # 평균 점수
        cursor.execute("""
            SELECT 
                AVG(score) as avg_score,
                AVG(confidence) as avg_confidence,
                AVG(spam) as avg_spam
            FROM analysis_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        avgs = cursor.fetchone()
        
        # 고위험 건수 (score >= 70)
        cursor.execute("""
            SELECT COUNT(*) as count FROM analysis_logs
            WHERE score >= 70
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        high_risk_count = cursor.fetchone()['count']
        
        # 스팸 건수 (spam >= 60)
        cursor.execute("""
            SELECT COUNT(*) as count FROM analysis_logs
            WHERE spam >= 60
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        spam_count = cursor.fetchone()['count']
        
        # 일별 통계
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count,
                AVG(score) as avg_score
            FROM analysis_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (days,))
        daily_stats = [
            {
                'date': str(row['date']),
                'count': row['count'],
                'avg_score': round(row['avg_score'], 1) if row['avg_score'] else 0
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            'period_days': days,
            'total_count': total_count,
            'avg_score': round(avgs['avg_score'], 1) if avgs['avg_score'] else 0,
            'avg_confidence': round(avgs['avg_confidence'], 1) if avgs['avg_confidence'] else 0,
            'avg_spam': round(avgs['avg_spam'], 1) if avgs['avg_spam'] else 0,
            'high_risk_count': high_risk_count,
            'spam_count': spam_count,
            'daily_stats': daily_stats
        }
    
    def delete_log(self, log_id: int) -> bool:
        """
        특정 로그 삭제
        
        Args:
            log_id: 삭제할 로그의 ID
        
        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM analysis_logs WHERE id = %s", (log_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count > 0
    
    def delete_old_logs(self, days: int = 90) -> int:
        """
        오래된 로그 삭제
        
        Args:
            days: 보관 기간 (일)
        
        Returns:
            삭제된 로그 수
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM analysis_logs
            WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def delete_all_logs(self) -> int:
        """
        모든 로그 삭제
        
        Returns:
            삭제된 로그 수
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM analysis_logs")
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count


# 전역 로거 인스턴스
db_logger = DatabaseLogger()

