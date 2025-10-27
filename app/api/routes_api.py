"""
🎯 Mock API 엔드포인트
시니어의 설명:
- 실제 백엔드 완성 전까지 사용할 가짜 데이터
- 프론트엔드 개발 시 유용
- 나중에 실제 DB로 교체
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import random

router = APIRouter(tags=["api"])

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

class HateScoreRequest(BaseModel):
    """혐오지수 분석 요청"""
    text: str

class HateScoreResponse(BaseModel):
    """혐오지수 분석 응답"""
    hate_score: float
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
# ⚠️ 혐오지수 분석 API
# ============================================

@router.post("/moderation/hate-score")
async def analyze_hate_score(request: HateScoreRequest):
    """
    텍스트 혐오지수 분석
    
    **실제로는:**
    - NLP 모델 사용
    - AI 기반 분석
    - 데이터베이스 저장
    """
    
    text = request.text.strip()
    
    if not text:
        raise HTTPException(status_code=400, detail="분석할 텍스트를 입력하세요")
    
    # 간단한 키워드 기반 Mock 분석
    hate_keywords = ["바보", "멍청", "쓰레기", "죽어", "꺼져"]
    detected = []
    
    for keyword in hate_keywords:
        if keyword in text:
            detected.append({
                "text": keyword,
                "type": "욕설",
                "severity": "high" if len(keyword) > 2 else "medium"
            })
    
    hate_score = min(len(detected) * 25, 100)
    
    recommendations = []
    if hate_score >= 70:
        recommendations.append({
            "priority": "high",
            "message": "심각한 혐오 표현이 감지되었습니다. 즉시 조치가 필요합니다."
        })
    elif hate_score >= 40:
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
        "hate_score": hate_score,
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

