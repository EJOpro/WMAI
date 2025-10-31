"""집계 워커 - 1분 단위 집계 수행"""
from sqlalchemy import text
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from backend.services.database import get_write_session
from loguru import logger
import sys

# 로깅 설정
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")


class AggregationWorker:
    """집계 워커"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
    
    def aggregate_1m(self):
        """1분 단위 집계 수행"""
        # 현재 시각의 이전 1분 버킷
        now = datetime.utcnow()
        bucket_ts = now.replace(second=0, microsecond=0) - timedelta(minutes=1)
        
        logger.info(f"Starting 1m aggregation for bucket: {bucket_ts}")
        
        try:
            with get_write_session() as session:
                # fact_events를 집계하여 agg_1m에 upsert
                query = text("""
                    INSERT INTO agg_1m (
                        bucket_ts, page_id, utm_id, device_id, country_id,
                        pv, sessions, conv, uv_hll
                    )
                    SELECT 
                        DATE_FORMAT(event_time, '%Y-%m-%d %H:%i:00') as bucket_ts,
                        page_id,
                        COALESCE(utm_id, 0) as utm_id,
                        device_id,
                        COALESCE(country_id, 0) as country_id,
                        COUNT(*) as pv,
                        COUNT(DISTINCT session_id) as sessions,
                        SUM(CASE WHEN event_type = 'conversion' THEN 1 ELSE 0 END) as conv,
                        NULL as uv_hll
                    FROM fact_events
                    WHERE event_time >= :start_ts 
                        AND event_time < :end_ts
                    GROUP BY bucket_ts, page_id, utm_id, device_id, country_id
                    ON DUPLICATE KEY UPDATE
                        pv = pv + VALUES(pv),
                        sessions = sessions + VALUES(sessions),
                        conv = conv + VALUES(conv)
                """)
                
                result = session.execute(
                    query,
                    {
                        "start_ts": bucket_ts,
                        "end_ts": bucket_ts + timedelta(minutes=1)
                    }
                )
                
                logger.info(f"1m aggregation completed: {result.rowcount} rows affected")
                
        except Exception as e:
            logger.error(f"1m aggregation failed: {e}")
    
    def aggregate_5m(self):
        """5분 단위 집계 (1분 집계를 다운샘플)"""
        now = datetime.utcnow()
        bucket_ts = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0) - timedelta(minutes=5)
        
        logger.info(f"Starting 5m aggregation for bucket: {bucket_ts}")
        
        try:
            with get_write_session() as session:
                query = text("""
                    INSERT INTO agg_5m (
                        bucket_ts, page_id, utm_id, device_id, country_id,
                        pv, sessions, conv, uv_hll
                    )
                    SELECT 
                        :bucket_ts as bucket_ts,
                        page_id,
                        utm_id,
                        device_id,
                        country_id,
                        SUM(pv) as pv,
                        SUM(sessions) as sessions,
                        SUM(conv) as conv,
                        NULL as uv_hll
                    FROM agg_1m
                    WHERE bucket_ts >= :start_ts AND bucket_ts < :end_ts
                    GROUP BY page_id, utm_id, device_id, country_id
                    ON DUPLICATE KEY UPDATE
                        pv = VALUES(pv),
                        sessions = VALUES(sessions),
                        conv = VALUES(conv)
                """)
                
                session.execute(
                    query,
                    {
                        "bucket_ts": bucket_ts,
                        "start_ts": bucket_ts,
                        "end_ts": bucket_ts + timedelta(minutes=5)
                    }
                )
                
                logger.info(f"5m aggregation completed")
                
        except Exception as e:
            logger.error(f"5m aggregation failed: {e}")
    
    def aggregate_1h(self):
        """1시간 단위 집계"""
        now = datetime.utcnow()
        bucket_ts = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        
        logger.info(f"Starting 1h aggregation for bucket: {bucket_ts}")
        
        try:
            with get_write_session() as session:
                query = text("""
                    INSERT INTO agg_1h (
                        bucket_ts, page_id, utm_id, device_id, country_id,
                        pv, sessions, conv, uv_hll
                    )
                    SELECT 
                        :bucket_ts as bucket_ts,
                        page_id,
                        utm_id,
                        device_id,
                        country_id,
                        SUM(pv) as pv,
                        SUM(sessions) as sessions,
                        SUM(conv) as conv,
                        NULL as uv_hll
                    FROM agg_5m
                    WHERE bucket_ts >= :start_ts AND bucket_ts < :end_ts
                    GROUP BY page_id, utm_id, device_id, country_id
                    ON DUPLICATE KEY UPDATE
                        pv = VALUES(pv),
                        sessions = VALUES(sessions),
                        conv = VALUES(conv)
                """)
                
                session.execute(
                    query,
                    {
                        "bucket_ts": bucket_ts,
                        "start_ts": bucket_ts,
                        "end_ts": bucket_ts + timedelta(hours=1)
                    }
                )
                
                logger.info(f"1h aggregation completed")
                
        except Exception as e:
            logger.error(f"1h aggregation failed: {e}")
    
    def start(self):
        """워커 시작"""
        # 1분마다 1분 집계 실행
        self.scheduler.add_job(
            self.aggregate_1m,
            'cron',
            minute='*',
            second='5'  # 5초 지연
        )
        
        # 5분마다 5분 집계 실행
        self.scheduler.add_job(
            self.aggregate_5m,
            'cron',
            minute='*/5',
            second='10'
        )
        
        # 매 시간 1시간 집계 실행
        self.scheduler.add_job(
            self.aggregate_1h,
            'cron',
            hour='*',
            minute='1'
        )
        
        self.scheduler.start()
        logger.info("Aggregation worker started")
    
    def stop(self):
        """워커 중지"""
        self.scheduler.shutdown()
        logger.info("Aggregation worker stopped")


# 싱글톤 인스턴스
aggregation_worker = AggregationWorker()


if __name__ == "__main__":
    """워커 단독 실행"""
    import time
    
    worker = AggregationWorker()
    worker.start()
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        worker.stop()


