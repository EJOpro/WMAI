"""
🎯 Mock API 엔드포인트
시니어의 설명:
- 실제 백엔드 완성 전까지 사용할 가짜 데이터
- 프론트엔드 개발 시 유용
- 나중에 실제 DB로 교체
"""

import logging
import os

from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import Counter
import random
import time
import httpx
from chrun_backend.rag_pipeline.models import AnalysisRequest
from chrun_backend.rag_pipeline.service import analyze_and_store
from chrun_backend.rag_pipeline.report_repository import get_recent_results

router = APIRouter(tags=["api"])
logger = logging.getLogger(__name__)

# Ethics Analyzer 전역 변수 (main.py에서 초기화됨)
ethics_analyzer = None

# ============================================
# 📊 데이터 모델 (Pydantic)
# ============================================

class SearchResult(BaseModel):
    """검색 결과 모델"""
    id: int
    title: str
    content: str
    author: str
    date: str
    category: str

class BounceMetrics(BaseModel):
    """이탈률 메트릭"""
    avg_bounce_rate: float
    total_visitors: int
    bounced_visitors: int
    period: str

class TrendItem(BaseModel):
    """트렌드 아이템"""
    keyword: str
    mentions: int
    change: float
    category: str

class ReportCategory(BaseModel):
    """신고 카테고리"""
    name: str
    count: int
    status: str
    avg_processing_time: str

class EthicsScoreRequest(BaseModel):
    """비윤리/스팸지수 분석 요청"""
    text: str

class EthicsScoreResponse(BaseModel):
    """비윤리/스팸지수 분석 응답"""
    ethics_score: float
    detected_expressions: List[dict]
    recommendations: List[dict]

# ============================================
# 🔍 검색 API
# ============================================

@router.get("/search")
async def search(q: str = Query(..., description="검색 키워드")):
    """
    자연어 검색 API
    
    **시니어의 팁:**
    - Query(...) : 필수 파라미터
    - Query(None) : 선택적 파라미터
    """
    
    if not q:
        raise HTTPException(status_code=400, detail="검색어를 입력하세요")
    
    # Mock 데이터 생성
    results = [
        {
            "id": i,
            "title": f"{q}에 관한 게시글 {i+1}",
            "content": f"이것은 '{q}' 키워드와 관련된 샘플 게시글입니다. 실제로는 데이터베이스에서 검색됩니다.",
            "author": f"사용자{random.randint(1, 100)}",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": random.choice(["자유게시판", "질문", "정보", "토론"])
        }
        for i in range(5)
    ]
    
    return {
        "query": q,
        "total": len(results),
        "results": results
    }

# ============================================
# 📊 이탈률 메트릭 API
# ============================================

@router.get("/metrics/bounce")
async def get_bounce_metrics():
    """
    방문객 이탈률 데이터
    
    **Mock 데이터:**
    실제로는 Google Analytics나 자체 분석 시스템에서 가져옴
    """
    
    return {
        "metrics": {
            "avg_bounce_rate": 42.5,
            "total_visitors": 15234,
            "bounced_visitors": 6474,
            "period": "2025-01-01 ~ 2025-01-31"
        },
        "details": [
            {
                "date": f"2025-01-{i+1:02d}",
                "visitors": random.randint(300, 800),
                "bounced": random.randint(100, 400),
                "bounce_rate": random.uniform(30, 60)
            }
            for i in range(7)
        ]
    }

# ============================================
# 📈 트렌드 분석 API (실제 데이터)
# ============================================

@router.get("/trends")
async def get_trends(limit: int = Query(100, ge=1, le=1000)):
    """
    MySQL 데이터베이스에서 트렌드 데이터 반환
    
    **설명:**
    - trend_keywords 테이블에서 최근 7일간 키워드 데이터 조회
    - 날짜별 타임라인 생성
    - 증감률 계산 (전일 대비)
    - 게시글/댓글 통계 포함
    """
    from app.database import get_db_connection
    
    try:
        print(f"\n[INFO] MySQL에서 트렌드 데이터 조회 (limit={limit})")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 최근 7일간의 전체 키워드 조회 (날짜별)
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT 
                    keyword,
                    SUM(search_count) as total_count,
                    search_date,
                    category
                FROM trend_keywords
                WHERE search_date >= %s
                GROUP BY keyword, search_date, category
                ORDER BY search_date DESC, total_count DESC
            """, (seven_days_ago,))
            
            keyword_data = cursor.fetchall()
            
            # 2. 키워드별 총 집계 (전체 기간)
            cursor.execute("""
                SELECT 
                    keyword,
                    SUM(search_count) as total_count,
                    category
                FROM trend_keywords
                WHERE search_date >= %s
                GROUP BY keyword, category
                ORDER BY total_count DESC
                LIMIT %s
            """, (seven_days_ago, limit))
            
            top_keywords = cursor.fetchall()
            
            # 3. 게시글/댓글 통계 조회
            cursor.execute("""
                SELECT 
                    COALESCE(total_posts, 0) as total_posts,
                    COALESCE(total_comments, 0) as total_comments
                FROM trend_stats_cache
                WHERE stat_date = CURDATE()
                LIMIT 1
            """)
            
            stats = cursor.fetchone()
            
            if stats:
                total_posts = stats['total_posts']
                total_comments = stats['total_comments']
            else:
                # 캐시가 없으면 실제 테이블에서 조회
                cursor.execute("SELECT COUNT(*) as cnt FROM board")
                posts_result = cursor.fetchone()
                total_posts = posts_result['cnt'] if posts_result else 0
                
                cursor.execute("SELECT COUNT(*) as cnt FROM comment")
                comments_result = cursor.fetchone()
                total_comments = comments_result['cnt'] if comments_result else 0
            
            cursor.close()
        
        print(f"[INFO] 조회된 키워드: {len(top_keywords)}개")
        
        # 키워드 목록 생성
        keywords = [
            {
                "word": item['keyword'],
                "count": item['total_count']
            }
            for item in top_keywords
        ]
        
        # 날짜별 데이터 구조화
        date_word_counts = {}
        for item in keyword_data:
            date = str(item['search_date'])
            keyword = item['keyword']
            count = item['total_count']
            
            if date not in date_word_counts:
                date_word_counts[date] = {}
            date_word_counts[date][keyword] = count
        
        # 증감률 계산
        dates = sorted(date_word_counts.keys())
        trends = []
        
        for kw in keywords[:20]:  # 상위 20개만 트렌드 분석
            word = kw["word"]
            
            # 최근 날짜와 이전 날짜의 검색 횟수 비교
            if len(dates) >= 2:
                recent_count = date_word_counts.get(dates[-1], {}).get(word, 0)
                previous_count = date_word_counts.get(dates[-2], {}).get(word, 0)
                
                if previous_count > 0:
                    change = ((recent_count - previous_count) / previous_count) * 100
                else:
                    change = 100.0 if recent_count > 0 else 0.0
            else:
                change = 0.0
            
            # 카테고리 자동 분류
            if change > 50:
                category = "급상승"
            elif change > 0:
                category = "상승"
            elif change < -50:
                category = "급감"
            elif change < 0:
                category = "하락"
            else:
                category = "유지"
            
            trends.append({
                "keyword": word,
                "mentions": kw["count"],
                "change": round(change, 1),
                "category": category
            })
        
        # 타임라인 데이터 생성 (날짜별 총 검색 횟수)
        timeline = []
        for date in sorted(dates):
            total_count = sum(date_word_counts[date].values())
            timeline.append({
                "date": date,
                "count": total_count
            })
        
        print(f"[INFO] 트렌드 {len(trends)}개, 타임라인 {len(timeline)}개 생성")
        
        # 통계 계산
        total_searches = sum(kw['count'] for kw in keywords)
        unique_keywords = len(keywords)
        
        return {
            "summary": {
                "total_posts": total_posts,
                "total_comments": total_comments,
                "total_searches": total_searches,
                "unique_keywords": unique_keywords,
                "total_trends": len(keywords),
                "new_trends": len([t for t in trends if t["change"] > 50]),
                "rising_trends": len([t for t in trends if t["change"] > 0])
            },
            "keywords": keywords,
            "trends": trends,
            "timeline": timeline,
            "source": "mysql",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[ERROR] MySQL 트렌드 데이터 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: 간단한 더미 데이터 반환
        print("[FALLBACK] 더미 데이터 사용")
        
        mock_keywords = [
            {"word": "인공지능", "count": 450},
            {"word": "챗GPT", "count": 380},
            {"word": "검색", "count": 320},
            {"word": "추천", "count": 280},
            {"word": "Python", "count": 250},
            {"word": "질문", "count": 230},
            {"word": "맛집", "count": 210},
            {"word": "여행", "count": 195},
            {"word": "영화", "count": 180},
            {"word": "리뷰", "count": 175}
        ]
        
        mock_trends = [
            {"keyword": "인공지능", "mentions": 450, "change": 12.5, "category": "상승"},
            {"keyword": "챗GPT", "mentions": 380, "change": 8.6, "category": "상승"},
            {"keyword": "검색", "mentions": 320, "change": 6.7, "category": "상승"},
            {"keyword": "추천", "mentions": 280, "change": 7.7, "category": "상승"},
            {"keyword": "Python", "mentions": 250, "change": 4.2, "category": "상승"}
        ]
        
        mock_timeline = [
            {"date": "2025-01-06", "count": 1450},
            {"date": "2025-01-07", "count": 1680},
            {"date": "2025-01-08", "count": 1920},
            {"date": "2025-01-09", "count": 2150},
            {"date": "2025-01-10", "count": 2380},
            {"date": "2025-01-11", "count": 2610},
            {"date": "2025-01-12", "count": 2850}
        ]
        
        return {
            "summary": {
                "total_posts": 1250,
                "total_comments": 6780,
                "total_searches": sum(k['count'] for k in mock_keywords),
                "unique_keywords": len(mock_keywords),
                "total_trends": len(mock_keywords),
                "new_trends": 0,
                "rising_trends": 5
            },
            "keywords": mock_keywords,
            "trends": mock_trends,
            "timeline": mock_timeline,
            "source": "fallback",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ============================================
# 🚨 신고글 분류 API
# ============================================

@router.get("/reports/moderation")
async def get_reports():
    """신고글 통계 데이터"""
    
    categories = [
        ("스팸/광고", "pending"),
        ("욕설/비방", "resolved"),
        ("음란물", "resolved"),
        ("개인정보 노출", "pending"),
        ("저작권 침해", "rejected"),
        ("기타", "pending")
    ]
    
    total = sum(random.randint(10, 100) for _ in categories)
    
    return {
        "stats": {
            "total": total,
            "pending": random.randint(20, 50),
            "resolved": random.randint(30, 60),
            "rejected": random.randint(5, 15)
        },
        "categories": [
            {
                "name": name,
                "count": random.randint(10, 100),
                "status": status,
                "avg_processing_time": f"{random.randint(1, 48)}시간"
            }
            for name, status in categories
        ]
    }

# ============================================
# ⚠️ 비윤리/스팸지수 분석 API
# ============================================

@router.post("/moderation/ethics-score")
async def analyze_ethics_score(request: EthicsScoreRequest):
    """
    텍스트 비윤리/스팸지수 분석
    
    **실제로는:**
    - NLP 모델 사용
    - AI 기반 분석
    - 데이터베이스 저장
    """
    
    text = request.text.strip()
    
    if not text:
        raise HTTPException(status_code=400, detail="분석할 텍스트를 입력하세요")
    
    # 간단한 키워드 기반 Mock 분석
    ethics_keywords = ["바보", "멍청", "쓰레기", "죽어", "꺼져"]
    detected = []
    
    for keyword in ethics_keywords:
        if keyword in text:
            detected.append({
                "text": keyword,
                "type": "비윤리적 표현",
                "severity": "high" if len(keyword) > 2 else "medium"
            })
    
    ethics_score = min(len(detected) * 25, 100)
    
    recommendations = []
    if ethics_score >= 70:
        recommendations.append({
            "priority": "high",
            "message": "심각한 비윤리적 표현이 감지되었습니다. 즉시 조치가 필요합니다."
        })
    elif ethics_score >= 40:
        recommendations.append({
            "priority": "medium",
            "message": "부적절한 표현이 포함되어 있습니다. 검토가 필요합니다."
        })
    else:
        recommendations.append({
            "priority": "low",
            "message": "특별한 문제가 발견되지 않았습니다."
        })
    
    return {
        "ethics_score": ethics_score,
        "detected_expressions": detected,
        "recommendations": recommendations
    }

# ============================================
# 📊 대시보드 통계 API
# ============================================

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """대시보드용 실시간 통계"""
    
    return {
        "users": {
            "total": 12345,
            "active": 1234,
            "new_today": 56
        },
        "posts": {
            "total": 45678,
            "today": 234
        },
        "reports": {
            "total": 234,
            "pending": 45
        },
        "system": {
            "uptime": "99.9%",
            "response_time": "120ms",
            "status": "healthy"
        }
    }

# ============================================
# 🧪 테스트 엔드포인트
# ============================================

@router.get("/test")
async def test_api():
    """API 연결 테스트"""
    return {
        "status": "success",
        "message": "API가 정상적으로 작동하고 있습니다!",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@router.get("/test/error")
async def test_error():
    """에러 테스트"""
    raise HTTPException(status_code=500, detail="테스트용 에러입니다")

# ============================================
# 🛡️ Ethics 비윤리/스팸 분석 API (실제 구현)
# ============================================

class EthicsAnalyzeRequest(BaseModel):
    """Ethics 분석 요청 모델"""
    text: str = Field(..., description="분석할 텍스트", min_length=1, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "너 정말 멍청하구나"
            }
        }

class RagSimilarCase(BaseModel):
    sentence: str
    similarity: float
    immoral_score: float
    spam_score: float
    confidence: float
    confirmed: bool
    feedback_type: Optional[str] = None
    created_at: Optional[str] = None


class RagAnalysis(BaseModel):
    enabled: bool
    adjustment_applied: bool
    adjustment_weight: float
    similar_cases_count: int
    max_similarity: float
    adjusted_score: Optional[float] = None
    adjusted_spam_score: Optional[float] = None
    similar_cases: List[RagSimilarCase] = Field(default_factory=list)


class DetailedAnalysis(BaseModel):
    """상세 분석 정보"""
    bert_score: Optional[float] = None
    bert_confidence: Optional[float] = None
    llm_score: Optional[float] = None
    llm_confidence: Optional[float] = None
    llm_spam_score: Optional[float] = None
    rule_spam_score: Optional[float] = None
    base_score: Optional[float] = None
    profanity_boost: Optional[float] = None
    weights: dict
    spam_weights: dict
    rag: RagAnalysis

class EthicsAnalyzeResponse(BaseModel):
    """Ethics 분석 응답 모델"""
    text: str
    score: Optional[float] = Field(None, description="비윤리 점수 (0-100, 즉시 차단 시 null)")
    confidence: Optional[float] = Field(None, description="비윤리 신뢰도 (0-100, 즉시 차단 시 null)")
    spam: Optional[float] = Field(None, description="스팸 지수 (0-100, 즉시 차단 시 null)")
    spam_confidence: Optional[float] = Field(None, description="스팸 신뢰도 (0-100, 즉시 차단 시 null)")
    types: List[str] = Field(..., description="분석 유형 목록")
    auto_blocked: Optional[bool] = Field(False, description="즉시 차단 여부")
    detailed: DetailedAnalysis = Field(..., description="상세 분석 정보")


def simplify_result(result: dict) -> dict:
    """분석 결과를 간결한 형식으로 변환 (소수점 1자리)"""
    rag_similar_cases = []
    for case in result.get('rag_similar_cases', []) or []:
        rag_similar_cases.append({
            'sentence': case.get('sentence', ''),
            'similarity': round(case.get('similarity', 0.0), 3),
            'immoral_score': round(case.get('immoral_score', 0.0), 1),
            'spam_score': round(case.get('spam_score', 0.0), 1),
            'confidence': round(case.get('confidence', 0.0), 1),
            'confirmed': bool(case.get('confirmed', False)),
            'feedback_type': case.get('feedback_type'),
            'created_at': case.get('created_at')
        })

    adjustment_applied = bool(result.get('adjustment_applied', False))
    auto_blocked = bool(result.get('auto_blocked', False))
    
    # 즉시 차단 케이스는 None 값을 그대로 반환
    def safe_round(value, digits=1):
        """None-safe rounding"""
        return round(value, digits) if value is not None else None
    
    return {
        'text': result['text'],
        'score': safe_round(result.get('final_score')),
        'confidence': safe_round(result.get('final_confidence')),
        'spam': safe_round(result.get('spam_score')),
        'spam_confidence': safe_round(result.get('spam_confidence')),
        'types': result.get('types', []),
        'auto_blocked': auto_blocked,
        # 상세 정보 추가
        'detailed': {
            'bert_score': safe_round(result.get('bert_score')),
            'bert_confidence': safe_round(result.get('bert_confidence')),
            'llm_score': safe_round(result.get('llm_score', 0.0)) if not auto_blocked else None,
            'llm_confidence': safe_round(result.get('llm_confidence', 0.0)) if not auto_blocked else None,
            'llm_spam_score': safe_round(result.get('llm_spam_score', 0.0)) if not auto_blocked else None,
            'rule_spam_score': safe_round(result.get('rule_spam_score')),
            'base_score': safe_round(result.get('base_score')),
            'profanity_boost': safe_round(result.get('profanity_boost')),
            'weights': {
                'bert': round(result.get('weights', {}).get('bert', 0.0), 2),
                'llm': round(result.get('weights', {}).get('llm', 0.0), 2)
            },
            'spam_weights': {
                'llm': 0.6 if result.get('rule_spam_score', 0) < 80 else 0.3,
                'rule': 0.4 if result.get('rule_spam_score', 0) < 80 else 0.7
            },
            'rag': {
                'enabled': bool(result.get('rag_enabled', False)),
                'adjustment_applied': adjustment_applied,
                'adjustment_weight': round(result.get('adjustment_weight', 0.0), 2) if adjustment_applied else 0.0,
                'similar_cases_count': result.get('similar_cases_count', 0),
                'max_similarity': round(result.get('max_similarity', 0.0), 2),
                'adjusted_score': safe_round(result.get('adjusted_immoral_score')) if adjustment_applied and result.get('adjusted_immoral_score') is not None else None,
                'adjusted_spam_score': safe_round(result.get('adjusted_spam_score')) if adjustment_applied and result.get('adjusted_spam_score') is not None else None,
                'similar_cases': rag_similar_cases
            }
        },
        'rag_applied': adjustment_applied
    }


@router.post("/ethics/analyze", response_model=EthicsAnalyzeResponse, tags=["ethics"])
async def ethics_analyze(request_data: EthicsAnalyzeRequest, request: Request):
    """
    텍스트 비윤리/스팸 분석 (하이브리드 시스템)
    
    - **text**: 분석할 텍스트 (최대 1000자)
    
    Returns:
    - 비윤리 점수, 신뢰도, 스팸 지수, 유형 정보 등
    """
    global ethics_analyzer
    
    # 지연 로딩: 서버 시작 시 초기화 실패한 경우 재시도
    if ethics_analyzer is None:
        try:
            print("[INFO] Ethics 분석기 초기화 중 (재시도)...")
            from ethics.ethics_hybrid_predictor import HybridEthicsAnalyzer
            ethics_analyzer = HybridEthicsAnalyzer()
            print("[INFO] Ethics 분석기 초기화 완료")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"분석기 초기화 실패: {str(e)}. models/ 디렉토리와 .env 파일을 확인하세요.")
    
    if ethics_analyzer is None:
        raise HTTPException(status_code=503, detail="분석기가 초기화되지 않았습니다.")
    
    start_time = time.time()
    
    try:
        result = ethics_analyzer.analyze(request_data.text)
        simplified = simplify_result(result)
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        
        # 로그 저장
        try:
            from ethics.ethics_db_logger import db_logger
            log_id = db_logger.log_analysis(
                text=simplified['text'],
                score=simplified['score'],
                confidence=simplified['confidence'],
                spam=simplified['spam'],
                spam_confidence=simplified['spam_confidence'],
                types=simplified['types'],
                ip_address=request.client.host,
                user_agent=request.headers.get('user-agent'),
                response_time=response_time,
                rag_applied=simplified.get('rag_applied', False),
                auto_blocked=result.get('auto_blocked', False)
            )
            
            # RAG 상세 정보 저장 (RAG가 적용된 경우)
            if simplified.get('rag_applied', False) and log_id:
                try:
                    rag_info = simplified.get('detailed', {}).get('rag', {})
                    db_logger.log_rag_details(
                        ethics_log_id=log_id,
                        similar_case_count=rag_info.get('similar_cases_count', 0),
                        max_similarity=rag_info.get('max_similarity', 0.0),  # 이미 0-1 범위
                        original_immoral_score=simplified.get('detailed', {}).get('base_score', simplified['score']),
                        original_spam_score=result.get('base_spam_score', simplified.get('spam', 0.0)),  # RAG 보정 전 스팸 점수
                        adjusted_immoral_score=rag_info.get('adjusted_score', simplified['score']),
                        adjusted_spam_score=rag_info.get('adjusted_spam_score', simplified['spam']),
                        adjustment_weight=rag_info.get('adjustment_weight', 0.0),
                        confidence_boost=0.0,  # 별도 계산 필요 시 추가
                        similar_cases=rag_info.get('similar_cases', []),
                        rag_response_time=response_time
                    )
                except Exception as rag_log_error:
                    print(f"[WARN] RAG 로그 저장 실패: {rag_log_error}")
        except Exception as log_error:
            print(f"[WARN] 로그 저장 실패: {log_error}")
        
        return simplified
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@router.get("/ethics/logs", tags=["ethics"])
async def get_ethics_logs(
    limit: int = Query(100, description="최대 조회 개수"),
    offset: int = Query(0, description="시작 위치"),
    min_score: Optional[float] = Query(None, description="최소 점수 필터"),
    max_score: Optional[float] = Query(None, description="최대 점수 필터"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)")
):
    """
    Ethics 분석 로그 조회
    
    - **limit**: 최대 조회 개수 (기본값: 100)
    - **offset**: 시작 위치 (기본값: 0)
    - **min_score**: 최소 점수 필터
    - **max_score**: 최대 점수 필터
    - **start_date**: 시작 날짜 (YYYY-MM-DD)
    - **end_date**: 종료 날짜 (YYYY-MM-DD)
    """
    try:
        from ethics.ethics_db_logger import db_logger
        logs = db_logger.get_logs_with_rag(
            limit=limit,
            offset=offset,
            min_score=min_score,
            max_score=max_score,
            start_date=start_date,
            end_date=end_date
        )
        return {
            "logs": logs,
            "count": len(logs),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 중 오류: {str(e)}")


@router.get("/ethics/logs/stats", tags=["ethics"])
async def get_ethics_statistics(days: int = Query(7, description="조회할 일수")):
    """
    Ethics 통계 정보 조회
    
    - **days**: 조회할 일수 (기본값: 7일)
    
    Returns:
    - 전체 건수, 평균 점수, 고위험 건수, 스팸 건수, 일별 통계
    """
    try:
        from ethics.ethics_db_logger import db_logger
        stats = db_logger.get_statistics(days=days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류: {str(e)}")


@router.delete("/ethics/logs/{log_id}", tags=["ethics"])
async def delete_ethics_log(log_id: int):
    """
    특정 Ethics 로그 삭제
    
    - **log_id**: 삭제할 로그의 ID
    
    Returns:
    - 삭제 성공 메시지
    """
    try:
        from ethics.ethics_db_logger import db_logger
        success = db_logger.delete_log(log_id)
        if success:
            return {
                "success": True,
                "message": f"로그 ID {log_id} 삭제 완료"
            }
        else:
            raise HTTPException(status_code=404, detail="해당 로그를 찾을 수 없습니다")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 삭제 중 오류: {str(e)}")


@router.delete("/ethics/logs/batch/old", tags=["ethics"])
async def delete_old_ethics_logs(days: int = Query(90, description="보관 기간 (일)")):
    """
    오래된 Ethics 로그 삭제
    
    - **days**: 보관 기간 (기본값: 90일, 0이면 모든 로그 삭제)
    
    Returns:
    - 삭제된 로그 수
    """
    try:
        from ethics.ethics_db_logger import db_logger
        if days == 0:
            # 모든 로그 삭제
            deleted_count = db_logger.delete_all_logs()
            return {
                "deleted_count": deleted_count,
                "message": f"모든 로그 {deleted_count}개 삭제 완료"
            }
        else:
            # 지정된 기간 이전 로그 삭제
            deleted_count = db_logger.delete_old_logs(days=days)
            return {
                "deleted_count": deleted_count,
                "message": f"{days}일 이전 로그 {deleted_count}개 삭제 완료"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 삭제 중 오류: {str(e)}")


@router.get("/risk/top", tags=["risk"])
async def get_risk_top_users(limit: int = Query(10, ge=1, le=100, description="조회할 사용자 수")):
    """
    고위험 사용자 목록 조회
    
    - **limit**: 조회할 사용자 수 (기본값: 10, 최대: 100)
    
    Returns:
    - summary: 통계 요약 정보
    - users: 고위험 사용자 목록
    """
    try:
        from chrun_backend.rag_pipeline.high_risk_store import get_recent_high_risk, init_db
        from datetime import datetime
        
        # DB 초기화 (없으면 생성)
        init_db()
        
        # 고위험 데이터 조회 (confirmed=0인 항목만 - 아직 처리하지 않은 것들)
        risk_data = get_recent_high_risk(limit=limit, only_unconfirmed=True)
        
        if not risk_data:
            return {
                "summary": {
                    "total_users": 0,
                    "high_priority_count": 0,
                    "medium_priority_count": 0,
                    "avg_risk_score": 0.0
                },
                "users": []
            }
        
        # 사용자별로 그룹화 (같은 user_id의 문장들을 하나의 사용자로)
        user_dict = {}
        for item in risk_data:
            user_id = item['user_id']
            if user_id not in user_dict:
                user_dict[user_id] = {
                    'chunk_id': item['chunk_id'],
                    'user_id': user_id,
                    'username': f"사용자_{user_id}",
                    'post_id': item.get('post_id', ''),
                    'risk_score': item['risk_score'],
                    'confirmed': bool(item.get('confirmed', 0)),
                    'evidence_sentences': [],
                    'last_activity': item.get('created_at', datetime.now().isoformat()),
                    'feedback_at': item.get('created_at') if item.get('confirmed') else None
                }
            
            # 문장 추가
            user_dict[user_id]['evidence_sentences'].append(item['sentence'])
            
            # 가장 높은 risk_score 사용
            if item['risk_score'] > user_dict[user_id]['risk_score']:
                user_dict[user_id]['risk_score'] = item['risk_score']
                user_dict[user_id]['chunk_id'] = item['chunk_id']
        
        # 사용자 리스트로 변환
        users = []
        for user_data in user_dict.values():
            # Priority 결정 (risk_score >= 0.7: HIGH, >= 0.5: MEDIUM, 그 외: LOW)
            if user_data['risk_score'] >= 0.7:
                priority = 'HIGH'
            elif user_data['risk_score'] >= 0.5:
                priority = 'MEDIUM'
            else:
                priority = 'LOW'
            
            # 제안 조치사항 생성
            if priority == 'HIGH':
                suggested_action = "즉시 연락 및 개선 조치 필요. 고위험 이탈 징후 감지됨."
            elif priority == 'MEDIUM':
                suggested_action = "모니터링 강화 및 예방적 조치 권장."
            else:
                suggested_action = "정기 모니터링 권장."
            
            users.append({
                **user_data,
                'priority': priority,
                'similar_patterns_count': len(user_data['evidence_sentences']),
                'suggested_action': suggested_action
            })
        
        # risk_score 기준으로 정렬
        users.sort(key=lambda x: x['risk_score'], reverse=True)
        
        # 통계 계산
        high_priority_count = sum(1 for u in users if u['priority'] == 'HIGH')
        medium_priority_count = sum(1 for u in users if u['priority'] == 'MEDIUM')
        avg_risk_score = sum(u['risk_score'] for u in users) / len(users) if users else 0.0
        
        return {
            "summary": {
                "total_users": len(users),
                "high_priority_count": high_priority_count,
                "medium_priority_count": medium_priority_count,
                "avg_risk_score": round(avg_risk_score, 2)
            },
            "users": users
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"고위험 사용자 조회 중 오류: {str(e)}")


class RiskFeedbackBase(BaseModel):
    chunk_id: str
    sentence: str
    pred_score: float
    final_label: str


class RiskFeedbackRequest(RiskFeedbackBase):
    """고위험 사용자 피드백 요청"""
    confirmed: bool


class CheckNewPostRequest(BaseModel):
    """새 게시물 위험도 체크 요청"""
    text: str
    user_id: str
    post_id: str
    created_at: str


class AutoAnalyzeRequest(BaseModel):
    """자동 RAG 분석 요청"""
    user_id: str
    post_id: str
    post_type: str = Field("post", description="post/comment 등")
    text: str
    created_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AutoAnalyzeResponse(BaseModel):
    id: int
    risk_score: float
    priority: str
    decision: Dict[str, Any]
    evidence_count: int


@router.get("/risk/collection_stats", tags=["risk"])
async def get_risk_collection_stats():
    """
    벡터 DB 컬렉션 통계 조회

    Returns:
        Dict[str, Any]: 컬렉션 이름과 문서 수, 마지막 업데이트 시각
    """
    try:
        from chrun_backend.rag_pipeline.vector_db import get_client, get_collection_stats

        client = get_client()
        stats = get_collection_stats(client)

        if "error" in stats:
            raise HTTPException(status_code=500, detail=f"벡터DB 통계 조회 실패: {stats['error']}")

        return {
            "name": stats.get("collection_name", "confirmed_risk"),
            "count": stats.get("total_documents", 0),
            "status": stats.get("status", "unknown")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[RISK] 벡터DB 통계 조회 실패")
        raise HTTPException(status_code=500, detail=f"벡터DB 통계 조회 중 예외 발생: {str(e)}")


def _build_safe_risk_response(
    request_data: CheckNewPostRequest,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """에러 상황에서 안전한 기본 응답을 생성합니다."""
    from chrun_backend.rag_pipeline.rag_checker import _create_safe_decision

    decision = _create_safe_decision()
    decision["confidence"] = "Uncertain"

    response: Dict[str, Any] = {
        "post": {
            "user_id": request_data.user_id,
            "post_id": request_data.post_id,
            "created_at": request_data.created_at,
            "original_text": request_data.text,
        },
        "decision": decision,
        "evidence": [],
    }

    if error:
        response["error"] = error

    return response


def _ensure_risk_response_schema(
    result: Dict[str, Any],
    request_data: CheckNewPostRequest
) -> Dict[str, Any]:
    """응답 객체가 필수 스키마(post/decision/evidence)를 만족하도록 보정합니다."""
    if not isinstance(result, dict):
        logger.warning("[RISK] check_new_post 결과가 dict가 아닙니다. 안전 응답으로 대체합니다.")
        return _build_safe_risk_response(request_data, error="Invalid response type")

    post_payload = result.get("post") or {}
    decision_payload = result.get("decision") or {}
    evidence_payload = result.get("evidence") or []

    if not isinstance(evidence_payload, list):
        logger.warning("[RISK] evidence가 리스트가 아닙니다. 빈 리스트로 대체합니다.")
        evidence_payload = []

    post_data = {
        "user_id": post_payload.get("user_id") or request_data.user_id,
        "post_id": post_payload.get("post_id") or request_data.post_id,
        "created_at": post_payload.get("created_at") or request_data.created_at,
        "original_text": post_payload.get("original_text") or request_data.text,
    }

    # ⭐ Evidence가 없어도 LLM 결정이 있으면 사용 (Evidence는 참고 자료일 뿐)
    if not isinstance(decision_payload, dict):
        logger.warning("[RISK] decision이 dict가 아닙니다. 안전 결정으로 대체합니다.")
        decision_payload = {}
    
    # LLM이 정상 분석했는지 확인 (risk_score가 있고 기본값 아님)
    has_valid_llm_decision = (
        decision_payload.get("risk_score") is not None and 
        decision_payload.get("priority") and
        decision_payload.get("reasons") and
        # 기본 fallback 메시지가 아닌지 확인
        "유사한 위험 문장이 발견되지 않음" not in str(decision_payload.get("reasons", []))
    )
    
    # Evidence 없고 LLM 결정도 없으면 safe_response 사용
    if not evidence_payload and not has_valid_llm_decision:
        logger.warning("[RISK] Evidence와 유효한 LLM 결정이 모두 없습니다. 안전 응답 반환")
        safe_response = _build_safe_risk_response(request_data)
        if "fallback_reason" in decision_payload:
            safe_response["decision"]["fallback_reason"] = decision_payload["fallback_reason"]
        return safe_response

    # Evidence 없어도 LLM 결정이 있으면 사용
    if not evidence_payload:
        logger.info("[RISK] Evidence 없음. LLM이 원문만으로 분석한 결과 사용")
    
    decision_payload.setdefault("confidence", "Uncertain" if not evidence_payload else "Low")

    return {
        "post": post_data,
        "decision": decision_payload,
        "evidence": evidence_payload,
    }


@router.post("/risk/feedback", tags=["risk"])
async def submit_risk_feedback(request_data: RiskFeedbackRequest):
    """
    고위험 사용자 피드백 제출
    
    - **chunk_id**: 피드백할 chunk_id
    - **confirmed**: 위험 확인 여부 (true: 위험 맞음, false: 위험 아님)
    
    Returns:
    - 성공 메시지
    """
    try:
        from chrun_backend.rag_pipeline.high_risk_store import update_feedback, get_chunk_by_id, log_feedback_event
        
        sentence = request_data.sentence.strip() if request_data.sentence else ""
        if not sentence:
            raise HTTPException(status_code=422, detail="sentence 필드는 비워둘 수 없습니다.")

        try:
            pred_score = float(request_data.pred_score)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="pred_score는 숫자여야 합니다.")

        final_label = request_data.final_label.strip().upper()
        if final_label not in {"MATCH", "MISMATCH", "UPDATE"}:
            raise HTTPException(status_code=422, detail="final_label은 MATCH/MISMATCH/UPDATE 중 하나여야 합니다.")

        # 1. 기존 SQLite 피드백 업데이트 (기존 기능 유지)
        update_feedback(request_data.chunk_id, request_data.confirmed)
        chunk_snapshot: Optional[Dict[str, Any]] = None
        
        # 2. confirmed=true인 경우에만 벡터DB에 저장
        if request_data.confirmed:
            try:
                # 2-1. SQLite에서 해당 chunk 정보 조회
                chunk_data = get_chunk_by_id(request_data.chunk_id)
                chunk_snapshot = chunk_data
                
                if not chunk_data:
                    # chunk를 찾을 수 없어도 기본 피드백은 성공으로 처리
                    print(f"[WARN] 벡터DB 저장 실패: chunk_id {request_data.chunk_id}를 찾을 수 없음")
                else:
                    # 2-2. 임베딩 생성
                    from chrun_backend.rag_pipeline.embedding_service import get_embedding
                    sentence = chunk_data.get('sentence', '')
                    
                    if sentence.strip():
                        embedding = get_embedding(sentence)
                        
                        # 2-3. 벡터DB에 저장할 메타데이터 구성
                        from chrun_backend.rag_pipeline.vector_db import build_chunk_id
                        
                        # 안정적인 chunk_id 생성 (기존 chunk_id와 다를 수 있음)
                        vector_chunk_id = build_chunk_id(sentence, chunk_data.get('post_id', ''))
                        
                        meta = {
                            "chunk_id": vector_chunk_id,  # 벡터DB용 안정적 ID
                            "original_chunk_id": chunk_data.get('chunk_id'),  # 원본 SQLite chunk_id
                            "user_id": chunk_data.get('user_id', ''),
                            "post_id": chunk_data.get('post_id', ''),
                            "sentence": sentence,
                            "risk_score": float(chunk_data.get('risk_score', 0.0)),
                            "created_at": chunk_data.get('created_at', ''),
                            "confirmed": True
                        }
                        
                        # 2-4. 벡터DB에 upsert (idempotent)
                        from chrun_backend.rag_pipeline.vector_db import get_client, upsert_confirmed_chunk
                        
                        client = get_client()  # 기본 경로 "./chroma_store" 사용
                        upsert_confirmed_chunk(client, embedding, meta)
                        
                        print(f"[INFO] 확인된 위험 문장을 벡터DB에 저장 완료: {vector_chunk_id}")
                    else:
                        print(f"[WARN] 벡터DB 저장 실패: 빈 문장 (chunk_id: {request_data.chunk_id})")
                        
            except Exception as vector_error:
                # 벡터DB 저장 실패해도 기본 피드백은 성공으로 처리
                import traceback
                print(f"[ERROR] 벡터DB 저장 중 오류 발생: {vector_error}")
                traceback.print_exc()
                # 에러 로그만 남기고 API는 성공으로 응답
        
        if chunk_snapshot is None:
            chunk_snapshot = get_chunk_by_id(request_data.chunk_id)
        user_id_for_hash = chunk_snapshot.get('user_id') if chunk_snapshot else None

        event_id = log_feedback_event(
            chunk_id=request_data.chunk_id,
            sentence=sentence[:500],
            pred_score=max(0.0, min(1.0, pred_score)),
            final_label=final_label,
            confirmed=request_data.confirmed,
            user_id=user_id_for_hash
        )

        return {
            "status": "ok",
            "feedback_id": event_id,
            "chunk_id": request_data.chunk_id,
            "final_label": final_label,
            "pred_score": round(max(0.0, min(1.0, pred_score)), 3),
            "confirmed": request_data.confirmed
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"피드백 저장 중 오류: {str(e)}")


@router.get("/risk/feedback", tags=["risk"])
async def list_risk_feedback(limit: int = Query(50, ge=1, le=200)):
    """
    피드백 이벤트 목록 조회
    """
    try:
        from chrun_backend.rag_pipeline.high_risk_store import get_feedback_events

        events = get_feedback_events(limit=limit)
        return {
            "items": events,
            "count": len(events)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[RISK] 피드백 로그 조회 실패")
        raise HTTPException(status_code=500, detail=f"피드백 로그 조회 중 예외 발생: {str(e)}")


@router.post("/risk/analyze", response_model=AutoAnalyzeResponse, tags=["risk"])
async def auto_analyze_risk(request_data: AutoAnalyzeRequest):
    """
    자동 RAG 분석을 실행하고 결과를 저장합니다.
    """
    analysis_request = AnalysisRequest(
        user_id=request_data.user_id,
        post_id=request_data.post_id,
        post_type=request_data.post_type,
        text=request_data.text,
        created_at=request_data.created_at,
        metadata=request_data.metadata,
    )
    result = analyze_and_store(analysis_request)
    context = result["context"]
    decision = context.get("decision", {})
    return AutoAnalyzeResponse(
        id=result["id"],
        risk_score=float(decision.get("risk_score", 0.0)),
        priority=decision.get("priority", "LOW"),
        decision=decision,
        evidence_count=len(context.get("evidence", [])),
    )


@router.get("/risk/analysis_results", tags=["risk"])
async def list_analysis_results(limit: int = Query(50, ge=1, le=200)):
    """
    저장된 RAG 분석 결과 목록 조회
    """
    try:
        items = get_recent_results(limit=limit)
        return {
            "items": items,
            "count": len(items),
        }
    except Exception as e:
        logger.exception("[RISK] 분석 결과 조회 실패")
        raise HTTPException(status_code=500, detail=f"분석 결과 조회 중 예외 발생: {str(e)}")

@router.post("/risk/check_new_post", tags=["risk"])
async def check_new_post_risk(request_data: CheckNewPostRequest):
    """
    새 게시물의 위험도를 체크하여 근거 컨텍스트를 반환합니다.
    
    - **text**: 분석할 게시물 텍스트
    - **user_id**: 사용자 ID
    - **post_id**: 게시물 ID
    - **created_at**: 생성 시간 (ISO 형식, 예: "2024-11-04T10:30:00")
    
    Returns:
    - 위험도 분석을 위한 컨텍스트 (근거 문장들과 통계 정보)
    """
    try:
        from chrun_backend.rag_pipeline.rag_checker import check_new_post

        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("[RISK] OPENAI_API_KEY가 설정되지 않았습니다. 기본 결정이 반환될 수 있습니다.")

        context = check_new_post(
            text=request_data.text,
            user_id=request_data.user_id,
            post_id=request_data.post_id,
            created_at=request_data.created_at
        )

        return _ensure_risk_response_schema(context, request_data)

    except Exception as e:
        logger.exception("[RISK] 새 게시물 위험도 체크 중 예외 발생")
        return _build_safe_risk_response(request_data, error=str(e))
