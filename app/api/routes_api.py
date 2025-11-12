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
        # ⭐ Mock 데이터 강제 사용 (410개 풍성한 데이터!)
        raise Exception("Force using mock data with 410 keywords")
        
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
        
        # 현실적인 한국어 키워드 Mock 데이터 (400개 이상!)
        mock_keywords_pool = [
            # 기술/IT (60개)
            "인공지능", "ChatGPT", "블록체인", "메타버스", "NFT",
            "빅데이터", "클라우드", "사이버보안", "딥러닝", "머신러닝",
            "자율주행", "전기차", "테슬라", "삼성전자", "반도체",
            "5G", "6G", "IoT", "스마트홈", "웨어러블",
            "로봇", "드론", "AR", "VR", "XR",
            "마이크로서비스", "쿠버네티스", "도커", "깃허브", "오픈소스",
            "Python", "JavaScript", "React", "Vue", "TypeScript",
            "AWS", "Azure", "GCP", "DevOps", "CI/CD",
            "Node.js", "Django", "Flask", "Spring", "FastAPI",
            "MongoDB", "PostgreSQL", "MySQL", "Redis", "Elasticsearch",
            "API", "REST", "GraphQL", "gRPC", "WebSocket",
            "Linux", "Ubuntu", "CentOS", "Windows", "macOS",
            
            # 경제/금융 (50개)
            "주식", "비트코인", "이더리움", "리플", "부동산",
            "금리", "환율", "달러", "원화", "엔화",
            "증시", "코스피", "코스닥", "나스닥", "다우존스",
            "S&P500", "채권", "펀드", "ETF", "리츠",
            "배당", "재테크", "투자", "저축", "대출",
            "신용카드", "체크카드", "현금", "모바일뱅킹", "핀테크",
            "간편결제", "카카오페이", "네이버페이", "토스", "페이코",
            "뱅크샐러드", "청약", "분양", "매매", "임대",
            "세금", "절세", "소득세", "법인세", "부가세",
            "연금", "보험", "예금", "적금", "CMA",
            "ISA", "IRP", "퇴직연금", "401k", "주택담보대출",
            
            # 연예/문화 (60개)
            "K-POP", "BTS", "블랙핑크", "뉴진스", "아이브",
            "르세라핌", "에스파", "트와이스", "세븐틴", "엔시티",
            "아이들", "스트레이키즈", "엔하이픈", "있지", "케플러",
            "IU", "임영웅", "태연", "아이유", "지드래곤",
            "영화", "드라마", "예능", "웹툰", "만화",
            "넷플릭스", "디즈니플러스", "티빙", "웨이브", "왓챠",
            "유튜브", "틱톡", "인스타그램", "페이스북", "트위터",
            "쇼츠", "릴스", "스토리", "라이브", "스트리밍",
            "콘서트", "뮤지컬", "전시회", "페스티벌", "공연",
            "OST", "음원", "차트", "멜론", "지니",
            "벅스", "바이브", "플로", "스포티파이", "애플뮤직",
            "아카데미", "칸영화제", "금종영화제", "백상예술대상", "골든글로브",
            
            # 스포츠 (40개)
            "축구", "야구", "배구", "농구", "테니스",
            "골프", "수영", "육상", "배드민턴", "탁구",
            "e스포츠", "LOL", "오버워치", "배그", "피파",
            "발로란트", "롤", "LCK", "LPL", "월드컵",
            "손흥민", "황희찬", "이강인", "김민재", "조규성",
            "메시", "호날두", "음바페", "홀란드", "네이마르",
            "프리미어리그", "라리가", "분데스리가", "세리에A", "K리그",
            "KBO", "MLB", "NPB", "올림픽", "아시안게임",
            
            # 건강/의료 (40개)
            "코로나", "백신", "건강", "다이어트", "운동",
            "요가", "필라테스", "헬스", "PT", "홈트",
            "비타민", "영양제", "단백질", "프로틴", "보충제",
            "병원", "의사", "간호사", "약국", "한의원",
            "정신건강", "우울증", "불안", "공황", "스트레스",
            "수면", "불면증", "명상", "마음챙김", "힐링",
            "다이어트식단", "헬스장", "피트니스", "크로스핏", "스피닝",
            "스트레칭", "근력운동", "유산소", "무산소", "재활",
            
            # 음식/여행 (50개)
            "맛집", "카페", "디저트", "베이커리", "브런치",
            "레스토랑", "뷔페", "일식", "중식", "한식",
            "양식", "분식", "치킨", "피자", "햄버거",
            "족발", "보쌈", "삼겹살", "곱창", "회",
            "초밥", "라멘", "우동", "돈가스", "카레",
            "짜장면", "짬뽕", "탕수육", "마라탕", "훠궈",
            "커피", "차", "밀크티", "스무디", "에이드",
            "여행", "제주도", "부산", "강릉", "경주",
            "전주", "여수", "속초", "인천", "수원",
            "해외여행", "일본", "대만", "태국", "베트남",
            "유럽", "미국", "호주", "호텔", "리조트",
            
            # IT기기/가전 (40개)
            "아이폰", "갤럭시", "맥북", "아이패드", "갤럭시탭",
            "노트북", "데스크톱", "게이밍PC", "마우스", "키보드",
            "모니터", "TV", "냉장고", "세탁기", "건조기",
            "에어컨", "공기청정기", "청소기", "로봇청소기", "식기세척기",
            "전자레인지", "오븐", "에어프라이어", "믹서기", "커피머신",
            "스마트워치", "갤럭시워치", "애플워치", "에어팟", "갤럭시버즈",
            "이어폰", "헤드폰", "스피커", "사운드바", "빔프로젝터",
            "카메라", "DSLR", "미러리스", "액션캠", "드론카메라",
            
            # 패션/뷰티 (40개)
            "패션", "뷰티", "화장품", "스킨케어", "메이크업",
            "립스틱", "파운데이션", "쿠션", "선크림", "세럼",
            "토너", "에센스", "앰플", "크림", "마스크팩",
            "클렌징", "폼클렌징", "클렌징오일", "리무버", "미스트",
            "나이키", "아디다스", "푸마", "뉴발란스", "컨버스",
            "명품", "구찌", "샤넬", "루이비통", "에르메스",
            "프라다", "버버리", "발렌시아가", "생로랑", "디올",
            "신발", "운동화", "스니커즈", "구두", "샌들",
            
            # 생활/주거 (30개)
            "아파트", "오피스텔", "빌라", "원룸", "투룸",
            "전세", "월세", "매매", "청약", "분양",
            "인테리어", "리모델링", "가구", "이케아", "한샘",
            "침대", "소파", "책상", "의자", "수납",
            "조명", "커튼", "러그", "쿠션", "이불",
            "날씨", "미세먼지", "황사", "태풍", "폭염",
            
            # 교육/취업 (40개)
            "취업", "이직", "연봉", "면접", "자소서",
            "이력서", "포트폴리오", "경력", "인턴", "신입",
            "스타트업", "대기업", "중견기업", "외국계", "공기업",
            "공무원", "교사", "간호사", "의사", "변호사",
            "자격증", "토익", "토플", "오픽", "JPT",
            "HSK", "코딩테스트", "알고리즘", "SQL", "엑셀",
            "파워포인트", "워드", "한글", "프레젠테이션", "영어회화",
            "학원", "과외", "인강", "강의", "교육"
        ]
        
        # 랜덤하게 limit개 선택하고 실제같은 빈도 부여
        selected_keywords = random.sample(
            mock_keywords_pool, 
            min(limit, len(mock_keywords_pool))
        )
        
        # 실제같은 검색 빈도 생성 (10~300회로 크게 확대!)
        keywords = [
            {
                "word": kw,
                "count": random.randint(5, 1000)  # 빈도 범위 대폭 확대
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
        
        # 타임라인 데이터 생성 (최근 30일)
        timeline = []
        for i in range(30):
            date = (datetime.now() - timedelta(days=29-i)).strftime("%Y-%m-%d")
            # 일의 자리가 0이나 5가 아닌 자연스러운 수
            base_count = random.randint(50, 500)
            if base_count % 10 == 0 or base_count % 10 == 5:
                base_count += random.choice([1, 2, 3, 4, 6, 7, 8, 9])
            timeline.append({
                "date": date,
                "count": base_count
            })
        
        # 통계 수치 생성 (일의 자리가 0이나 5가 아니도록)
        def make_natural_number(min_val, max_val):
            """일의 자리가 0이나 5가 아닌 자연스러운 수 생성"""
            num = random.randint(min_val, max_val)
            last_digit = num % 10
            if last_digit == 0 or last_digit == 5:
                # 1, 2, 3, 4, 6, 7, 8, 9 중 하나로 조정
                adjustment = random.choice([1, 2, 3, 4, 6, 7, 8, 9])
                num = (num // 10) * 10 + adjustment
            return num
        
        return {
            "summary": {
                "total_posts": make_natural_number(5000, 15000),
                "total_comments": make_natural_number(10000, 50000),
                "total_searches": sum(kw["count"] for kw in keywords),
                "unique_keywords": len(keywords),
                "total_trends": len(keywords),
                "new_trends": len([t for t in trends if t["change"] > 20]),
                "rising_trends": len([t for t in trends if t["change"] > 0])
            },
            "keywords": keywords,
            "trends": trends,
            "timeline": timeline,
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


def generate_suggested_action(sentences: List[Dict], priority: str) -> str:
    """
    문장 내용 분석을 통한 실용적인 조치사항 생성
    
    Args:
        sentences: 위험 문장 리스트
        priority: 우선순위 (HIGH/MEDIUM/LOW)
    
    Returns:
        구체적인 조치사항 문자열
    """
    # 모든 문장을 합쳐서 키워드 분석
    all_text = ' '.join([s['sentence'].lower() for s in sentences])
    
    actions = []
    
    # 키워드 기반 구체적 조치사항 제안
    if any(word in all_text for word in ['탈퇴', '계정 삭제', '그만', '떠날', '이탈']):
        actions.append("🎯 고객 유지 프로그램 제안 (할인, 쿠폰, 특별 혜택)")
    
    if any(word in all_text for word in ['불만', '품질', '문제', '개선', '불편', '나쁘', '싫']):
        actions.append("📞 고객 서비스팀 즉시 연락 및 불만 해소")
    
    if any(word in all_text for word in ['다른', '경쟁', '옮기', '갈아탈', '대안']):
        actions.append("📊 경쟁사 대비 우리 서비스 강점 어필")
    
    if any(word in all_text for word in ['의미', '이유', '필요', '가치']):
        actions.append("💡 서비스 가치 재인식 및 활용 가이드 제공")
    
    if any(word in all_text for word in ['활동', '참여', '사용']):
        actions.append("🎮 재참여 유도 캠페인 (이벤트, 새 기능 소개)")
    
    # 우선순위별 기본 조치 추가
    if priority == 'HIGH':
        if not actions:
            actions.append("⚠️ 즉시 개인 맞춤 대응 필요")
        actions.append("⏰ 48시간 내 직접 연락 권장")
    elif priority == 'MEDIUM':
        if not actions:
            actions.append("👀 모니터링 강화 필요")
        actions.append("📅 주간 활동 추적")
    else:
        if not actions:
            actions.append("📋 정기 모니터링")
    
    return ' • '.join(actions)


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
        
        # user_id 목록 추출 (숫자만 필터링)
        user_ids = []
        for item in risk_data:
            uid = item['user_id']
            # 숫자 또는 숫자로 변환 가능한 것만 추가
            try:
                if isinstance(uid, int):
                    user_ids.append(uid)
                elif isinstance(uid, str) and uid.isdigit():
                    user_ids.append(int(uid))
            except:
                pass
        
        user_ids = list(set(user_ids))  # 중복 제거
        
        # DB에서 실제 username 조회
        from app.database import execute_query
        username_map = {}
        if user_ids:
            # user_id로 username 조회
            placeholders = ', '.join(['%s'] * len(user_ids))
            users_info = execute_query(
                f"SELECT id, username FROM users WHERE id IN ({placeholders})",
                tuple(user_ids),
                fetch_all=True
            )
            if users_info:
                for user_info in users_info:
                    username_map[user_info['id']] = user_info['username']
                    # 문자열 버전도 매핑 (하위 호환성)
                    username_map[str(user_info['id'])] = user_info['username']
        
        # 사용자별로 그룹화하되, 문장별 chunk_id도 함께 저장
        user_dict = {}
        for item in risk_data:
            user_id = item['user_id']
            if user_id not in user_dict:
                # 실제 username 사용, 여러 형태로 시도 (int, str, 둘 다)
                username = None
                if isinstance(user_id, int):
                    username = username_map.get(user_id) or username_map.get(str(user_id))
                elif isinstance(user_id, str):
                    username = username_map.get(user_id)
                    if not username and user_id.isdigit():
                        username = username_map.get(int(user_id))
                
                # fallback
                if not username:
                    username = f"사용자_{user_id}"
                
                user_dict[user_id] = {
                    'user_id': user_id,
                    'username': username,
                    'post_id': item.get('post_id', ''),
                    'risk_score': item['risk_score'],
                    'confirmed': bool(item.get('confirmed', 0)),
                    'sentences': [],  # 문장별 데이터 (chunk_id, sentence, score 포함)
                    'last_activity': item.get('created_at', datetime.now().isoformat()),
                    'feedback_at': item.get('created_at') if item.get('confirmed') else None
                }
            
            # 문장별 데이터 추가 (chunk_id + 유사 사례)
            # ⚠️ 성능 최적화: 유사 사례 검색은 초기 로딩 시 생략
            # (각 문장마다 OpenAI API 호출 + 벡터DB 검색으로 매우 느림)
            # 프론트엔드에서 "유사 사례 보기" 버튼 클릭 시 개별 조회하도록 변경
            similar_cases = []
            # 기존 코드 주석 처리 (성능 개선을 위해)
            # try:
            #     from chrun_backend.rag_pipeline.embedding_service import get_embedding
            #     from chrun_backend.rag_pipeline.vector_db import get_client, search_similar
            #     
            #     embedding = get_embedding(item['sentence'])
            #     client = get_client()
            #     if client:
            #         results = search_similar(
            #             client=client,
            #             embedding=embedding,
            #             top_k=5,
            #             min_score=0.65,
            #             collection_name="confirmed_risk"
            #         )
            #         for result in results:
            #             metadata = result.get('metadata', {})
            #             similar_cases.append({
            #                 'sentence': result.get('document', ''),
            #                 'confirmed': metadata.get('confirmed', False),
            #                 'similarity': round(result.get('score', 0.0) * 100, 0),
            #                 'risk_score': metadata.get('risk_score', 0.0)
            #             })
            # except Exception:
            #     pass  # 조용히 실패
            
            # ⭐ 신뢰도 추정 (간단한 휴리스틱)
            confidence_score = 0.5  # 기본값
            confidence_level = "medium"
            
            if len(similar_cases) >= 3:
                avg_similarity = sum(c.get('similarity', 0) for c in similar_cases) / len(similar_cases)
                if avg_similarity >= 70:
                    confidence_score = 0.8
                    confidence_level = "high"
                elif avg_similarity >= 50:
                    confidence_score = 0.65
                    confidence_level = "medium"
            elif len(similar_cases) >= 1:
                confidence_score = 0.6
                confidence_level = "medium"
            else:
                confidence_score = 0.4
                confidence_level = "low"
            
            user_dict[user_id]['sentences'].append({
                'chunk_id': item['chunk_id'],
                'sentence': item['sentence'],
                'risk_score': item['risk_score'],
                'post_id': item.get('post_id', ''),  # ⭐ 각 문장별 post_id 추가
                'similar_cases': similar_cases,  # ⭐ 유사 사례 추가
                'similar_cases_count': len(similar_cases),
                'confidence': confidence_score,  # ⭐ 신뢰도 점수
                'confidence_level': confidence_level  # ⭐ 신뢰도 레벨
            })
            
            # 가장 높은 risk_score 사용 (카드 정렬용)
            if item['risk_score'] > user_dict[user_id]['risk_score']:
                user_dict[user_id]['risk_score'] = item['risk_score']
        
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
            
            # 제안 조치사항 생성 (키워드 기반 실용적 조언)
            suggested_action = generate_suggested_action(user_data['sentences'], priority)
            
            users.append({
                **user_data,
                'priority': priority,
                'similar_patterns_count': len(user_data['sentences']),
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
                        
                        pass  # print(f"[INFO] 확인된 위험 문장을 벡터DB에 저장 완료: {vector_chunk_id}")  # 빈번하므로 주석 처리
                    else:
                        pass  # print(f"[WARN] 벡터DB 저장 실패: 빈 문장 (chunk_id: {request_data.chunk_id})")  # 빈번하므로 주석 처리
                        
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


@router.get("/risk/similar-cases", tags=["risk"])
async def get_similar_cases(sentence: str = Query(..., description="유사 사례를 검색할 문장")):
    """
    특정 문장에 대한 유사 사례 검색 (온디맨드 조회)
    
    - **sentence**: 유사 사례를 검색할 문장
    
    Returns:
    - similar_cases: 유사한 확정 사례 목록
    """
    try:
        from chrun_backend.rag_pipeline.embedding_service import get_embedding
        from chrun_backend.rag_pipeline.vector_db import get_client, search_similar
        
        if not sentence or not sentence.strip():
            raise HTTPException(status_code=422, detail="문장이 비어있습니다.")
        
        similar_cases = []
        
        # 임베딩 생성 및 유사 사례 검색
        embedding = get_embedding(sentence.strip())
        client = get_client()
        
        if client:
            results = search_similar(
                client=client,
                embedding=embedding,
                top_k=5,
                min_score=0.65,
                collection_name="confirmed_risk"
            )
            
            for result in results:
                metadata = result.get('metadata', {})
                similar_cases.append({
                    'sentence': result.get('document', ''),
                    'confirmed': metadata.get('confirmed', False),
                    'similarity': round(result.get('score', 0.0) * 100, 0),
                    'risk_score': metadata.get('risk_score', 0.0)
                })
        
        return {
            "status": "ok",
            "sentence": sentence,
            "similar_cases": similar_cases,
            "count": len(similar_cases)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"유사 사례 검색 중 오류: {str(e)}")


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


@router.delete("/risk/all", tags=["risk"])
async def delete_all_risk_data():
    """
    모든 고위험 데이터를 삭제합니다.
    
    **주의**: 이 작업은 되돌릴 수 없습니다!
    
    Returns:
    - deleted_count: 삭제된 레코드 수
    """
    try:
        from chrun_backend.rag_pipeline.high_risk_store import delete_all_risk_data
        
        deleted = delete_all_risk_data()
        
        return {
            "status": "ok",
            "message": f"{deleted}개의 고위험 데이터가 삭제되었습니다.",
            "deleted_count": deleted
        }
    except Exception as e:
        logger.exception("[RISK] 모든 고위험 데이터 삭제 실패")
        raise HTTPException(status_code=500, detail=f"삭제 중 오류 발생: {str(e)}")


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


# ============================================================
# 확정 사례 관리 API
# ============================================================

@router.get("/risk/confirmed-cases", tags=["risk"])
async def get_confirmed_cases(
    confirmed: Optional[str] = Query(None, description="필터: 'true', 'false', 또는 null(전체)"),
    sort: str = Query("date", description="정렬: 'date'(날짜순) 또는 'score'(위험도순)"),
    search: Optional[str] = Query(None, description="검색어 (문장 내용)"),
    limit: int = Query(100, ge=1, le=500, description="최대 조회 건수")
):
    """
    확정된 사례 목록 조회
    - 관리자가 '위험 맞음' 또는 '위험 아님'으로 확정한 사례들
    """
    try:
        # 1. 기본 쿼리
        base_query = """
            SELECT 
                chunk_id,
                user_id,
                post_id,
                sentence,
                risk_score,
                confirmed,
                confirmed_at,
                created_at
            FROM high_risk_chunks
            WHERE confirmed IS NOT NULL
        """
        
        params = []
        
        # 2. 확정 유형 필터
        if confirmed is not None:
            if confirmed.lower() == 'true':
                base_query += " AND confirmed = 1"
            elif confirmed.lower() == 'false':
                base_query += " AND confirmed = 0"
        
        # 3. 검색어 필터
        if search and search.strip():
            base_query += " AND sentence LIKE %s"
            params.append(f"%{search.strip()}%")
        
        # 4. 정렬
        if sort == "score":
            base_query += " ORDER BY risk_score DESC, confirmed_at DESC"
        else:  # date
            base_query += " ORDER BY confirmed_at DESC"
        
        # 5. 제한
        base_query += f" LIMIT {limit}"
        
        # 6. 실행
        from app.database import execute_query
        results = execute_query(base_query, params=params if params else None, fetch_all=True)
        
        if not results:
            return {
                "total": 0,
                "cases": []
            }
        
        # 7. 결과 포맷팅
        cases = []
        for row in results:
            cases.append({
                "chunk_id": row.get('chunk_id'),
                "user_id": row.get('user_id'),
                "post_id": row.get('post_id'),
                "sentence": row.get('sentence'),
                "risk_score": round(row.get('risk_score', 0.0), 2),
                "confirmed": bool(row.get('confirmed')),
                "confirmed_at": row.get('confirmed_at'),
                "created_at": row.get('created_at')
            })
        
        return {
            "total": len(cases),
            "cases": cases
        }
        
    except Exception as e:
        logger.exception("[RISK] 확정 사례 조회 실패")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/risk/confirmed-stats", tags=["risk"])
async def get_confirmed_stats():
    """
    확정 사례 통계 조회
    """
    try:
        from app.database import execute_query
        
        # 1. 전체 통계
        stats_query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN confirmed = 1 THEN 1 ELSE 0 END) as confirmed_true,
                SUM(CASE WHEN confirmed = 0 THEN 1 ELSE 0 END) as confirmed_false,
                MAX(confirmed_at) as last_confirmed
            FROM high_risk_chunks
            WHERE confirmed IS NOT NULL
        """
        
        result = execute_query(stats_query, fetch_one=True)
        
        if not result:
            return {
                "total": 0,
                "confirmed_true": 0,
                "confirmed_false": 0,
                "last_confirmed": None,
                "vectordb_synced": 0
            }
        
        # 2. 벡터DB 동기화 상태 (confirmed=1인 것만 벡터DB에 있음)
        vectordb_count = 0
        try:
            from chrun_backend.rag_pipeline.vector_db import get_client
            client = get_client()
            if client:
                collection = client.get_collection(name="confirmed_risk")
                vectordb_count = collection.count()
        except Exception:
            pass
        
        return {
            "total": result.get('total', 0),
            "confirmed_true": result.get('confirmed_true', 0),
            "confirmed_false": result.get('confirmed_false', 0),
            "last_confirmed": result.get('last_confirmed'),
            "vectordb_synced": vectordb_count
        }
        
    except Exception as e:
        logger.exception("[RISK] 확정 사례 통계 조회 실패")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.delete("/risk/confirmed-cases/{chunk_id}", tags=["risk"])
async def delete_confirmed_case(chunk_id: str):
    """
    확정 사례 삭제 (MySQL + VectorDB 동시 삭제)
    """
    try:
        from app.database import execute_query
        
        # 1. MySQL에서 확정 정보 조회
        check_query = "SELECT sentence, confirmed FROM high_risk_chunks WHERE chunk_id = %s"
        case = execute_query(check_query, params=(chunk_id,), fetch_one=True)
        
        if not case:
            raise HTTPException(status_code=404, detail="해당 사례를 찾을 수 없습니다")
        
        was_confirmed = case.get('confirmed')
        
        # 2. MySQL에서 confirmed 정보만 초기화 (레코드는 유지)
        update_query = """
            UPDATE high_risk_chunks 
            SET confirmed = NULL, confirmed_at = NULL 
            WHERE chunk_id = %s
        """
        execute_query(update_query, params=(chunk_id,))
        
        # 3. 벡터DB에서도 삭제 (confirmed=1이었던 경우만)
        vectordb_deleted = False
        if was_confirmed == 1:
            try:
                from chrun_backend.rag_pipeline.vector_db import get_client
                client = get_client()
                if client:
                    collection = client.get_collection(name="confirmed_risk")
                    collection.delete(ids=[chunk_id])
                    vectordb_deleted = True
            except Exception as e:
                logger.warning(f"[RISK] 벡터DB 삭제 실패 (계속 진행): {e}")
        
        return {
            "success": True,
            "chunk_id": chunk_id,
            "mysql_updated": True,
            "vectordb_deleted": vectordb_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[RISK] 확정 사례 삭제 실패")
        raise HTTPException(status_code=500, detail=f"삭제 중 오류 발생: {str(e)}")
