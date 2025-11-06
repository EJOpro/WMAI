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
from datetime import datetime, timedelta
from collections import Counter
import random
import time
import httpx

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
# 📈 트렌드 분석 API (실제 데이터)
# ============================================

@router.get("/trends")
async def get_trends(limit: int = Query(100, ge=1, le=1000)):
    """
    실제 트렌드 데이터 반환 (dad.dothome.co.kr API 연동)
    
    **시니어의 설명:**
    - 외부 API에서 실제 인기 검색어 데이터를 가져옴
    - 키워드 정규화 (검색했음→검색, 검색어→검색)
    - 날짜별 타임라인 생성
    - 실제 증감률 계산
    """
    
    # ⭐ 키워드 정규화 매핑 (자연어 → 키워드)
    KEYWORD_NORMALIZATION = {
        "검색했음": "검색",
        "검색하기": "검색",
        "검색중": "검색",
        "검색어": "검색",
        "검색어들": "검색",
        "안녕하세요": "인사",
        "안녕": "인사",
        "ㅎㅇ": "인사",
    }
    
    def normalize_keyword(word: str) -> str:
        """키워드 정규화"""
        word = word.strip()
        return KEYWORD_NORMALIZATION.get(word, word)
    
    try:
        print(f"\n[DEBUG] Calling dad.dothome.co.kr API with limit={limit}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            # ✅ 1. 실제 인기 검색어 API 호출 (standalone 버전)
            url = "https://dad.dothome.co.kr/adm/popular_api_standalone.php"
            print(f"[DEBUG] URL: {url}")
            
            response = await client.get(url, params={"limit": limit})
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response content-type: {response.headers.get('content-type')}")
            
            response.raise_for_status()
            
            data = response.json()
            print(f"[DEBUG] JSON parsed successfully")
            print(f"[DEBUG] success={data.get('success')}, data_count={len(data.get('data', []))}")
            
            if not data.get("success", False):
                raise Exception("API returned error")
            
            # ✅ 2. 게시글/댓글 통계 API 호출
            stats_url = "https://dad.dothome.co.kr/adm/board_stats_api.php"
            print(f"[DEBUG] Fetching board stats from: {stats_url}")
            
            stats_response = await client.get(stats_url)
            stats_data = stats_response.json()
            
            total_posts = 0
            total_comments = 0
            
            if stats_data.get("success"):
                total_posts = stats_data["data"]["total_posts"]
                total_comments = stats_data["data"]["total_comments"]
                print(f"[DEBUG] Board stats: posts={total_posts}, comments={total_comments}")
                
                # 디버그 정보 출력
                if "debug" in stats_data:
                    print(f"[DEBUG] Tables found: {stats_data['debug'].get('tables_found', [])}")
            else:
                print(f"[DEBUG] Board stats API failed, using defaults")
            
            # 데이터 변환
            api_data = data.get("data", [])
            print(f"[DEBUG] Converting {len(api_data)} items to keywords")
            
            # ⭐ 키워드 정규화 + 빈도 집계
            word_counts = Counter()
            date_word_counts = {}  # 날짜별 키워드 빈도
            
            for item in api_data:
                word = item.get("word", "").strip()
                date = item.get("date", "")
                
                if word:
                    # 키워드 정규화
                    normalized_word = normalize_keyword(word)
                    word_counts[normalized_word] += 1
                    
                    # 날짜별 집계
                    if date not in date_word_counts:
                        date_word_counts[date] = Counter()
                    date_word_counts[date][normalized_word] += 1
            
            # 빈도순으로 정렬하여 키워드 생성
            keywords = [
                {
                    "word": word,
                    "count": count
                }
                for word, count in word_counts.most_common()
            ]
            
            print(f"[DEBUG] Top 5 keywords (after normalization): {keywords[:5]}")
            
            # ⭐ 증감률 계산 (날짜별 비교)
            dates = sorted(date_word_counts.keys())
            trends = []
            
            for kw in keywords[:10]:
                word = kw["word"]
                
                # 최근 날짜와 이전 날짜의 검색 횟수 비교
                if len(dates) >= 2:
                    recent_count = date_word_counts[dates[-1]].get(word, 0)
                    previous_count = date_word_counts[dates[-2]].get(word, 0)
                    
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
            
            # ⭐ 타임라인 데이터 생성 (날짜별 검색 횟수)
            timeline = []
            for date in sorted(dates):
                total_count = sum(date_word_counts[date].values())
                timeline.append({
                    "date": date,
                    "count": total_count
                })
            
            # ⭐ 실제 통계 계산
            total_searches = sum(word_counts.values())
            unique_keywords = len(keywords)
            
            return {
                "summary": {
                    "total_posts": total_posts,             # ⭐ 실제 게시글 수
                    "total_comments": total_comments,        # ⭐ 실제 댓글 수
                    "total_searches": total_searches,        # 총 검색 횟수
                    "unique_keywords": unique_keywords,      # 고유 키워드 수
                    "total_trends": len(keywords),
                    "new_trends": len([t for t in trends if t["change"] > 50]),
                    "rising_trends": len([t for t in trends if t["change"] > 0])
                },
                "keywords": keywords,
                "trends": trends,
                "timeline": timeline,  # ⭐ 타임라인 데이터 추가!
                "source": "dad.dothome.co.kr",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        # ⭐ 에러 발생 시 현실적인 Mock 데이터 반환 (로그인 문제 대응)
        print(f"[INFO] Using mock data due to: {e}")
        
        # 현실적인 한국어 키워드 Mock 데이터
        mock_keywords_pool = [
            "인공지능", "ChatGPT", "블록체인", "메타버스", "NFT",
            "빅데이터", "클라우드", "사이버보안", "딥러닝", "머신러닝",
            "자율주행", "전기차", "테슬라", "삼성전자", "반도체",
            "K-POP", "BTS", "축구", "야구", "배구",
            "주식", "비트코인", "부동산", "금리", "환율",
            "날씨", "미세먼지", "코로나", "백신", "건강",
            "다이어트", "운동", "요가", "필라테스", "헬스",
            "맛집", "카페", "여행", "제주도", "부산",
            "넷플릭스", "유튜브", "인스타그램", "틱톡", "페이스북",
            "아이폰", "갤럭시", "게임", "LOL", "오버워치",
            "영화", "드라마", "예능", "웹툰", "만화",
            "패션", "뷰티", "화장품", "스킨케어", "메이크업",
            "부동산", "전세", "월세", "아파트", "오피스텔",
            "취업", "이직", "연봉", "면접", "자소서"
        ]
        
        # 랜덤하게 limit개 선택하고 실제같은 빈도 부여
        selected_keywords = random.sample(
            mock_keywords_pool, 
            min(limit, len(mock_keywords_pool))
        )
        
        # 실제같은 검색 빈도 생성 (높은 빈도 ~ 낮은 빈도)
        keywords = [
            {
                "word": kw,
                "count": random.randint(1, 15)  # 현실적인 검색 횟수 (1~15회)
            }
            for kw in selected_keywords
        ]
        
        # 빈도순으로 정렬
        keywords.sort(key=lambda x: x["count"], reverse=True)
        
        # 상위 10개로 트렌드 생성
        trends = [
            {
                "keyword": kw["word"],
                "mentions": kw["count"],  # ⭐ count와 동일하게!
                "change": random.uniform(-30, 50),
                "category": random.choice(["인기", "트렌드", "이슈", "급상승", "화제"])
            }
            for kw in keywords[:10]
        ]
        
        return {
            "summary": {
                "total_trends": len(keywords),
                "new_trends": len([t for t in trends if t["change"] > 20]),
                "rising_trends": len([t for t in trends if t["change"] > 0])
            },
            "keywords": keywords,
            "trends": trends,
            "source": "mock_data",
            "note": "API 인증 문제로 Mock 데이터 사용 중",
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

class DetailedAnalysis(BaseModel):
    """상세 분석 정보"""
    bert_score: float
    bert_confidence: float
    llm_score: float
    llm_confidence: float
    llm_spam_score: float
    rule_spam_score: float
    base_score: float
    profanity_boost: float
    weights: dict
    spam_weights: dict

class EthicsAnalyzeResponse(BaseModel):
    """Ethics 분석 응답 모델"""
    text: str
    score: float = Field(..., description="비윤리 점수 (0-100)")
    confidence: float = Field(..., description="비윤리 신뢰도 (0-100)")
    spam: float = Field(..., description="스팸 지수 (0-100)")
    spam_confidence: float = Field(..., description="스팸 신뢰도 (0-100)")
    types: List[str] = Field(..., description="분석 유형 목록")
    detailed: DetailedAnalysis = Field(..., description="상세 분석 정보")


def simplify_result(result: dict) -> dict:
    """분석 결과를 간결한 형식으로 변환 (소수점 1자리)"""
    return {
        'text': result['text'],
        'score': round(result['final_score'], 1),
        'confidence': round(result['final_confidence'], 1),
        'spam': round(result['spam_score'], 1),
        'spam_confidence': round(result['spam_confidence'], 1),
        'types': result['types'],
        # 상세 정보 추가
        'detailed': {
            'bert_score': round(result['bert_score'], 1),
            'bert_confidence': round(result['bert_confidence'], 1),
            'llm_score': round(result['llm_score'], 1),
            'llm_confidence': round(result['llm_confidence'], 1),
            'llm_spam_score': round(result['llm_spam_score'], 1),
            'rule_spam_score': round(result['rule_spam_score'], 1),
            'base_score': round(result['base_score'], 1),
            'profanity_boost': round(result['profanity_boost'], 1),
            'weights': {
                'bert': round(result['weights']['bert'], 2),
                'llm': round(result['weights']['llm'], 2)
            },
            'spam_weights': {
                'llm': 0.6 if result['rule_spam_score'] < 80 else 0.3,
                'rule': 0.4 if result['rule_spam_score'] < 80 else 0.7
            }
        }
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


# ============================================
# RAG 관련 코드 (테스트 완료 전까지 주석 처리)
# ============================================
# @router.get("/risk/top", tags=["risk"])
# async def get_risk_top_users(limit: int = Query(10, ge=1, le=100, description="조회할 사용자 수")):
#     """
#     고위험 사용자 목록 조회
#     
#     - **limit**: 조회할 사용자 수 (기본값: 10, 최대: 100)
#     
#     Returns:
#     - summary: 통계 요약 정보
#     - users: 고위험 사용자 목록
#     """
#     try:
#         from chrun_backend.rag_pipeline.high_risk_store import get_recent_high_risk, init_db
#         from datetime import datetime
#         
#         # DB 초기화 (없으면 생성)
#         init_db()
#         
#         # 고위험 데이터 조회
#         risk_data = get_recent_high_risk(limit=limit)
#         
#         if not risk_data:
#             return {
#                 "summary": {
#                     "total_users": 0,
#                     "high_priority_count": 0,
#                     "medium_priority_count": 0,
#                     "avg_risk_score": 0.0
#                 },
#                 "users": []
#             }
#         
#         # 사용자별로 그룹화 (같은 user_id의 문장들을 하나의 사용자로)
#         user_dict = {}
#         for item in risk_data:
#             user_id = item['user_id']
#             if user_id not in user_dict:
#                 user_dict[user_id] = {
#                     'chunk_id': item['chunk_id'],
#                     'user_id': user_id,
#                     'username': f"사용자_{user_id}",
#                     'post_id': item.get('post_id', ''),
#                     'risk_score': item['risk_score'],
#                     'confirmed': bool(item.get('confirmed', 0)),
#                     'evidence_sentences': [],
#                     'last_activity': item.get('created_at', datetime.now().isoformat()),
#                     'feedback_at': item.get('created_at') if item.get('confirmed') else None
#                 }
#             
#             # 문장 추가
#             user_dict[user_id]['evidence_sentences'].append(item['sentence'])
#             
#             # 가장 높은 risk_score 사용
#             if item['risk_score'] > user_dict[user_id]['risk_score']:
#                 user_dict[user_id]['risk_score'] = item['risk_score']
#                 user_dict[user_id]['chunk_id'] = item['chunk_id']
#         
#         # 사용자 리스트로 변환
#         users = []
#         for user_data in user_dict.values():
#             # Priority 결정 (risk_score >= 0.7: HIGH, >= 0.5: MEDIUM, 그 외: LOW)
#             if user_data['risk_score'] >= 0.7:
#                 priority = 'HIGH'
#             elif user_data['risk_score'] >= 0.5:
#                 priority = 'MEDIUM'
#             else:
#                 priority = 'LOW'
#             
#             # 제안 조치사항 생성
#             if priority == 'HIGH':
#                 suggested_action = "즉시 연락 및 개선 조치 필요. 고위험 이탈 징후 감지됨."
#             elif priority == 'MEDIUM':
#                 suggested_action = "모니터링 강화 및 예방적 조치 권장."
#             else:
#                 suggested_action = "정기 모니터링 권장."
#             
#             users.append({
#                 **user_data,
#                 'priority': priority,
#                 'similar_patterns_count': len(user_data['evidence_sentences']),
#                 'suggested_action': suggested_action
#             })
#         
#         # risk_score 기준으로 정렬
#         users.sort(key=lambda x: x['risk_score'], reverse=True)
#         
#         # 통계 계산
#         high_priority_count = sum(1 for u in users if u['priority'] == 'HIGH')
#         medium_priority_count = sum(1 for u in users if u['priority'] == 'MEDIUM')
#         avg_risk_score = sum(u['risk_score'] for u in users) / len(users) if users else 0.0
#         
#         return {
#             "summary": {
#                 "total_users": len(users),
#                 "high_priority_count": high_priority_count,
#                 "medium_priority_count": medium_priority_count,
#                 "avg_risk_score": round(avg_risk_score, 2)
#             },
#             "users": users
#         }
#         
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"고위험 사용자 조회 중 오류: {str(e)}")


class RiskFeedbackRequest(BaseModel):
    """고위험 사용자 피드백 요청"""
    chunk_id: str
    confirmed: bool


class CheckNewPostRequest(BaseModel):
    """새 게시물 위험도 체크 요청"""
    text: str
    user_id: str
    post_id: str
    created_at: str


# @router.post("/risk/feedback", tags=["risk"])
# async def submit_risk_feedback(request_data: RiskFeedbackRequest):
#     """
#     고위험 사용자 피드백 제출
#     
#     - **chunk_id**: 피드백할 chunk_id
#     - **confirmed**: 위험 확인 여부 (true: 위험 맞음, false: 위험 아님)
#     
#     Returns:
#     - 성공 메시지
#     """
#     try:
#         from chrun_backend.rag_pipeline.high_risk_store import update_feedback, get_chunk_by_id
#         
#         # 1. 기존 SQLite 피드백 업데이트 (기존 기능 유지)
#         update_feedback(request_data.chunk_id, request_data.confirmed)
#         
#         # 2. confirmed=true인 경우에만 벡터DB에 저장
#         if request_data.confirmed:
#             try:
#                 # 2-1. SQLite에서 해당 chunk 정보 조회
#                 chunk_data = get_chunk_by_id(request_data.chunk_id)
#                 
#                 if not chunk_data:
#                     # chunk를 찾을 수 없어도 기본 피드백은 성공으로 처리
#                     print(f"[WARN] 벡터DB 저장 실패: chunk_id {request_data.chunk_id}를 찾을 수 없음")
#                 else:
#                     # 2-2. 임베딩 생성
#                     from chrun_backend.rag_pipeline.embedding_service import get_embedding
#                     sentence = chunk_data.get('sentence', '')
#                     
#                     if sentence.strip():
#                         embedding = get_embedding(sentence)
#                         
#                         # 2-3. 벡터DB에 저장할 메타데이터 구성
#                         from chrun_backend.rag_pipeline.vector_db import build_chunk_id
#                         
#                         # 안정적인 chunk_id 생성 (기존 chunk_id와 다를 수 있음)
#                         vector_chunk_id = build_chunk_id(sentence, chunk_data.get('post_id', ''))
#                         
#                         meta = {
#                             "chunk_id": vector_chunk_id,  # 벡터DB용 안정적 ID
#                             "original_chunk_id": chunk_data.get('chunk_id'),  # 원본 SQLite chunk_id
#                             "user_id": chunk_data.get('user_id', ''),
#                             "post_id": chunk_data.get('post_id', ''),
#                             "sentence": sentence,
#                             "risk_score": float(chunk_data.get('risk_score', 0.0)),
#                             "created_at": chunk_data.get('created_at', ''),
#                             "confirmed": True
#                         }
#                         
#                         # 2-4. 벡터DB에 upsert (idempotent)
#                         from chrun_backend.rag_pipeline.vector_db import get_client, upsert_confirmed_chunk
#                         
#                         client = get_client()  # 기본 경로 "./chroma_store" 사용
#                         upsert_confirmed_chunk(client, embedding, meta)
#                         
#                         print(f"[INFO] 확인된 위험 문장을 벡터DB에 저장 완료: {vector_chunk_id}")
#                     else:
#                         print(f"[WARN] 벡터DB 저장 실패: 빈 문장 (chunk_id: {request_data.chunk_id})")
#                         
#             except Exception as vector_error:
#                 # 벡터DB 저장 실패해도 기본 피드백은 성공으로 처리
#                 import traceback
#                 print(f"[ERROR] 벡터DB 저장 중 오류 발생: {vector_error}")
#                 traceback.print_exc()
#                 # 에러 로그만 남기고 API는 성공으로 응답
#         
#         return {
#             "status": "ok",
#             "message": f"피드백이 저장되었습니다. (chunk_id: {request_data.chunk_id}, confirmed: {request_data.confirmed})"
#         }
#         
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"피드백 저장 중 오류: {str(e)}")


# @router.post("/risk/check_new_post", tags=["risk"])
# async def check_new_post_risk(request_data: CheckNewPostRequest):
#     """
#     새 게시물의 위험도를 체크하여 근거 컨텍스트를 반환합니다.
#     
#     - **text**: 분석할 게시물 텍스트
#     - **user_id**: 사용자 ID
#     - **post_id**: 게시물 ID
#     - **created_at**: 생성 시간 (ISO 형식, 예: "2024-11-04T10:30:00")
#     
#     Returns:
#     - 위험도 분석을 위한 컨텍스트 (근거 문장들과 통계 정보)
#     """
#     try:
#         from chrun_backend.rag_pipeline.rag_checker import check_new_post
#         
#         # RAG 기반 위험도 체크 수행
#         context = check_new_post(
#             text=request_data.text,
#             user_id=request_data.user_id,
#             post_id=request_data.post_id,
#             created_at=request_data.created_at
#         )
#         
#         return context
#         
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"새 게시물 위험도 체크 중 오류: {str(e)}")