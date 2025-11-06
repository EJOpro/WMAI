from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .chrun_models import Event, User, MonthlyMetrics, UserSegment
from .chrun_llm_service import llm_generator

class ChurnAnalyzer:
    """이탈 분석 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.min_sample_size = 50  # Uncertain 라벨 기준
        
        # 데이터베이스 타입 확인
        from .chrun_database import DATABASE_URL
        self.is_sqlite = DATABASE_URL.startswith('sqlite')
        self.is_mysql = 'mysql' in DATABASE_URL.lower()
    
    def _get_month_trunc(self, column_name: str = 'created_at') -> str:
        """데이터베이스별로 적절한 월 추출 SQL 반환"""
        if self.is_sqlite:
            return f"strftime('%Y-%m', {column_name})"
        elif self.is_mysql:
            return f"DATE_FORMAT({column_name}, '%Y-%m')"
        else:  # 기본값은 SQLite
            return f"strftime('%Y-%m', {column_name})"
    
    def _get_extract_dow(self, column_name: str) -> str:
        """데이터베이스별로 적절한 요일 추출 SQL 반환"""
        if self.is_sqlite:
            return f"CAST(strftime('%w', {column_name}) AS INTEGER)"
        elif self.is_mysql:
            return f"WEEKDAY({column_name})"
        else:  # 기본값은 SQLite
            return f"CAST(strftime('%w', {column_name}) AS INTEGER)"
    
    def _get_extract_hour(self, column_name: str) -> str:
        """데이터베이스별로 적절한 시간 추출 SQL 반환"""
        if self.is_sqlite:
            return f"CAST(strftime('%H', {column_name}) AS INTEGER)"
        elif self.is_mysql:
            return f"EXTRACT(HOUR FROM {column_name})"
        else:  # 기본값은 SQLite
            return f"CAST(strftime('%H', {column_name}) AS INTEGER)"
    
    def _get_month_subtract(self, column_name: str, months: int) -> str:
        """데이터베이스별로 적절한 월 빼기 SQL 반환"""
        if self.is_sqlite:
            return f"strftime('%Y-%m', datetime({column_name}, '-{months} months'))"
        elif self.is_mysql:
            return f"DATE_FORMAT(DATE_SUB({column_name}, INTERVAL {months} MONTH), '%Y-%m')"
        else:  # 기본값은 SQLite
            return f"strftime('%Y-%m', datetime({column_name}, '-{months} months'))"
    
    def _get_date_subtract_days(self, column_name: str, days: int) -> str:
        """데이터베이스별로 적절한 일수 빼기 SQL 반환"""
        if self.is_sqlite:
            return f"datetime({column_name}, '-{days} days')"
        elif self.is_mysql:
            return f"DATE_SUB({column_name}, INTERVAL {days} DAY)"
        else:  # 기본값은 SQLite
            return f"datetime({column_name}, '-{days} days')"
    
    def run_full_analysis(
        self, 
        start_month: str, 
        end_month: str,
        segments: Dict[str, bool] = None,
        inactivity_days: List[int] = [30, 60, 90],
        threshold: int = 1
    ) -> Dict:
        """전체 이탈 분석 실행"""
        
        if segments is None:
            segments = {"gender": False, "age_band": False, "channel": False}
        
        start_time = datetime.now()
        
        try:
            # 1. 기본 지표 계산
            metrics = self.get_monthly_metrics(end_month, threshold)
            
            # 2. 월별 트렌드
            months = self._generate_month_range(start_month, end_month)
            trends = self.get_churn_trends(months, threshold)
            
            # 3. 세그먼트 분석 (체크된 세그먼트만 분석)
            segment_analysis = {}
            if segments.get("gender", False):
                segment_analysis["gender"] = self._analyze_segment("gender", start_month, end_month)
            if segments.get("age_band", False):
                segment_analysis["age_band"] = self._analyze_segment("age_band", start_month, end_month)
            if segments.get("channel", False):
                segment_analysis["channel"] = self._analyze_segment("channel", start_month, end_month)
            if segments.get("combined", False):
                segment_analysis["combined"] = self._analyze_combined_segments(start_month, end_month)
            if segments.get("weekday_pattern", False):
                segment_analysis["weekday_pattern"] = self._analyze_weekday_pattern(start_month, end_month)
            if segments.get("time_pattern", False):
                segment_analysis["time_pattern"] = self._analyze_time_pattern(start_month, end_month)
            if segments.get("action_type", False):
                segment_analysis["action_type"] = self._analyze_action_type_segment(start_month, end_month)
            
            # 4. 장기 미접속 분석
            inactivity_analysis = self._analyze_inactivity(end_month, inactivity_days)
            
            # 5. 재활성 사용자 분석
            reactivation_analysis = self._analyze_reactivation(end_month)
            
            # 6. LLM 기반 인사이트 및 액션 생성
            llm_result = self._generate_llm_insights_and_actions({
                "start_month": start_month,
                "end_month": end_month,
                "metrics": metrics,
                "trends": trends,
                "segments": segment_analysis,
                "inactivity": inactivity_analysis,
                "reactivation": reactivation_analysis,
                "data_quality": self._check_data_quality(start_month, end_month),
                "config": {
                    "segments": segments
                }
            })
            
            insights = llm_result.get('insights', [])
            actions = llm_result.get('actions', [])
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "analysis_id": f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "start_month": start_month,
                    "end_month": end_month,
                    "segments": segments,
                    "inactivity_days": inactivity_days
                },
                "metrics": metrics,
                "trends": trends,
                "segments": segment_analysis,
                "inactivity": inactivity_analysis,
                "reactivation": reactivation_analysis,
                "insights": insights,
                "actions": actions,
                "data_quality": self._check_data_quality(start_month, end_month),
                "execution_time_seconds": execution_time
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[ERROR] 분석 실행 중 오류 발생: {e}")
            print(f"[ERROR] 상세 오류:\n{error_detail}")
            
            # 오류 발생 시에도 가능한 데이터로 LLM 인사이트 생성 시도
            try:
                # 최소한의 데이터로 LLM 호출
                llm_result = self._generate_llm_insights_and_actions({
                    "start_month": start_month,
                    "end_month": end_month,
                    "metrics": {},
                    "trends": {},
                    "segments": {},
                    "inactivity": {},
                    "reactivation": {},
                    "data_quality": {},
                    "config": {
                        "segments": segments if segments else {}
                    },
                    "error": str(e)
                })
                
                insights = llm_result.get('insights', [])
                actions = llm_result.get('actions', [])
            except Exception as llm_error:
                print(f"[ERROR] LLM 인사이트 생성도 실패: {llm_error}")
                insights = [
                    f"분석 중 오류가 발생했습니다: {str(e)}",
                    "데이터 범위나 형식을 확인해주세요.",
                    "오류 해결 후 다시 분석을 실행해주세요."
                ]
                actions = [
                    "분석 기간과 데이터 범위를 확인하세요.",
                    "데이터베이스 연결 상태를 확인하세요.",
                    "오류 로그를 확인하여 문제를 해결하세요."
                ]
            
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "execution_time_seconds": (datetime.now() - start_time).total_seconds(),
                "insights": insights,
                "actions": actions,
                "metrics": {},
                "trends": {},
                "segments": {},
                "data_quality": {}
            }
    
    def get_monthly_metrics(self, month: str, threshold: int = 1) -> Dict:
        """월별 주요 지표 계산"""
        
        current_month = month
        previous_month = self._get_previous_month(month)
        
        month_trunc = self._get_month_trunc('created_at')
        
        # SQL 쿼리로 효율적인 계산
        query = text(f"""
        WITH monthly_users AS (
            SELECT 
                {month_trunc} as month,
                user_hash,
                COUNT(*) as event_count
            FROM events 
            WHERE {month_trunc} IN (:prev_month, :curr_month)
            GROUP BY {month_trunc}, user_hash
            HAVING COUNT(*) >= :threshold
        ),
        current_active AS (
            SELECT user_hash FROM monthly_users 
            WHERE month = :curr_month
        ),
        previous_active AS (
            SELECT user_hash FROM monthly_users 
            WHERE month = :prev_month
        ),
        churned AS (
            SELECT p.user_hash 
            FROM previous_active p
            LEFT JOIN current_active c ON p.user_hash = c.user_hash
            WHERE c.user_hash IS NULL
        ),
        retained AS (
            SELECT p.user_hash
            FROM previous_active p
            INNER JOIN current_active c ON p.user_hash = c.user_hash
        )
        SELECT 
            (SELECT COUNT(*) FROM current_active) as current_active_users,
            (SELECT COUNT(*) FROM previous_active) as previous_active_users,
            (SELECT COUNT(*) FROM churned) as churned_users,
            (SELECT COUNT(*) FROM retained) as retained_users
        """)
        
        result = self.db.execute(query, {
            "curr_month": current_month,
            "prev_month": previous_month,
            "threshold": threshold
        }).fetchone()
        
        if not result:
            return {"error": "데이터를 찾을 수 없습니다."}
        
        # Decimal 타입을 int로 변환
        from decimal import Decimal
        def to_int(value):
            if isinstance(value, Decimal):
                return int(value)
            elif value is None:
                return 0
            else:
                return int(value)
        
        current_active = to_int(result.current_active_users)
        previous_active = to_int(result.previous_active_users)
        churned = to_int(result.churned_users)
        retained = to_int(result.retained_users)
        
        # 이탈률 계산
        churn_rate = (churned / previous_active * 100) if previous_active > 0 else 0
        retention_rate = (retained / previous_active * 100) if previous_active > 0 else 0
        
        # 재활성 사용자 계산
        reactivated_users = self._calculate_reactivated_users(current_month)
        
        # 장기 미접속 사용자 계산
        long_term_inactive = self._calculate_long_term_inactive(current_month, 90)
        
        return {
            "month": current_month,
            "active_users": current_active,
            "previous_active_users": previous_active,
            "churned_users": churned,
            "retained_users": retained,
            "churn_rate": round(churn_rate, 1),
            "retention_rate": round(retention_rate, 1),
            "reactivated_users": reactivated_users,
            "long_term_inactive": long_term_inactive,
            "month_over_month_change": {
                "active_users": current_active - previous_active,
                "churn_rate_change": churn_rate  # 이전 달과의 차이는 별도 계산 필요
            }
        }
    
    def get_churn_trends(self, months: List[str], threshold: int = 1) -> Dict:
        """월별 이탈률 트렌드"""
        
        trends = []
        
        for i in range(1, len(months)):
            current_month = months[i]
            
            metrics = self.get_monthly_metrics(current_month, threshold)
            
            trends.append({
                "month": current_month,
                "churn_rate": metrics.get("churn_rate", 0),
                "active_users": metrics.get("active_users", 0),
                "churned_users": metrics.get("churned_users", 0)
            })
        
        return {
            "months": months[1:],  # 첫 번째 월 제외
            "trends": trends
        }
    
    def get_segment_analysis(self, start_month: str, end_month: str, segments_config: Dict[str, bool] = None) -> Dict:
        """세그먼트별 이탈률 분석 - 선택된 세그먼트만 분석"""
        
        if segments_config is None:
            segments_config = {"channel": False, "action_type": False, "weekday_pattern": False, "time_pattern": False}
        
        segments = {}
        
        # 선택된 세그먼트만 분석
        if segments_config.get("channel", False):
            try:
                segments["channel"] = self._analyze_segment("channel", start_month, end_month)
            except Exception as e:
                print(f"⚠️ 세그먼트 channel 분석 실패: {e}")
                segments["channel"] = []
        
        if segments_config.get("action_type", False):
            try:
                segments["action_type"] = self._analyze_action_type_segment(start_month, end_month)
            except Exception as e:
                print(f"⚠️ 세그먼트 action_type 분석 실패: {e}")
                segments["action_type"] = []
        
        if segments_config.get("weekday_pattern", False):
            try:
                segments["weekday_pattern"] = self._analyze_weekday_pattern(start_month, end_month)
            except Exception as e:
                print(f"⚠️ 세그먼트 weekday_pattern 분석 실패: {e}")
                segments["weekday_pattern"] = []
        
        if segments_config.get("time_pattern", False):
            try:
                segments["time_pattern"] = self._analyze_time_pattern(start_month, end_month)
            except Exception as e:
                print(f"⚠️ 세그먼트 time_pattern 분석 실패: {e}")
                segments["time_pattern"] = []
        
        return segments
    
    def generate_monthly_report(
        self,
        month: str,
        threshold: int = 1,
        inactivity_days: Optional[List[int]] = None
    ) -> Dict:
        """단일 월에 대한 요약 리포트를 생성"""

        if inactivity_days is None:
            inactivity_days = [30, 60, 90]

        metrics = self.get_monthly_metrics(month, threshold)

        previous_month = self._get_previous_month(month)
        trends = self.get_churn_trends([previous_month, month], threshold)

        segments = {
            "channel": self._analyze_segment("channel", month, month),
        }

        inactivity = self._analyze_inactivity(month, inactivity_days)
        reactivation = self._analyze_reactivation(month)
        data_quality = self._check_data_quality(month, month)

        analysis_payload = {
            "start_month": previous_month,
            "end_month": month,
            "metrics": metrics,
            "trends": trends,
            "segments": segments,
            "inactivity": inactivity,
            "reactivation": reactivation,
            "data_quality": data_quality,
            "config": {
                "segments": {
                    "channel": True
                }
            }
        }

        llm_result = self._generate_llm_insights_and_actions(analysis_payload)

        latest_trend = trends.get("trends", [])[-1] if trends.get("trends") else None

        return {
            "month": month,
            "generated_at": datetime.now().isoformat(),
            "metrics": metrics,
            "trend": latest_trend,
            "trends": trends,
            "segments": segments,
            "inactivity": inactivity,
            "reactivation": reactivation,
            "data_quality": data_quality,
            "insights": llm_result.get("insights", []),
            "actions": llm_result.get("actions", []),
            "llm_metadata": llm_result.get("llm_metadata"),
        }

    def _analyze_segment(self, segment_type: str, start_month: str, end_month: str) -> List[Dict]:
        """특정 세그먼트 분석 - 분석 기간 전체의 모든 월 전환을 집계하여 이탈률 계산"""
        
        # 컬럼 존재 여부 확인 (실제 데이터베이스 스키마에 맞게)
        # Event 모델에는 user_hash, created_at, action, channel만 존재
        valid_segments = ["channel"]
        if segment_type not in valid_segments:
            # 존재하지 않는 세그먼트는 빈 배열 반환
            print(f"⚠️ 세그먼트 {segment_type}는 데이터베이스에 존재하지 않습니다. 사용 가능한 세그먼트: {valid_segments}")
            return []
        
        month_trunc = self._get_month_trunc('created_at')
        
        # MySQL의 경우 문자열 월을 DATE로 변환 후 빼기
        # SQLite에서는 문자열을 날짜로 변환 후 빼기
        if self.is_mysql:
            month_subtract = "DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(sm.month, '-01'), '%Y-%m-%d'), INTERVAL 1 MONTH), '%Y-%m')"
        elif self.is_sqlite:
            month_subtract = "strftime('%Y-%m', datetime(sm.month || '-01', '-1 month'))"
        else:
            month_subtract = self._get_month_subtract("STR_TO_DATE(CONCAT(sm.month, '-01'), '%Y-%m-%d')", 1)
        
        try:
            # 모든 세그먼트 타입에 대해 동일한 로직 사용
            # 채널의 경우: 사용자가 해당 채널을 사용했으면 (이벤트가 있으면) 그 채널로 카운트
            # 같은 사용자가 여러 채널을 사용하면 각 채널에 모두 포함됨 (독립적인 이탈률 계산)
            query = text(f"""
                WITH segment_monthly AS (
                    SELECT 
                        {segment_type} AS segment_value,
                        {month_trunc} AS month,
                        user_hash
                    FROM events 
                    WHERE {month_trunc} BETWEEN :start_month AND :end_month
                      AND {segment_type} IS NOT NULL 
                      AND {segment_type} != 'Unknown'
                    GROUP BY {segment_type}, {month_trunc}, user_hash
                ),
                segment_months AS (
                    SELECT DISTINCT segment_value, month FROM segment_monthly
                ),
                month_pairs AS (
                    SELECT 
                        sm.segment_value,
                        sm.month AS curr_month,
                        {month_subtract} AS prev_month
                    FROM segment_months sm
                    WHERE sm.month > :start_month
                ),
                prev_active AS (
                    SELECT 
                        mp.segment_value,
                        mp.curr_month,
                        COUNT(DISTINCT m.user_hash) AS previous_active
                    FROM month_pairs mp
                    LEFT JOIN segment_monthly m
                      ON m.segment_value = mp.segment_value AND m.month = mp.prev_month
                    GROUP BY mp.segment_value, mp.curr_month
                ),
                curr_active AS (
                    SELECT 
                        mp.segment_value,
                        mp.curr_month,
                        COUNT(DISTINCT m.user_hash) AS current_active
                    FROM month_pairs mp
                    LEFT JOIN segment_monthly m
                      ON m.segment_value = mp.segment_value AND m.month = mp.curr_month
                    GROUP BY mp.segment_value, mp.curr_month
                ),
                churned AS (
                    SELECT 
                        mp.segment_value,
                        mp.curr_month,
                        COUNT(DISTINCT pm.user_hash) AS churned_users
                    FROM month_pairs mp
                    LEFT JOIN segment_monthly pm
                      ON pm.segment_value = mp.segment_value AND pm.month = mp.prev_month
                    LEFT JOIN segment_monthly cm
                      ON cm.segment_value = mp.segment_value AND cm.month = mp.curr_month AND cm.user_hash = pm.user_hash
                    WHERE cm.user_hash IS NULL
                    GROUP BY mp.segment_value, mp.curr_month
                ),
                aggregated AS (
                    SELECT 
                        mp.segment_value,
                        SUM(COALESCE(pa.previous_active, 0)) AS previous_active_sum,
                        SUM(COALESCE(ca.current_active, 0)) AS current_active_sum,
                        SUM(COALESCE(ch.churned_users, 0)) AS churned_sum
                    FROM month_pairs mp
                    LEFT JOIN prev_active pa ON pa.segment_value = mp.segment_value AND pa.curr_month = mp.curr_month
                    LEFT JOIN curr_active ca ON ca.segment_value = mp.segment_value AND ca.curr_month = mp.curr_month
                    LEFT JOIN churned ch ON ch.segment_value = mp.segment_value AND ch.curr_month = mp.curr_month
                    GROUP BY mp.segment_value
                )
                SELECT 
                    segment_value,
                    current_active_sum AS current_active,
                    previous_active_sum AS previous_active,
                    churned_sum AS churned,
                    CASE 
                        WHEN previous_active_sum > 0 THEN ROUND((CAST(churned_sum AS FLOAT) / previous_active_sum * 100), 1)
                        ELSE 0 
                    END AS churn_rate,
                    CASE WHEN previous_active_sum < :min_sample THEN 1 ELSE 0 END AS is_uncertain
                FROM aggregated
                WHERE previous_active_sum > 0
                ORDER BY churn_rate DESC
                """)
            
            results = self.db.execute(query, {
                "start_month": f"{start_month}-01",
                "end_month": f"{end_month}-01",
                "min_sample": self.min_sample_size
            }).fetchall()
            
            from decimal import Decimal
            def convert_value(value):
                if isinstance(value, Decimal):
                    return float(value) if isinstance(value, Decimal) and value % 1 != 0 else int(value)
                return value
            
            return [
                {
                    "segment_value": row.segment_value,
                    "current_active": int(convert_value(row.current_active)),
                    "previous_active": int(convert_value(row.previous_active)),
                    "churned_users": int(convert_value(row.churned)),
                    "churn_rate": float(convert_value(row.churn_rate)),
                    "is_uncertain": bool(row.is_uncertain)
                }
                for row in results
            ]
        except Exception as e:
            # SQL 에러 발생 시 빈 배열 반환
            print(f"⚠️ 세그먼트 {segment_type} 분석 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _analyze_inactivity(self, month: str, days_list: List[int]) -> Dict:
        """장기 미접속 분석"""
        
        results = {}
        # 월의 마지막 날짜 계산 (실제 월의 일수 고려)
        from calendar import monthrange
        year, month_num = map(int, month.split('-'))
        last_day = monthrange(year, month_num)[1]  # 해당 월의 마지막 날짜
        month_end = f"{month}-{last_day:02d}"
        month_end_date = datetime.strptime(month_end, "%Y-%m-%d")
        
        for days in days_list:
            cutoff_date = month_end_date - timedelta(days=days)
            
            # 사용자 목록도 함께 반환
            query = text("""
            SELECT 
                user_hash,
                MAX(created_at) as last_activity
            FROM events
            GROUP BY user_hash
            HAVING MAX(created_at) < :cutoff_date
            ORDER BY last_activity ASC
            """)
            
            inactive_users_result = self.db.execute(query, {"cutoff_date": cutoff_date}).fetchall()
            
            from decimal import Decimal
            inactive_count = len(inactive_users_result)
            
            # 사용자 목록 생성 (user_hash와 마지막 활동일 포함)
            inactive_users_list = []
            for row in inactive_users_result:
                last_activity = row.last_activity
                if isinstance(last_activity, str):
                    last_activity = datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
                inactive_days = (month_end_date - last_activity).days
                inactive_users_list.append({
                    "user_hash": row.user_hash,
                    "last_activity": last_activity.isoformat() if isinstance(last_activity, datetime) else str(last_activity),
                    "inactive_days": inactive_days
                })
            
            results[f"inactive_{days}d"] = inactive_count
            results[f"inactive_{days}d_users"] = inactive_users_list
        
        return results
    
    def _analyze_reactivation(self, month: str, gap_days: int = 30) -> Dict:
        """재활성 사용자 분석"""
        
        # 월의 마지막 날짜 계산 (실제 월의 일수 고려)
        from calendar import monthrange
        year, month_num = map(int, month.split('-'))
        last_day = monthrange(year, month_num)[1]  # 해당 월의 마지막 날짜
        month_start = f"{month}-01"
        month_end = f"{month}-{last_day:02d}"
        
        # SQLite/MySQL 호환성을 위해 직접 날짜 계산
        if self.is_sqlite:
            date_subtract_sql = f"datetime(:month_start, '-{gap_days} days')"
        elif self.is_mysql:
            date_subtract_sql = f"DATE_SUB(:month_start, INTERVAL {gap_days} DAY)"
        else:
            date_subtract_sql = f"datetime(:month_start, '-{gap_days} days')"
        
        query = text(f"""
        WITH current_month_active AS (
            SELECT DISTINCT user_hash
            FROM events
            WHERE created_at >= :month_start AND created_at <= :month_end
        ),
        user_last_activity_before AS (
            SELECT 
                cma.user_hash,
                MAX(e.created_at) as last_activity_before
            FROM current_month_active cma
            LEFT JOIN events e ON cma.user_hash = e.user_hash 
                AND e.created_at < :month_start
            GROUP BY cma.user_hash
        )
        SELECT COUNT(*) as reactivated_count
        FROM user_last_activity_before
        WHERE last_activity_before IS NOT NULL
        AND last_activity_before < {date_subtract_sql}
        """)
        
        result = self.db.execute(query, {
            "month_start": month_start,
            "month_end": month_end,
            "gap_days": gap_days
        }).fetchone()
        
        from decimal import Decimal
        reactivated_count = result.reactivated_count if result else 0
        if isinstance(reactivated_count, Decimal):
            reactivated_count = int(reactivated_count)
        
        return {
            "reactivated_users": reactivated_count,
            "gap_days": gap_days
        }
    
    def _generate_insights(self, metrics: Dict, segments: Dict, trends: Dict) -> List[str]:
        """
        [DEPRECATED] 기존 하드코딩된 인사이트 생성 - LLM으로 대체됨
        이 함수는 더 이상 사용되지 않습니다.
        """
        
        insights = []
        
        # 1. 전체 이탈률 트렌드
        if trends.get("trends"):
            recent_trends = trends["trends"][-2:]  # 최근 2개월
            if len(recent_trends) >= 2:
                current_rate = recent_trends[-1]["churn_rate"]
                previous_rate = recent_trends[-2]["churn_rate"]
                change = current_rate - previous_rate
                
                if change > 2:
                    insights.append(f"이탈률이 전월 대비 {change:.1f}%p 상승하여 주의가 필요합니다.")
                elif change < -2:
                    insights.append(f"이탈률이 전월 대비 {abs(change):.1f}%p 개선되었습니다.")
        
        # 2. 세그먼트별 인사이트
        for segment_type, segment_data in segments.items():
            if segment_data:
                # 가장 높은 이탈률 세그먼트
                highest_churn = max(segment_data, key=lambda x: x["churn_rate"])
                lowest_churn = min(segment_data, key=lambda x: x["churn_rate"])
                
                if highest_churn["churn_rate"] - lowest_churn["churn_rate"] > 5:
                    segment_names = {
                        "gender": {"M": "남성", "F": "여성"},
                        "age_band": {"20s": "20대", "30s": "30대", "40s": "40대", "50s": "50대"},
                        "channel": {"web": "웹", "app": "앱"}
                    }
                    
                    high_name = segment_names.get(segment_type, {}).get(highest_churn["segment_value"], highest_churn["segment_value"])
                    low_name = segment_names.get(segment_type, {}).get(lowest_churn["segment_value"], lowest_churn["segment_value"])
                    
                    diff = highest_churn["churn_rate"] - lowest_churn["churn_rate"]
                    uncertain_note = " (모수 부족으로 Uncertain 표기)" if highest_churn["is_uncertain"] else ""
                    
                    insights.append(f"{high_name} 사용자의 이탈률이 {low_name} 대비 {diff:.1f}%p 높습니다{uncertain_note}.")
        
        # 3. 장기 미접속 인사이트
        if metrics.get("long_term_inactive", 0) > 0:
            total_users = metrics.get("active_users", 0) + metrics.get("long_term_inactive", 0)
            if total_users > 0:
                inactive_ratio = metrics["long_term_inactive"] / total_users * 100
                if inactive_ratio > 15:
                    insights.append(f"90일+ 장기 미접속 사용자가 전체의 {inactive_ratio:.1f}%로 높은 수준입니다.")
        
        return insights[:3]  # Top 3만 반환
    
    def _generate_actions(self, insights: List[str], segments: Dict) -> List[str]:
        """
        [DEPRECATED] 기존 하드코딩된 액션 생성 - LLM으로 대체됨
        이 함수는 더 이상 사용되지 않습니다.
        """
        
        actions = []
        
        # 세그먼트별 액션
        for segment_type, segment_data in segments.items():
            if segment_data:
                highest_churn = max(segment_data, key=lambda x: x["churn_rate"])
                
                if highest_churn["churn_rate"] > 20:  # 20% 이상 이탈률
                    if segment_type == "gender" and highest_churn["segment_value"] == "F":
                        actions.append("여성 사용자 대상 맞춤형 콘텐츠 및 커뮤니티 활동 강화")
                    elif segment_type == "age_band" and highest_churn["segment_value"] in ["50s", "60s"]:
                        actions.append("50대 이상 사용자를 위한 사용성 개선 및 신규 가이드 제공")
                    elif segment_type == "channel" and highest_churn["segment_value"] == "app":
                        actions.append("모바일 앱 사용자 경험 개선 및 푸시 알림 최적화")
        
        # 일반적인 액션
        actions.append("장기 미접속자 대상 복귀 유도 캠페인 및 개인화된 콘텐츠 추천")
        
        return actions[:3]  # Top 3만 반환
    
    def _check_data_quality(self, start_month: str, end_month: str) -> Dict:
        """데이터 품질 체크"""
        
        query = text(f"""
        SELECT 
            COUNT(*) as total_events,
            COUNT(CASE WHEN user_hash IS NOT NULL AND created_at IS NOT NULL AND action IS NOT NULL THEN 1 END) as valid_events,
            COUNT(CASE WHEN channel = 'Unknown' THEN 1 END) as unknown_values,
            COUNT(DISTINCT user_hash) as unique_users
        FROM events
        WHERE {self._get_month_trunc('created_at')} BETWEEN :start_month AND :end_month
        """)
        
        result = self.db.execute(query, {
            "start_month": f"{start_month}-01",
            "end_month": f"{end_month}-01"
        }).fetchone()
        
        if not result:
            return {"error": "데이터 품질 체크 실패"}
        
        from decimal import Decimal
        def to_int(value):
            if isinstance(value, Decimal):
                return int(value)
            elif value is None:
                return 0
            else:
                return int(value)
        
        total = to_int(result.total_events)
        valid = to_int(result.valid_events)
        unknown = to_int(result.unknown_values)
        unique_users = to_int(result.unique_users)
        
        return {
            "total_events": total,
            "valid_events": valid,
            "invalid_events": total - valid,
            "unknown_values": unknown,
            "unique_users": unique_users,
            "data_completeness": round((valid / total * 100), 1) if total > 0 else 0,
            "unknown_ratio": round((unknown / total * 100), 1) if total > 0 else 0
        }
    
    # 유틸리티 메서드들
    def _get_previous_month(self, month: str) -> str:
        """이전 월 계산"""
        year, month_num = map(int, month.split('-'))
        if month_num == 1:
            return f"{year-1}-12"
        else:
            return f"{year}-{month_num-1:02d}"
    
    def _generate_month_range(self, start_month: str, end_month: str) -> List[str]:
        """월 범위 생성"""
        start_year, start_month_num = map(int, start_month.split('-'))
        end_year, end_month_num = map(int, end_month.split('-'))
        
        months = []
        current_year, current_month = start_year, start_month_num
        
        while (current_year, current_month) <= (end_year, end_month_num):
            months.append(f"{current_year}-{current_month:02d}")
            
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        return months
    
    def _calculate_reactivated_users(self, month: str, gap_days: int = 30) -> int:
        """재활성 사용자 수 계산"""
        reactivation_data = self._analyze_reactivation(month, gap_days)
        return reactivation_data.get("reactivated_users", 0)
    
    def _calculate_long_term_inactive(self, month: str, days: int) -> int:
        """장기 미접속 사용자 수 계산"""
        inactivity_data = self._analyze_inactivity(month, [days])
        return inactivity_data.get(f"inactive_{days}d", 0)
    
    def _generate_llm_insights_and_actions(self, analysis_data: Dict) -> Dict:
        """LLM을 활용한 인사이트 및 권장 액션 생성"""
        print(f"[INFO] LLM 인사이트 생성 시작 - 분석 기간: {analysis_data.get('start_month')} ~ {analysis_data.get('end_month')}")
        try:
            # LLM 서비스를 통해 인사이트 생성
            print(f"[INFO] llm_generator.generate_insights_and_actions 호출 중...")
            result = llm_generator.generate_insights_and_actions(analysis_data)
            
            print(f"[INFO] LLM 결과 수신 - generated_by: {result.get('generated_by')}, insights: {len(result.get('insights', []))}개, actions: {len(result.get('actions', []))}개")
            
            # LLM 결과에 메타데이터 추가
            result['llm_metadata'] = {
                'model_used': 'gpt-4o-mini',
                'generation_method': result.get('generated_by', 'llm'),
                'timestamp': result.get('timestamp'),
                'fallback_used': result.get('generated_by') in ['fallback', 'basic_analysis', 'no_api_key']
            }
            
            return result
            
        except Exception as e:
            # LLM 실패 시 간단한 안내 메시지만 표시
            import traceback
            error_detail = traceback.format_exc()
            print(f"[ERROR] LLM 인사이트 생성 실패: {e}")
            print(f"[ERROR] 상세 오류:\n{error_detail}")
            
            return {
                'insights': [
                    "AI 분석을 위해 OpenAI API 키가 필요합니다.",
                    "설정 완료 후 더 정확하고 상세한 인사이트를 제공받을 수 있습니다.",
                    "현재는 기본 분석 결과만 표시됩니다."
                ],
                'actions': [
                    "OpenAI API 키를 설정하여 AI 기반 권장 액션을 활성화하세요.",
                    "LLM_INTEGRATION_GUIDE.md 문서를 참조하여 설정을 완료하세요.",
                    "API 키 설정 후 서버를 재시작하면 AI 분석이 활성화됩니다."
                ],
                'generated_by': 'no_api_key',
                'timestamp': datetime.now().isoformat(),
                'llm_metadata': {
                    'model_used': None,
                    'generation_method': 'no_api_key',
                    'fallback_used': True,
                    'error': str(e),
                    'setup_required': True
                }
            }
    
    def _analyze_combined_segments(self, start_month: str, end_month: str) -> List[Dict]:
        """복합 세그먼트 분석 (성별×연령×채널) - 현재 데이터베이스에 gender, age_band 컬럼이 없으므로 빈 배열 반환"""
        
        # Event 모델에는 gender, age_band 컬럼이 없으므로 복합 세그먼트 분석 불가
        print("⚠️ 복합 세그먼트 분석: gender, age_band 컬럼이 데이터베이스에 존재하지 않습니다.")
        return []
        
        # 아래 코드는 gender, age_band 컬럼이 있을 때 사용
        # month_trunc = self._get_month_trunc('created_at')
        # month_subtract = self._get_month_subtract('sm.month', 1)
        # 
        # query = text(f"""
        # WITH segment_monthly AS (
        #     SELECT 
        #         gender || '/' || age_band || '/' || channel AS segment_value,
        #         {month_trunc} AS month,
        #         user_hash
        #     FROM events 
        #     WHERE {month_trunc} BETWEEN :start_month AND :end_month
        #       AND gender IS NOT NULL 
        #       AND age_band IS NOT NULL 
        #       AND channel IS NOT NULL
        #       AND gender != 'Unknown'
        #       AND age_band != 'Unknown'
        #       AND channel != 'Unknown'
        #     GROUP BY gender, age_band, channel, {month_trunc}, user_hash
        # ),
        # segment_months AS (
        #     SELECT DISTINCT segment_value, month FROM segment_monthly
        # ),
        # month_pairs AS (
        #     SELECT 
        #         sm.segment_value,
        #         sm.month AS curr_month,
        #         {month_subtract} AS prev_month
        #     FROM segment_months sm
        #     WHERE sm.month > :start_month
        # ),
        # prev_active AS (
        #     SELECT 
        #         mp.segment_value,
        #         mp.curr_month,
        #         COUNT(DISTINCT m.user_hash) AS previous_active
        #     FROM month_pairs mp
        #     LEFT JOIN segment_monthly m
        #       ON m.segment_value = mp.segment_value AND m.month = mp.prev_month
        #     GROUP BY mp.segment_value, mp.curr_month
        # ),
        # curr_active AS (
        #     SELECT 
        #         mp.segment_value,
        #         mp.curr_month,
        #         COUNT(DISTINCT m.user_hash) AS current_active
        #     FROM month_pairs mp
        #     LEFT JOIN segment_monthly m
        #       ON m.segment_value = mp.segment_value AND m.month = mp.curr_month
        #     GROUP BY mp.segment_value, mp.curr_month
        # ),
        # churned AS (
        #     SELECT 
        #         mp.segment_value,
        #         mp.curr_month,
        #         COUNT(DISTINCT pm.user_hash) AS churned_users
        #     FROM month_pairs mp
        #     LEFT JOIN segment_monthly pm
        #       ON pm.segment_value = mp.segment_value AND pm.month = mp.prev_month
        #     LEFT JOIN segment_monthly cm
        #       ON cm.segment_value = mp.segment_value AND cm.month = mp.curr_month AND cm.user_hash = pm.user_hash
        #     WHERE cm.user_hash IS NULL
        #     GROUP BY mp.segment_value, mp.curr_month
        # ),
        # aggregated AS (
        #     SELECT 
        #         mp.segment_value,
        #         SUM(COALESCE(pa.previous_active, 0)) AS previous_active_sum,
        #         SUM(COALESCE(ca.current_active, 0)) AS current_active_sum,
        #         SUM(COALESCE(ch.churned_users, 0)) AS churned_sum
        #     FROM month_pairs mp
        #     LEFT JOIN prev_active pa ON pa.segment_value = mp.segment_value AND pa.curr_month = mp.curr_month
        #     LEFT JOIN curr_active ca ON ca.segment_value = mp.segment_value AND ca.curr_month = mp.curr_month
        #     LEFT JOIN churned ch ON ch.segment_value = mp.segment_value AND ch.curr_month = mp.curr_month
        #     GROUP BY mp.segment_value
        # )
        # SELECT 
        #     segment_value,
        #     current_active_sum AS current_active,
        #     previous_active_sum AS previous_active,
        #     churned_sum AS churned,
        #     CASE 
        #         WHEN previous_active_sum > 0 THEN ROUND((CAST(churned_sum AS FLOAT) / previous_active_sum * 100), 1)
        #         ELSE 0 
        #     END AS churn_rate,
        #     CASE WHEN previous_active_sum < :min_sample THEN true ELSE false END AS is_uncertain
        # FROM aggregated
        # WHERE previous_active_sum > 0
        # ORDER BY churn_rate DESC
        # """)
        # 
        # results = self.db.execute(query, {
        #     "start_month": f"{start_month}-01",
        #     "end_month": f"{end_month}-01",
        #     "min_sample": self.min_sample_size
        # }).fetchall()
        # 
        # return [
        #     {
        #         "segment_value": row.segment_value,
        #         "current_active": row.current_active,
        #         "previous_active": row.previous_active,
        #         "churned_users": row.churned,
        #         "churn_rate": row.churn_rate,
        #         "is_uncertain": row.is_uncertain
        #     }
        #     for row in results
        # ]
    
    def _analyze_weekday_pattern(self, start_month: str, end_month: str) -> List[Dict]:
        """활동 요일 패턴 세그먼트 분석"""
        
        month_trunc = self._get_month_trunc('created_at')
        extract_dow = self._get_extract_dow('created_at')
        
        # MySQL의 경우 문자열 월을 DATE로 변환 후 빼기
        # SQLite에서는 문자열을 날짜로 변환 후 빼기
        if self.is_mysql:
            month_subtract = "DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(us.month, '-01'), '%Y-%m-%d'), INTERVAL 1 MONTH), '%Y-%m')"
        elif self.is_sqlite:
            month_subtract = "strftime('%Y-%m', datetime(us.month || '-01', '-1 month'))"
        else:
            month_subtract = self._get_month_subtract('us.month', 1)
        
        query = text(f"""
            WITH user_weekday_stats AS (
                SELECT 
                    user_hash,
                    {month_trunc} AS month,
                    COUNT(CASE WHEN {extract_dow} BETWEEN 1 AND 5 THEN 1 END) AS weekday_count,
                    COUNT(CASE WHEN {extract_dow} IN (0, 6) THEN 1 END) AS weekend_count,
                    COUNT(*) AS total_count
            FROM events
            WHERE {month_trunc} BETWEEN :start_month AND :end_month
            GROUP BY user_hash, {month_trunc}
        ),
        user_segments AS (
            SELECT 
                user_hash,
                month,
                CASE 
                    WHEN CAST(weekday_count AS FLOAT) / NULLIF(total_count, 0) >= 0.7 THEN '평일주력'
                    WHEN CAST(weekend_count AS FLOAT) / NULLIF(total_count, 0) >= 0.5 THEN '주말주력'
                    WHEN weekday_count = total_count THEN '평일만'
                    WHEN weekend_count = total_count THEN '주말만'
                    ELSE '혼합'
                END AS segment_value
            FROM user_weekday_stats
        ),
        month_pairs AS (
            SELECT DISTINCT
                us.segment_value,
                us.month AS curr_month,
                {month_subtract} AS prev_month
            FROM user_segments us
            WHERE us.month > :start_month
        ),
        aggregated AS (
            SELECT 
                mp.segment_value,
                COUNT(DISTINCT CASE WHEN ps.month = mp.prev_month THEN ps.user_hash END) AS previous_active,
                COUNT(DISTINCT CASE WHEN cs.month = mp.curr_month THEN cs.user_hash END) AS current_active,
                COUNT(DISTINCT CASE 
                    WHEN ps.month = mp.prev_month 
                    AND NOT EXISTS (
                        SELECT 1 FROM user_segments cs2 
                        WHERE cs2.user_hash = ps.user_hash 
                        AND cs2.month = mp.curr_month
                    )
                    THEN ps.user_hash 
                END) AS churned_users
            FROM month_pairs mp
            LEFT JOIN user_segments ps ON ps.segment_value = mp.segment_value AND ps.month = mp.prev_month
            LEFT JOIN user_segments cs ON cs.segment_value = mp.segment_value AND cs.month = mp.curr_month
            GROUP BY mp.segment_value
        )
        SELECT 
            segment_value,
            current_active,
            previous_active,
            churned_users,
            CASE 
                WHEN previous_active > 0 THEN ROUND((CAST(churned_users AS FLOAT) / previous_active * 100), 1)
                ELSE 0 
            END AS churn_rate,
            CASE WHEN previous_active < :min_sample THEN true ELSE false END AS is_uncertain
        FROM aggregated
        WHERE previous_active > 0
        ORDER BY churn_rate DESC
        """)
        
        results = self.db.execute(query, {
            "start_month": f"{start_month}-01",
            "end_month": f"{end_month}-01",
            "min_sample": self.min_sample_size
        }).fetchall()
        
        from decimal import Decimal
        def convert_value(value):
            if isinstance(value, Decimal):
                return float(value) if isinstance(value, Decimal) and value % 1 != 0 else int(value)
            return value
        
        return [
            {
                "segment_value": row.segment_value,
                "current_active": int(convert_value(row.current_active)),
                "previous_active": int(convert_value(row.previous_active)),
                "churned_users": int(convert_value(row.churned_users)),
                "churn_rate": float(convert_value(row.churn_rate)),
                "is_uncertain": bool(row.is_uncertain)
            }
            for row in results
        ]
    
    def _analyze_time_pattern(self, start_month: str, end_month: str) -> List[Dict]:
        """활동 시간대 세그먼트 분석"""
        
        month_trunc = self._get_month_trunc('created_at')
        extract_hour = self._get_extract_hour('created_at')
        
        # MySQL의 경우 문자열 월을 DATE로 변환 후 빼기
        # SQLite에서는 문자열을 날짜로 변환 후 빼기
        if self.is_mysql:
            month_subtract = "DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(us.month, '-01'), '%Y-%m-%d'), INTERVAL 1 MONTH), '%Y-%m')"
        elif self.is_sqlite:
            month_subtract = "strftime('%Y-%m', datetime(us.month || '-01', '-1 month'))"
        else:
            month_subtract = self._get_month_subtract('us.month', 1)
        
        query = text(f"""
        WITH user_hour_stats AS (
            SELECT 
                user_hash,
                {month_trunc} AS month,
                COUNT(CASE WHEN {extract_hour} BETWEEN 6 AND 11 THEN 1 END) AS morning_count,
                COUNT(CASE WHEN {extract_hour} BETWEEN 12 AND 17 THEN 1 END) AS afternoon_count,
                COUNT(CASE WHEN {extract_hour} BETWEEN 18 AND 23 THEN 1 END) AS evening_count,
                COUNT(CASE WHEN {extract_hour} BETWEEN 0 AND 5 THEN 1 END) AS night_count,
                COUNT(*) AS total_count
            FROM events
            WHERE {month_trunc} BETWEEN :start_month AND :end_month
            GROUP BY user_hash, {month_trunc}
        ),
        user_segments AS (
            SELECT 
                user_hash,
                month,
                CASE 
                    WHEN morning_count >= afternoon_count AND morning_count >= evening_count AND morning_count >= night_count
                    THEN '오전'
                    WHEN afternoon_count >= morning_count AND afternoon_count >= evening_count AND afternoon_count >= night_count
                    THEN '오후'
                    WHEN evening_count >= morning_count AND evening_count >= afternoon_count AND evening_count >= night_count
                    THEN '저녁'
                    WHEN night_count >= morning_count AND night_count >= afternoon_count AND night_count >= evening_count
                    THEN '새벽'
                    ELSE '혼합'
                END AS segment_value
            FROM user_hour_stats
        ),
        month_pairs AS (
            SELECT DISTINCT
                us.segment_value,
                us.month AS curr_month,
                {month_subtract} AS prev_month
            FROM user_segments us
            WHERE us.month > :start_month
        ),
        aggregated AS (
            SELECT 
                mp.segment_value,
                COUNT(DISTINCT CASE WHEN ps.month = mp.prev_month THEN ps.user_hash END) AS previous_active,
                COUNT(DISTINCT CASE WHEN cs.month = mp.curr_month THEN cs.user_hash END) AS current_active,
                COUNT(DISTINCT CASE 
                    WHEN ps.month = mp.prev_month 
                    AND NOT EXISTS (
                        SELECT 1 FROM user_segments cs2 
                        WHERE cs2.user_hash = ps.user_hash 
                        AND cs2.month = mp.curr_month
                    )
                    THEN ps.user_hash 
                END) AS churned_users
            FROM month_pairs mp
            LEFT JOIN user_segments ps ON ps.segment_value = mp.segment_value AND ps.month = mp.prev_month
            LEFT JOIN user_segments cs ON cs.segment_value = mp.segment_value AND cs.month = mp.curr_month
            GROUP BY mp.segment_value
        )
        SELECT 
            segment_value,
            current_active,
            previous_active,
            churned_users,
            CASE 
                WHEN previous_active > 0 THEN ROUND((CAST(churned_users AS FLOAT) / previous_active * 100), 1)
                ELSE 0 
            END AS churn_rate,
            CASE WHEN previous_active < :min_sample THEN true ELSE false END AS is_uncertain
        FROM aggregated
        WHERE previous_active > 0
        ORDER BY churn_rate DESC
        """)
        
        results = self.db.execute(query, {
            "start_month": f"{start_month}-01",
            "end_month": f"{end_month}-01",
            "min_sample": self.min_sample_size
        }).fetchall()
        
        from decimal import Decimal
        def convert_value(value):
            if isinstance(value, Decimal):
                return float(value) if isinstance(value, Decimal) and value % 1 != 0 else int(value)
            return value
        
        return [
            {
                "segment_value": row.segment_value,
                "current_active": int(convert_value(row.current_active)),
                "previous_active": int(convert_value(row.previous_active)),
                "churned_users": int(convert_value(row.churned_users)),
                "churn_rate": float(convert_value(row.churn_rate)),
                "is_uncertain": bool(row.is_uncertain)
            }
            for row in results
        ]
    
    def get_detailed_verification_report(self, month: str, threshold: int = 1) -> Dict:
        """계산 과정을 상세히 보여주는 검증 리포트 생성"""
        
        current_month = month
        previous_month = self._get_previous_month(month)
        month_trunc = self._get_month_trunc('created_at')
        
        # 1. 월별 사용자별 이벤트 수 집계
        # GROUP_CONCAT은 SQLite 전용이므로, MySQL에서는 GROUP_CONCAT 사용
        if self.is_sqlite:
            concat_func = "GROUP_CONCAT(DISTINCT action)"
        elif self.is_mysql:
            concat_func = "GROUP_CONCAT(DISTINCT action SEPARATOR ',')"
        else:
            concat_func = "GROUP_CONCAT(DISTINCT action)"
        
        query_users = text(f"""
        SELECT 
            {month_trunc} as month,
            user_hash,
            COUNT(*) as event_count,
            {concat_func} as actions
        FROM events 
        WHERE {month_trunc} IN (:prev_month, :curr_month)
        GROUP BY {month_trunc}, user_hash
        ORDER BY {month_trunc}, user_hash
        """)
        
        users_detail = self.db.execute(query_users, {
            "curr_month": current_month,
            "prev_month": previous_month
        }).fetchall()
        
        # 2. 이전월 활성 사용자 목록
        query_prev_active = text(f"""
        SELECT DISTINCT user_hash
        FROM events
        WHERE {month_trunc} = :prev_month
        GROUP BY user_hash
        HAVING COUNT(*) >= :threshold
        """)
        
        prev_active_users = [row.user_hash for row in self.db.execute(query_prev_active, {
            "prev_month": previous_month,
            "threshold": threshold
        }).fetchall()]
        
        # 3. 현재월 활성 사용자 목록
        query_curr_active = text(f"""
        SELECT DISTINCT user_hash
        FROM events
        WHERE {month_trunc} = :curr_month
        GROUP BY user_hash
        HAVING COUNT(*) >= :threshold
        """)
        
        curr_active_users = [row.user_hash for row in self.db.execute(query_curr_active, {
            "curr_month": current_month,
            "threshold": threshold
        }).fetchall()]
        
        # 4. 이탈자 계산 (이전월에는 있었지만 현재월에는 없는 사용자)
        churned_users = [user for user in prev_active_users if user not in curr_active_users]
        
        # 5. 유지자 계산 (두 월 모두에 있는 사용자)
        retained_users = [user for user in prev_active_users if user in curr_active_users]
        
        # 6. 재활성 사용자 계산 (이전월에는 없었지만 현재월에는 있는 사용자)
        reactivated_users = [user for user in curr_active_users if user not in prev_active_users]
        
        # 7. 각 사용자의 상세 이벤트 정보
        user_events_detail = {}
        for row in users_detail:
            month_key = row.month
            user_key = row.user_hash
            if user_key not in user_events_detail:
                user_events_detail[user_key] = {}
            user_events_detail[user_key][month_key] = {
                "event_count": row.event_count,
                "actions": row.actions.split(',') if row.actions else []
            }
        
        # 8. 계산 결과 요약
        churn_rate = (len(churned_users) / len(prev_active_users) * 100) if prev_active_users else 0
        
        return {
            "report_type": "verification",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "month": current_month,
                "previous_month": previous_month,
                "threshold": threshold
            },
            "summary": {
                "previous_active_count": len(prev_active_users),
                "current_active_count": len(curr_active_users),
                "churned_count": len(churned_users),
                "retained_count": len(retained_users),
                "reactivated_count": len(reactivated_users),
                "churn_rate": round(churn_rate, 1),
                "retention_rate": round((len(retained_users) / len(prev_active_users) * 100) if prev_active_users else 0, 1)
            },
            "user_lists": {
                "previous_active_users": prev_active_users,
                "current_active_users": curr_active_users,
                "churned_users": churned_users,
                "retained_users": retained_users,
                "reactivated_users": reactivated_users
            },
            "user_events_detail": user_events_detail,
            "calculation_steps": {
                "step1": f"이전월({previous_month}) 활성 사용자: {len(prev_active_users)}명 (이벤트 {threshold}개 이상)",
                "step2": f"현재월({current_month}) 활성 사용자: {len(curr_active_users)}명 (이벤트 {threshold}개 이상)",
                "step3": f"이탈자: 이전월에만 있는 사용자 = {len(churned_users)}명",
                "step4": f"유지자: 두 월 모두 있는 사용자 = {len(retained_users)}명",
                "step5": f"재활성: 현재월에만 있는 사용자 = {len(reactivated_users)}명",
                "step6": f"이탈률 = (이탈자 {len(churned_users)} / 이전월 활성 {len(prev_active_users)}) × 100 = {round(churn_rate, 1)}%"
            }
        }
    
    def _analyze_action_type_segment(self, start_month: str, end_month: str) -> List[Dict]:
        """이벤트 타입별 세그먼트 분석"""
        
        month_trunc = self._get_month_trunc('created_at')
        
        # MySQL의 경우 문자열 월을 DATE로 변환 후 빼기
        # SQLite에서는 문자열을 날짜로 변환 후 빼기
        if self.is_mysql:
            month_subtract = "DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(us.month, '-01'), '%Y-%m-%d'), INTERVAL 1 MONTH), '%Y-%m')"
        elif self.is_sqlite:
            month_subtract = "strftime('%Y-%m', datetime(us.month || '-01', '-1 month'))"
        else:
            month_subtract = self._get_month_subtract('us.month', 1)
        
        query = text(f"""
        WITH user_action_stats AS (
            SELECT 
                user_hash,
                {month_trunc} AS month,
                COUNT(CASE WHEN action = 'view' THEN 1 END) AS view_count,
                COUNT(CASE WHEN action = 'login' THEN 1 END) AS login_count,
                COUNT(CASE WHEN action = 'comment' THEN 1 END) AS comment_count,
                COUNT(CASE WHEN action = 'like' THEN 1 END) AS like_count,
                COUNT(CASE WHEN action = 'post' THEN 1 END) AS post_count,
                COUNT(*) AS total_count
            FROM events
            WHERE {month_trunc} BETWEEN :start_month AND :end_month
            GROUP BY user_hash, {month_trunc}
        ),
        user_segments AS (
            SELECT 
                user_hash,
                month,
                CASE 
                    WHEN view_count >= login_count AND view_count >= comment_count AND view_count >= like_count AND view_count >= post_count
                    THEN 'view'
                    WHEN login_count >= view_count AND login_count >= comment_count AND login_count >= like_count AND login_count >= post_count
                    THEN 'login'
                    WHEN comment_count >= view_count AND comment_count >= login_count AND comment_count >= like_count AND comment_count >= post_count
                    THEN 'comment'
                    WHEN like_count >= view_count AND like_count >= login_count AND like_count >= comment_count AND like_count >= post_count
                    THEN 'like'
                    WHEN post_count >= view_count AND post_count >= login_count AND post_count >= comment_count AND post_count >= like_count
                    THEN 'post'
                    ELSE 'mixed'
                END AS segment_value
            FROM user_action_stats
        ),
        month_pairs AS (
            SELECT DISTINCT
                us.segment_value,
                us.month AS curr_month,
                {month_subtract} AS prev_month
            FROM user_segments us
            WHERE us.month > :start_month
        ),
        aggregated AS (
            SELECT 
                mp.segment_value,
                COUNT(DISTINCT CASE WHEN ps.month = mp.prev_month THEN ps.user_hash END) AS previous_active,
                COUNT(DISTINCT CASE WHEN cs.month = mp.curr_month THEN cs.user_hash END) AS current_active,
                COUNT(DISTINCT CASE 
                    WHEN ps.month = mp.prev_month 
                    AND NOT EXISTS (
                        SELECT 1 FROM user_segments cs2 
                        WHERE cs2.user_hash = ps.user_hash 
                        AND cs2.month = mp.curr_month
                    )
                    THEN ps.user_hash 
                END) AS churned_users
            FROM month_pairs mp
            LEFT JOIN user_segments ps ON ps.segment_value = mp.segment_value AND ps.month = mp.prev_month
            LEFT JOIN user_segments cs ON cs.segment_value = mp.segment_value AND cs.month = mp.curr_month
            GROUP BY mp.segment_value
        )
        SELECT 
            segment_value,
            current_active,
            previous_active,
            churned_users,
            CASE 
                WHEN previous_active > 0 THEN ROUND((CAST(churned_users AS FLOAT) / previous_active * 100), 1)
                ELSE 0 
            END AS churn_rate,
            CASE WHEN previous_active < :min_sample THEN true ELSE false END AS is_uncertain
        FROM aggregated
        WHERE previous_active > 0
        ORDER BY churn_rate DESC
        """)
        
        results = self.db.execute(query, {
            "start_month": f"{start_month}-01",
            "end_month": f"{end_month}-01",
            "min_sample": self.min_sample_size
        }).fetchall()
        
        from decimal import Decimal
        def convert_value(value):
            if isinstance(value, Decimal):
                return float(value) if isinstance(value, Decimal) and value % 1 != 0 else int(value)
            return value
        
        return [
            {
                "segment_value": row.segment_value,
                "current_active": int(convert_value(row.current_active)),
                "previous_active": int(convert_value(row.previous_active)),
                "churned_users": int(convert_value(row.churned_users)),
                "churn_rate": float(convert_value(row.churn_rate)),
                "is_uncertain": bool(row.is_uncertain)
            }
            for row in results
        ]
