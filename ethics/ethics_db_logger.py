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
            database: MySQL 데이터베이스명 (환경변수 DB_NAME 또는 기본값 'wmai')
        """
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.port = port or int(os.getenv('DB_PORT', '3306'))
        self.user = user or os.getenv('DB_USER', 'root')
        self.password = password or os.getenv('DB_PASSWORD', '')
        self.database = database or os.getenv('DB_NAME', 'wmai')
        
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
            CREATE TABLE IF NOT EXISTS ethics_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                text TEXT NOT NULL,
                score DOUBLE DEFAULT NULL,
                confidence DOUBLE DEFAULT NULL,
                spam DOUBLE DEFAULT NULL,
                spam_confidence DOUBLE DEFAULT NULL,
                types TEXT,
                ip_address VARCHAR(50) DEFAULT NULL,
                user_agent TEXT,
                response_time DOUBLE DEFAULT NULL,
                rag_applied TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ethics_created_at (created_at DESC),
                INDEX idx_ethics_score (score),
                INDEX idx_ethics_spam (spam)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 기존 테이블에 types 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN types TEXT")
        except pymysql.err.OperationalError:
            # types 컬럼이 이미 있으면 무시
            pass
        
        # 기존 테이블에 spam_confidence 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN spam_confidence DOUBLE")
        except pymysql.err.OperationalError:
            # spam_confidence 컬럼이 이미 있으면 무시
            pass

        # RAG 관련 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN rag_applied TINYINT(1) DEFAULT 0")
        except pymysql.err.OperationalError:
            pass
        
        # 자동 차단 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN auto_blocked TINYINT(1) DEFAULT 0")
        except pymysql.err.OperationalError:
            pass
        
        # spam 컬럼 NULL 허용으로 변경 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE ethics_logs MODIFY COLUMN spam DOUBLE DEFAULT NULL")
        except pymysql.err.OperationalError:
            pass
        
        # score, confidence 컬럼 NULL 허용으로 변경 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE ethics_logs MODIFY COLUMN score DOUBLE DEFAULT NULL")
        except pymysql.err.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE ethics_logs MODIFY COLUMN confidence DOUBLE DEFAULT NULL")
        except pymysql.err.OperationalError:
            pass
        
        # 관리자 확정 관련 컬럼 추가 (마이그레이션)
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN admin_confirmed TINYINT(1) DEFAULT 0")
        except pymysql.err.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN confirmed_type VARCHAR(20) DEFAULT NULL")
        except pymysql.err.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN confirmed_at DATETIME DEFAULT NULL")
        except pymysql.err.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE ethics_logs ADD COLUMN confirmed_by INT DEFAULT NULL")
        except pymysql.err.OperationalError:
            pass
        
        # RAG 로그 테이블 생성 (마이그레이션)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ethics_rag_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                ethics_log_id BIGINT NOT NULL,
                similar_case_count INT DEFAULT 0,
                max_similarity DOUBLE DEFAULT NULL,
                original_immoral_score DOUBLE DEFAULT NULL,
                original_spam_score DOUBLE DEFAULT NULL,
                adjusted_immoral_score DOUBLE DEFAULT NULL,
                adjusted_spam_score DOUBLE DEFAULT NULL,
                adjustment_weight DOUBLE DEFAULT NULL,
                confidence_boost DOUBLE DEFAULT NULL,
                adjustment_method VARCHAR(50) DEFAULT 'similarity_based',
                similar_cases JSON DEFAULT NULL,
                rag_response_time DOUBLE DEFAULT NULL,
                vector_search_time DOUBLE DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_rag_ethics_log 
                    FOREIGN KEY (ethics_log_id) 
                    REFERENCES ethics_logs(id) 
                    ON DELETE CASCADE,
                INDEX idx_rag_ethics_log (ethics_log_id),
                INDEX idx_rag_created_at (created_at DESC),
                INDEX idx_rag_similarity (max_similarity),
                INDEX idx_rag_case_count (similar_case_count)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        conn.close()
        
        print(f"[INFO] 데이터베이스 초기화 완료: {self.user}@{self.host}:{self.port}/{self.database}")
    
    def log_analysis(
        self,
        text: str,
        score: float = None,
        confidence: float = None,
        spam: float = None,
        types: List[str] = None,
        spam_confidence: float = None,
        ip_address: str = None,
        user_agent: str = None,
        response_time: float = None,
        rag_applied: bool = False,
        auto_blocked: bool = False,
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
            rag_applied: RAG 보정 적용 여부
            auto_blocked: 자동 차단 여부 (LLM 미사용)
        
        Returns:
            생성된 로그 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        types_json = json.dumps(types if types is not None else [], ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO ethics_logs 
            (text, score, confidence, spam, spam_confidence, types, ip_address, user_agent, response_time, rag_applied, auto_blocked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            text,
            score,
            confidence,
            spam,
            spam_confidence,
            types_json,
            ip_address,
            user_agent,
            response_time,
            1 if rag_applied else 0,
            1 if auto_blocked else 0
        ))
        
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
        
        query = "SELECT * FROM ethics_logs WHERE 1=1"
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
            SELECT COUNT(*) as count FROM ethics_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        total_count = cursor.fetchone()['count']
        
        # 평균 점수
        cursor.execute("""
            SELECT 
                AVG(score) as avg_score,
                AVG(confidence) as avg_confidence,
                AVG(spam) as avg_spam
            FROM ethics_logs
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        avgs = cursor.fetchone()
        
        # 고위험 건수 (score >= 70)
        cursor.execute("""
            SELECT COUNT(*) as count FROM ethics_logs
            WHERE score >= 70
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        high_risk_count = cursor.fetchone()['count']
        
        # 스팸 건수 (spam >= 60)
        cursor.execute("""
            SELECT COUNT(*) as count FROM ethics_logs
            WHERE spam >= 60
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        spam_count = cursor.fetchone()['count']

        # RAG 보정 적용 건수
        cursor.execute("""
            SELECT COUNT(*) as count FROM ethics_logs
            WHERE rag_applied = 1
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        rag_applied_count = cursor.fetchone()['count']
        
        # 즉시 차단 건수 (auto_blocked = 1)
        cursor.execute("""
            SELECT COUNT(*) as count FROM ethics_logs
            WHERE auto_blocked = 1
            AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        auto_blocked_count = cursor.fetchone()['count']
        
        # 일별 통계
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count,
                AVG(score) as avg_score
            FROM ethics_logs
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

        # RAG 벡터DB 통계
        try:
            from ethics.ethics_vector_db import get_client, get_collection_stats
            vector_client = get_client()
            rag_stats = get_collection_stats(vector_client)
        except Exception as rag_error:
            rag_stats = {
                'status': 'error',
                'error': str(rag_error)
            }

        return {
            'period_days': days,
            'total_count': total_count,
            'avg_score': round(avgs['avg_score'], 1) if avgs['avg_score'] else 0,
            'avg_confidence': round(avgs['avg_confidence'], 1) if avgs['avg_confidence'] else 0,
            'avg_spam': round(avgs['avg_spam'], 1) if avgs['avg_spam'] else 0,
            'high_risk_count': high_risk_count,
            'spam_count': spam_count,
            'rag_applied_count': rag_applied_count,
            'auto_blocked_count': auto_blocked_count,
            'daily_stats': daily_stats,
            'rag_stats': rag_stats
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
        
        cursor.execute("DELETE FROM ethics_logs WHERE id = %s", (log_id,))
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
            DELETE FROM ethics_logs
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
        
        cursor.execute("DELETE FROM ethics_logs")
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count
    
    def log_rag_details(
        self,
        ethics_log_id: int,
        similar_case_count: int,
        max_similarity: float,
        original_immoral_score: float,
        original_spam_score: float,
        adjusted_immoral_score: float,
        adjusted_spam_score: float,
        adjustment_weight: float,
        confidence_boost: float,
        similar_cases: List[Dict] = None,
        rag_response_time: float = None,
        vector_search_time: float = None,
        adjustment_method: str = 'similarity_based'
    ) -> int:
        """
        RAG 보정 상세 정보 저장
        
        Args:
            ethics_log_id: 연결된 ethics_logs의 ID
            similar_case_count: 검색된 유사 케이스 개수
            max_similarity: 최대 유사도 점수 (0-1)
            original_immoral_score: RAG 보정 전 비윤리 점수
            original_spam_score: RAG 보정 전 스팸 점수
            adjusted_immoral_score: RAG 보정 후 비윤리 점수
            adjusted_spam_score: RAG 보정 후 스팸 점수
            adjustment_weight: 보정 가중치 (0-1)
            confidence_boost: 신뢰도 증가량
            similar_cases: 유사 케이스 상세 정보
            rag_response_time: RAG 처리 시간 (초)
            vector_search_time: 벡터 검색 시간 (초)
            adjustment_method: 보정 방법
        
        Returns:
            생성된 RAG 로그 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        similar_cases_json = json.dumps(similar_cases, ensure_ascii=False) if similar_cases else None
        
        cursor.execute("""
            INSERT INTO ethics_rag_logs 
            (ethics_log_id, similar_case_count, max_similarity,
             original_immoral_score, original_spam_score,
             adjusted_immoral_score, adjusted_spam_score,
             adjustment_weight, confidence_boost,
             similar_cases, rag_response_time, vector_search_time,
             adjustment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            ethics_log_id, similar_case_count, max_similarity,
            original_immoral_score, original_spam_score,
            adjusted_immoral_score, adjusted_spam_score,
            adjustment_weight, confidence_boost,
            similar_cases_json, rag_response_time, vector_search_time,
            adjustment_method
        ))
        
        rag_log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return rag_log_id
    
    def get_rag_details(self, ethics_log_id: int) -> Optional[Dict]:
        """
        특정 로그의 RAG 상세 정보 조회
        
        Args:
            ethics_log_id: ethics_logs의 ID
        
        Returns:
            RAG 상세 정보 딕셔너리 또는 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ethics_rag_logs 
            WHERE ethics_log_id = %s
        """, (ethics_log_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        rag_details = dict(row)
        # JSON 파싱
        if rag_details.get('similar_cases'):
            try:
                rag_details['similar_cases'] = json.loads(rag_details['similar_cases'])
            except (json.JSONDecodeError, TypeError):
                rag_details['similar_cases'] = []
        
        return rag_details
    
    def get_logs_with_rag(
        self,
        limit: int = 100,
        offset: int = 0,
        min_score: float = None,
        max_score: float = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """
        로그 조회 (RAG 정보 포함)
        
        Args:
            limit: 최대 조회 개수
            offset: 시작 위치
            min_score: 최소 점수 필터
            max_score: 최대 점수 필터
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
        
        Returns:
            로그 리스트 (RAG 정보 포함)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                el.*,
                erl.id as rag_log_id,
                erl.similar_case_count,
                erl.max_similarity,
                erl.original_immoral_score,
                erl.original_spam_score,
                erl.adjusted_immoral_score,
                erl.adjusted_spam_score,
                erl.adjustment_weight,
                erl.confidence_boost,
                erl.adjustment_method,
                erl.similar_cases,
                erl.rag_response_time,
                erl.vector_search_time
            FROM ethics_logs el
            LEFT JOIN ethics_rag_logs erl ON el.id = erl.ethics_log_id
            WHERE 1=1
        """
        params = []
        
        if min_score is not None:
            query += " AND el.score >= %s"
            params.append(min_score)
        
        if max_score is not None:
            query += " AND el.score <= %s"
            params.append(max_score)
        
        if start_date:
            query += " AND DATE(el.created_at) >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(el.created_at) <= %s"
            params.append(end_date)
        
        query += " ORDER BY el.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            log = dict(row)
            
            # types JSON 파싱
            if log.get('types'):
                try:
                    log['types'] = json.loads(log['types'])
                except (json.JSONDecodeError, TypeError):
                    log['types'] = []
            
            # similar_cases JSON 파싱
            if log.get('similar_cases'):
                try:
                    log['similar_cases'] = json.loads(log['similar_cases'])
                except (json.JSONDecodeError, TypeError):
                    log['similar_cases'] = None
            
            # RAG 정보를 별도 객체로 그룹화
            if log.get('rag_log_id'):
                log['rag_details'] = {
                    'id': log.pop('rag_log_id'),
                    'similar_case_count': log.pop('similar_case_count'),
                    'max_similarity': log.pop('max_similarity'),
                    'original_immoral_score': log.pop('original_immoral_score'),
                    'original_spam_score': log.pop('original_spam_score'),
                    'adjusted_immoral_score': log.pop('adjusted_immoral_score'),
                    'adjusted_spam_score': log.pop('adjusted_spam_score'),
                    'adjustment_weight': log.pop('adjustment_weight'),
                    'confidence_boost': log.pop('confidence_boost'),
                    'adjustment_method': log.pop('adjustment_method'),
                    'similar_cases': log.pop('similar_cases'),
                    'rag_response_time': log.pop('rag_response_time'),
                    'vector_search_time': log.pop('vector_search_time')
                }
            else:
                # RAG 정보가 없으면 None으로 설정
                log['rag_details'] = None
                # 불필요한 필드 제거
                for key in ['rag_log_id', 'similar_case_count', 'max_similarity', 
                           'original_immoral_score', 'original_spam_score',
                           'adjusted_immoral_score', 'adjusted_spam_score',
                           'adjustment_weight', 'confidence_boost', 'adjustment_method',
                           'similar_cases', 'rag_response_time', 'vector_search_time']:
                    log.pop(key, None)
            
            logs.append(log)
        
        conn.close()
        return logs


# 전역 로거 인스턴스
db_logger = DatabaseLogger()

