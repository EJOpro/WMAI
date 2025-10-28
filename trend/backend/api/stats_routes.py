"""통계 조회 API"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from backend.services.database import get_connection
from loguru import logger

router = APIRouter(prefix="/v1/stats", tags=["Statistics"])


@router.get("/summary")
async def get_stats_summary():
    """전체 통계 요약 (인증 불필요)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 전체 통계
        cursor.execute("""
            SELECT 
                event_type,
                COUNT(*) as count
            FROM fact_events
            GROUP BY event_type
        """)
        
        total_stats = {}
        total_events = 0
        for row in cursor.fetchall():
            event_type = row[0]
            count = row[1]
            total_stats[event_type] = count
            total_events += count
        
        # 최근 10분 통계
        cursor.execute("""
            SELECT 
                event_type,
                COUNT(*) as count
            FROM fact_events
            WHERE created_at > NOW() - INTERVAL 10 MINUTE
            GROUP BY event_type
        """)
        
        recent_stats = {}
        recent_total = 0
        for row in cursor.fetchall():
            event_type = row[0]
            count = row[1]
            recent_stats[event_type] = count
            recent_total += count
        
        # 오늘 통계
        cursor.execute("""
            SELECT 
                event_type,
                COUNT(*) as count
            FROM fact_events
            WHERE DATE(created_at) = CURDATE()
            GROUP BY event_type
        """)
        
        today_stats = {}
        today_total = 0
        for row in cursor.fetchall():
            event_type = row[0]
            count = row[1]
            today_stats[event_type] = count
            today_total += count
        
        # 최근 이벤트
        cursor.execute("""
            SELECT 
                event_type,
                event_value,
                created_at
            FROM fact_events
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        recent_events = []
        for row in cursor.fetchall():
            recent_events.append({
                'event_type': row[0],
                'event_value': row[1],
                'created_at': row[2].isoformat() if row[2] else None
            })
        
        cursor.close()
        conn.close()
        
        return {
            'total': {
                'events': total_events,
                'pageview': total_stats.get('pageview', 0),
                'search': total_stats.get('search', 0),
                'click': total_stats.get('click', 0),
                'scroll': total_stats.get('scroll', 0),
                'conversion': total_stats.get('conversion', 0),
                'post_write': total_stats.get('post_write', 0),
                'comment_write': total_stats.get('comment_write', 0)
            },
            'recent_10min': {
                'events': recent_total,
                'pageview': recent_stats.get('pageview', 0),
                'search': recent_stats.get('search', 0),
                'click': recent_stats.get('click', 0),
                'scroll': recent_stats.get('scroll', 0),
                'post_write': recent_stats.get('post_write', 0),
                'comment_write': recent_stats.get('comment_write', 0)
            },
            'today': {
                'events': today_total,
                'pageview': today_stats.get('pageview', 0),
                'search': today_stats.get('search', 0),
                'click': today_stats.get('click', 0),
                'scroll': today_stats.get('scroll', 0),
                'post_write': today_stats.get('post_write', 0),
                'comment_write': today_stats.get('comment_write', 0)
            },
            'recent_events': recent_events,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stats summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

