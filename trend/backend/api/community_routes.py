"""커뮤니티 관련 API 라우트"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, List
import pymysql
from loguru import logger

from backend.services.text_analysis import text_analysis_service
from config.settings import settings

router = APIRouter(
    prefix="/api/v1/community",
    tags=["Community"]
)


def get_db_connection():
    """wmai_db 연결"""
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


@router.get("/wordcloud")
async def get_wordcloud(
    start: str = Query(..., description="시작 일시 (ISO format)"),
    end: str = Query(..., description="종료 일시 (ISO format)"),
    category: Optional[str] = Query(None, description="게시판 카테고리"),
    top_k: int = Query(50, description="상위 K개 키워드")
):
    """
    키워드 추출 및 워드클라우드 데이터
    """
    try:
        # 날짜 파싱
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 게시글 조회 쿼리
        board_query = """
            SELECT title, content, created_at 
            FROM board 
            WHERE status = 'exposed' 
            AND created_at BETWEEN %s AND %s
        """
        params = [start_dt, end_dt]
        
        if category:
            board_query += " AND category = %s"
            params.append(category)
        
        cursor.execute(board_query, params)
        boards = cursor.fetchall()
        
        # 댓글 조회 쿼리
        comment_query = """
            SELECT c.content, c.created_at
            FROM comment c
            JOIN board b ON c.board_id = b.id
            WHERE c.status = 'exposed' 
            AND c.created_at BETWEEN %s AND %s
        """
        comment_params = [start_dt, end_dt]
        
        if category:
            comment_query += " AND b.category = %s"
            comment_params.append(category)
        
        cursor.execute(comment_query, comment_params)
        comments = cursor.fetchall()
        
        # 텍스트 추출
        texts = []
        for board in boards:
            texts.append(f"{board['title']} {board['content']}")
        
        for comment in comments:
            texts.append(comment['content'])
        
        # 키워드 추출
        keywords = text_analysis_service.extract_keywords(texts, top_k=top_k)
        words = text_analysis_service.calculate_word_weights(keywords)
        
        conn.close()
        
        return {
            "words": words,
            "total_posts": len(boards),
            "total_comments": len(comments),
            "period": {
                "start": start,
                "end": end
            }
        }
        
    except Exception as e:
        logger.error(f"Wordcloud API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_timeline(
    start: str = Query(..., description="시작 일시 (ISO format)"),
    end: str = Query(..., description="종료 일시 (ISO format)"),
    keywords: str = Query(..., description="키워드 (쉼표로 구분)"),
    granularity: str = Query("1d", description="집계 단위 (1h/1d/1w)"),
    category: Optional[str] = Query(None, description="게시판 카테고리")
):
    """
    시간대별 키워드 트렌드
    """
    try:
        # 날짜 파싱
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        # 키워드 리스트 파싱
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 게시글과 댓글을 시간대별로 조회
        query = """
            SELECT title, content, created_at FROM board 
            WHERE status = 'exposed' AND created_at BETWEEN %s AND %s
        """
        params = [start_dt, end_dt]
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        query += """
            UNION ALL
            SELECT '' as title, c.content, c.created_at FROM comment c
            JOIN board b ON c.board_id = b.id
            WHERE c.status = 'exposed' AND c.created_at BETWEEN %s AND %s
        """
        params.extend([start_dt, end_dt])
        
        if category:
            query += " AND b.category = %s"
            params.append(category)
        
        query += " ORDER BY created_at"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # 텍스트와 타임스탬프 조합
        texts_with_timestamp = []
        for row in results:
            text = f"{row['title']} {row['content']}".strip()
            texts_with_timestamp.append((row['created_at'], text))
        
        # 시간대별 키워드 추출
        timeline_data = text_analysis_service.extract_keywords_by_timeframe(
            texts_with_timestamp, 
            granularity=granularity,
            keywords=keyword_list
        )
        
        # 응답 형식으로 변환
        series = []
        for keyword in keyword_list:
            points = []
            for timestamp, keyword_counts in sorted(timeline_data.items()):
                count = keyword_counts.get(keyword, 0)
                points.append({
                    "ts": timestamp.isoformat(),
                    "count": count
                })
            
            series.append({
                "keyword": keyword,
                "points": points
            })
        
        conn.close()
        
        return {
            "series": series,
            "period": {
                "start": start,
                "end": end
            },
            "granularity": granularity
        }
        
    except Exception as e:
        logger.error(f"Timeline API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular")
async def get_popular_posts(
    start: str = Query(..., description="시작 일시 (ISO format)"),
    end: str = Query(..., description="종료 일시 (ISO format)"),
    category: Optional[str] = Query(None, description="게시판 카테고리"),
    sort_by: str = Query("view_count", description="정렬 기준 (view_count/like_count)"),
    limit: int = Query(20, description="결과 개수")
):
    """
    인기 게시글 조회
    """
    try:
        # 날짜 파싱
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        # 정렬 기준 검증
        if sort_by not in ['view_count', 'like_count']:
            raise HTTPException(status_code=400, detail="sort_by must be 'view_count' or 'like_count'")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 인기 게시글 조회 쿼리
        query = f"""
            SELECT 
                b.id,
                b.title,
                u.username as author,
                b.view_count,
                b.like_count,
                b.created_at,
                b.category
            FROM board b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE b.status = 'exposed' 
            AND b.created_at BETWEEN %s AND %s
        """
        params = [start_dt, end_dt]
        
        if category:
            query += " AND b.category = %s"
            params.append(category)
        
        query += f" ORDER BY b.{sort_by} DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        posts = cursor.fetchall()
        
        # 결과 포맷팅
        result_posts = []
        for post in posts:
            result_posts.append({
                "id": post['id'],
                "title": post['title'],
                "author": post['author'] or "탈퇴한 사용자",
                "view_count": post['view_count'],
                "like_count": post['like_count'],
                "created_at": post['created_at'].isoformat() if post['created_at'] else None,
                "category": post['category']
            })
        
        conn.close()
        
        return {
            "posts": result_posts,
            "sort_by": sort_by,
            "period": {
                "start": start,
                "end": end
            },
            "total": len(result_posts)
        }
        
    except Exception as e:
        logger.error(f"Popular posts API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities")
async def get_communities():
    """
    카테고리 목록 및 게시글 수 조회
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 카테고리별 게시글 수 조회
        query = """
            SELECT 
                category,
                COUNT(*) as post_count
            FROM board 
            WHERE status = 'exposed'
            GROUP BY category
            ORDER BY post_count DESC
        """
        
        cursor.execute(query)
        categories = cursor.fetchall()
        
        # 결과 포맷팅 (community_name으로 매핑)
        result = []
        for cat in categories:
            result.append({
                "community_name": cat['category'],
                "post_count": cat['post_count']
            })
        
        conn.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Communities API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_community_trends():
    """커뮤니티 트렌드 조회 (추후 구현)"""
    return {
        "message": "Community trends endpoint - Coming soon",
        "data": []
    }

