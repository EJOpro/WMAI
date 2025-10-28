"""
🎯 Mock API 엔드포인트
시니어의 설명:
- 실제 백엔드 완성 전까지 사용할 가짜 데이터
- 프론트엔드 개발 시 유용
- 나중에 실제 DB로 교체
"""

from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import random
import time

router = APIRouter(tags=["api"])

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
# 📈 트렌드 분석 API
# ============================================

@router.get("/trends")
async def get_trends():
    """트렌드 데이터 반환"""
    
    keywords = [
        "인공지능", "블록체인", "메타버스", "NFT", "웹3.0",
        "빅데이터", "클라우드", "사이버보안", "IoT", "5G"
    ]
    
    return {
        "summary": {
            "total_trends": len(keywords),
            "new_trends": 3,
            "rising_trends": 5
        },
        "keywords": [
            {
                "word": kw,
                "count": random.randint(50, 500)
            }
            for kw in keywords
        ],
        "trends": [
            {
                "keyword": kw,
                "mentions": random.randint(100, 1000),
                "change": random.uniform(-30, 50),
                "category": random.choice(["기술", "트렌드", "이슈"])
            }
            for kw in keywords[:5]
        ]
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
        schema_extra = {
            "example": {
                "text": "너 정말 멍청하구나"
            }
        }

class EthicsAnalyzeResponse(BaseModel):
    """Ethics 분석 응답 모델"""
    text: str
    score: float = Field(..., description="비윤리 점수 (0-100)")
    confidence: float = Field(..., description="비윤리 신뢰도 (0-100)")
    spam: float = Field(..., description="스팸 지수 (0-100)")
    spam_confidence: float = Field(..., description="스팸 신뢰도 (0-100)")
    types: List[str] = Field(..., description="분석 유형 목록")


def simplify_result(result: dict) -> dict:
    """분석 결과를 간결한 형식으로 변환 (소수점 1자리)"""
    return {
        'text': result['text'],
        'score': round(result['final_score'], 1),
        'confidence': round(result['final_confidence'], 1),
        'spam': round(result['spam_score'], 1),
        'spam_confidence': round(result['spam_confidence'], 1),
        'types': result['types']
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
            db_logger.log_analysis(
                text=simplified['text'],
                score=simplified['score'],
                confidence=simplified['confidence'],
                spam=simplified['spam'],
                spam_confidence=simplified['spam_confidence'],
                types=simplified['types'],
                ip_address=request.client.host,
                user_agent=request.headers.get('user-agent'),
                response_time=response_time
            )
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
        logs = db_logger.get_logs(
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

