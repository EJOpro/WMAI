from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Iterable, List, Optional
import pandas as pd
import redis
import json
import os
from pydantic import BaseModel
from dotenv import load_dotenv

# 환경 변수 로드 (chrun_backend 폴더의 .env 파일 우선 로드)
import pathlib
current_dir = pathlib.Path(__file__).parent
env_path = current_dir / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] .env 파일 로드됨: {env_path}")
else:
    load_dotenv()  # 프로젝트 루트의 .env 파일 시도
    print("[INFO] 프로젝트 루트의 .env 파일 로드 시도")

from .chrun_database import get_db, engine, init_db
from .chrun_models import Event, User, ChurnAnalysis, Base
from .chrun_schemas import EventCreate, ChurnMetrics, SegmentAnalysis
from .chrun_analytics import ChurnAnalyzer
from .cache_utils import (
    calculate_dataset_hash,
    generate_cache_key,
    log_cache_hit,
    log_cache_miss,
    log_cache_invalidate
)

from fastapi import APIRouter

router = APIRouter()

# FastAPI 앱 생성
app = FastAPI(title="Churn Analysis API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 로컬 테스트용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router를 앱에 포함
app.include_router(router)

# 데이터베이스 초기화는 메인 앱에서 처리

# Redis 연결 (환경 변수 기반)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()  # Redis 연결 테스트
    print(f"Redis 연결 성공: {redis_url}")
except Exception as e:
    print(f"Redis 연결 실패: {e}")
    print("Redis 없이 실행됩니다 (캐싱 비활성화)")
    redis_client = None


DEFAULT_CACHE_PATTERNS: List[str] = [
    "churn_analysis:*",
    "metrics:*",
    "segments:*",
    "trends:*",
    "report:*",
]


def _collect_cache_keys(patterns: Iterable[str]) -> List[str]:
    """지정된 패턴의 캐시 키를 모두 수집"""
    
    if not redis_client:
        return []
    
    keys: List[str] = []
    seen = set()

    for pattern in patterns:
        for key in redis_client.scan_iter(pattern):
            if key not in seen:
                seen.add(key)
                keys.append(key)

    return keys


def invalidate_cache(patterns: Optional[List[str]] = None, reason: Optional[str] = None) -> int:
    """패턴 목록에 해당하는 캐시 키를 삭제하고 삭제된 키 수를 반환
    
    Args:
        patterns: 삭제할 캐시 패턴 목록 (None이면 기본 패턴 사용)
        reason: 무효화 이유 (로그용)
    
    Returns:
        삭제된 키 수
    """
    
    if not redis_client:
        return 0

    if patterns is None:
        patterns = DEFAULT_CACHE_PATTERNS

    keys = _collect_cache_keys(patterns)

    if keys:
        redis_client.delete(*keys)
        # 구조화된 로그 출력
        for pattern in patterns:
            log_cache_invalidate(
                pattern=pattern,
                deleted_count=len(keys),
                reason=reason or "manual_invalidation"
            )

    return len(keys)

class AnalysisRequest(BaseModel):
    start_month: str  # "2025-08" (월 단위) 또는 "2025-08-01" (날짜 단위)
    end_month: str    # "2025-10" (월 단위) 또는 "2025-10-31" (날짜 단위)
    segments: dict = {"gender": True, "age_band": True, "channel": True, "combined": False, "weekday_pattern": False, "time_pattern": False, "action_type": False}
    inactivity_days: List[int] = [30, 60, 90]
    threshold: int = 1  # 최소 이벤트 수 (활성 사용자 기준)

@router.get("/")
async def root():
    return {"message": "Churn Analysis API", "version": "1.0.0"}

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now()}

@router.get("/data/status")
async def get_data_status(db: Session = Depends(get_db)):
    """데이터베이스 데이터 상태 확인"""
    try:
        # 테이블 존재 여부 확인 (MySQL의 경우)
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'events' not in tables:
            # 테이블이 없으면 빈 데이터 반환
            return {
                "has_data": False,
                "total_events": 0,
                "unique_users": 0,
                "latest_date": None,
                "oldest_date": None,
                "data_range_months": None,
                "error": "events 테이블이 존재하지 않습니다"
            }
        
        # 총 이벤트 수
        total_events = db.query(Event).count()
        
        # 고유 사용자 수
        unique_users = db.query(Event.user_hash).distinct().count()
        
        # 최신 이벤트 날짜
        latest_event = db.query(Event.created_at).order_by(Event.created_at.desc()).first()
        latest_date = latest_event.created_at if latest_event else None
        
        # 가장 오래된 이벤트 날짜
        oldest_event = db.query(Event.created_at).order_by(Event.created_at.asc()).first()
        oldest_date = oldest_event.created_at if oldest_event else None
        
        return {
            "has_data": total_events > 0,
            "total_events": total_events,
            "unique_users": unique_users,
            "latest_date": latest_date.isoformat() if latest_date else None,
            "oldest_date": oldest_date.isoformat() if oldest_date else None,
            "data_range_months": None if not (latest_date and oldest_date) else (
                (latest_date.year - oldest_date.year) * 12 + (latest_date.month - oldest_date.month) + 1
            )
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] 데이터 상태 확인 실패: {str(e)}")
        print(f"[ERROR] 상세 오류:\n{error_detail}")
        # 오류가 발생해도 빈 데이터로 반환하여 프론트엔드가 계속 동작하도록 함
        return {
            "has_data": False,
            "total_events": 0,
            "unique_users": 0,
            "latest_date": None,
            "oldest_date": None,
            "data_range_months": None,
            "error": str(e)
        }

@router.delete("/events/clear")
async def clear_events(db: Session = Depends(get_db)):
    """모든 이벤트 데이터 삭제"""
    try:
        from sqlalchemy import text
        
        # 외래키 제약 조건 비활성화 (SQLite)
        from .chrun_database import DATABASE_URL
        if DATABASE_URL.startswith('sqlite'):
            db.execute(text("PRAGMA foreign_keys=OFF"))
        
        # 관련 테이블 데이터 삭제
        db.execute(text("DELETE FROM events"))
        db.execute(text("DELETE FROM users"))
        db.execute(text("DELETE FROM monthly_metrics"))
        db.execute(text("DELETE FROM user_segments"))
        
        db.commit()
        
        # 캐시 무효화 (데이터 삭제로 인한 무효화)
        invalidate_cache(reason="data_deletion")
        
        return {"message": "모든 이벤트 데이터가 삭제되었습니다."}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터 삭제 실패: {str(e)}")

@router.post("/events/bulk")
async def upload_events(events: List[EventCreate], db: Session = Depends(get_db)):
    """이벤트 데이터 대량 업로드"""
    try:
        db_events = []
        for event_data in events:
            db_event = Event(**event_data.dict())
            db_events.append(db_event)
        
        db.bulk_save_objects(db_events)
        db.commit()
        
        # 캐시 무효화 - 모든 관련 캐시 삭제 (데이터 변경으로 인한 무효화)
        invalidate_cache(reason="data_upload")
        
        return {"message": f"{len(events)}개 이벤트가 업로드되었습니다."}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/run")
async def run_analysis(
    request: AnalysisRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """이탈 분석 실행"""
    
    # 데이터셋 해시 계산 (데이터 변경 감지)
    dataset_hash = calculate_dataset_hash(db)
    
    # LLM 모델 및 프롬프트 버전 (LLM 서비스에서 가져오기)
    from .chrun_llm_service import LLMInsightGenerator
    llm_service = LLMInsightGenerator()
    model = llm_service.model
    prompt_v = llm_service.prompt_version
    
    # 캐시 키 생성 (모든 분석 입력 반영)
    cache_key = generate_cache_key(
        dataset_hash=dataset_hash,
        start_month=request.start_month,
        end_month=request.end_month,
        segments=request.segments,
        threshold=request.threshold,
        model=model,
        prompt_v=prompt_v
    )
    
    # 캐시된 결과 확인 (Redis가 있을 때만)
    if redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                # 캐시 히트 로그
                log_cache_hit(cache_key, dataset_hash)
                return json.loads(cached_result)
        except Exception as e:
            print(f"⚠️ Redis 캐시 읽기 실패: {e}")
            log_cache_miss(cache_key, dataset_hash, reason=f"redis_error: {str(e)}")
    else:
        # Redis가 없으면 캐시 미스
        log_cache_miss(cache_key, dataset_hash, reason="redis_unavailable")
    
    try:
        # 분석 실행
        analyzer = ChurnAnalyzer(db)
        result = analyzer.run_full_analysis(
            start_month=request.start_month,
            end_month=request.end_month,
            segments=request.segments,
            inactivity_days=request.inactivity_days,
            threshold=request.threshold
        )
        
        # 결과 캐시 (1시간) - Redis가 있을 때만
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, json.dumps(result, default=str))
                # 캐시 저장 로그 (미스 후 저장)
                log_cache_miss(cache_key, dataset_hash, reason="cache_miss_new_data")
            except Exception as e:
                print(f"⚠️ Redis 캐시 쓰기 실패: {e}")
        
        # 백그라운드에서 분석 결과 DB 저장
        background_tasks.add_task(save_analysis_result, result, db)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"분석 실행 중 오류: {str(e)}")

@router.get("/analysis/metrics")
async def get_metrics(
    month: str,
    db: Session = Depends(get_db)
):
    """월별 주요 지표 조회"""
    
    cache_key = f"metrics:{month}"
    
    # 캐시된 결과 확인 (Redis가 있을 때만)
    if redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
        except Exception as e:
            print(f"⚠️ Redis 캐시 읽기 실패: {e}")
    
    try:
        analyzer = ChurnAnalyzer(db)
        metrics = analyzer.get_monthly_metrics(month)
        
        # 캐시 저장 (30분) - Redis가 있을 때만
        if redis_client:
            try:
                redis_client.setex(cache_key, 1800, json.dumps(metrics, default=str))
            except Exception as e:
                print(f"⚠️ Redis 캐시 쓰기 실패: {e}")
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/segments")
async def get_segment_analysis(
    start_month: str,
    end_month: str,
    channel: bool = False,
    action_type: bool = False,
    weekday_pattern: bool = False,
    time_pattern: bool = False,
    db: Session = Depends(get_db)
):
    """세그먼트별 이탈률 분석"""
    
    # 세그먼트 설정 구성
    segments_config = {
        "channel": channel,
        "action_type": action_type,
        "weekday_pattern": weekday_pattern,
        "time_pattern": time_pattern
    }
    
    cache_key = f"segments:{start_month}:{end_month}:{':'.join([f'{k}:{v}' for k, v in sorted(segments_config.items())])}"
    
    # 캐시된 결과 확인 (Redis가 있을 때만)
    if redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
        except Exception as e:
            print(f"⚠️ Redis 캐시 읽기 실패: {e}")
    
    try:
        analyzer = ChurnAnalyzer(db)
        segments = analyzer.get_segment_analysis(start_month, end_month, segments_config)
        
        # 캐시 저장 (1시간) - Redis가 있을 때만
        if redis_client:
            try:
                redis_client.setex(cache_key, 3600, json.dumps(segments, default=str))
            except Exception as e:
                print(f"⚠️ Redis 캐시 쓰기 실패: {e}")
        
        return segments
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/trends")
async def get_churn_trends(
    months: List[str],
    db: Session = Depends(get_db)
):
    """월별 이탈률 트렌드"""
    
    cache_key = f"trends:{':'.join(months)}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        return json.loads(cached_result)
    
    try:
        analyzer = ChurnAnalyzer(db)
        trends = analyzer.get_churn_trends(months)
        
        # 캐시 저장 (2시간)
        redis_client.setex(cache_key, 7200, json.dumps(trends, default=str))
        
        return trends
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/inactive")
async def get_inactive_users(
    month: str = None,
    days: int = 90,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """장기 미접속 사용자 목록"""
    
    try:
        # 월이 지정되면 해당 월의 마지막 날 기준, 없으면 현재 날짜 기준
        if month:
            from calendar import monthrange
            year, month_num = map(int, month.split('-'))
            last_day = monthrange(year, month_num)[1]
            month_end = f"{month}-{last_day:02d}"
            cutoff_date = datetime.strptime(month_end, "%Y-%m-%d") - timedelta(days=days)
            reference_date = datetime.strptime(month_end, "%Y-%m-%d")
        else:
            cutoff_date = datetime.now() - timedelta(days=days)
            reference_date = datetime.now()
        
        # 서브쿼리로 각 사용자의 마지막 활동일 계산
        subquery = db.query(
            Event.user_hash,
            db.func.max(Event.created_at).label('last_activity')
        ).group_by(Event.user_hash).subquery()
        
        # 장기 미접속 사용자 조회
        inactive_users = db.query(subquery).filter(
            subquery.c.last_activity < cutoff_date
        ).order_by(subquery.c.last_activity.asc()).limit(limit).all()
        
        result = [
            {
                "user_hash": user.user_hash,
                "last_activity": user.last_activity.isoformat() if isinstance(user.last_activity, datetime) else str(user.last_activity),
                "inactive_days": (reference_date - user.last_activity).days if isinstance(user.last_activity, datetime) else 0
            }
            for user in inactive_users
        ]
        
        return {
            "inactive_users": result, 
            "total_count": len(result),
            "reference_month": month,
            "cutoff_date": cutoff_date.isoformat(),
            "days": days
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/summary/{month}")
async def get_monthly_report(month: str, db: Session = Depends(get_db)):
    """월별 요약 리포트"""
    
    cache_key = f"report:{month}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        return json.loads(cached_result)
    
    try:
        analyzer = ChurnAnalyzer(db)
        report = analyzer.get_monthly_metrics(month)
        
        # 캐시 저장 (4시간)
        redis_client.setex(cache_key, 14400, json.dumps(report, default=str))
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/verification/{month}")
async def get_verification_report(
    month: str,
    threshold: int = 1,
    db: Session = Depends(get_db)
):
    """계산 검증 상세 리포트"""
    
    cache_key = f"verification:{month}:{threshold}"
    
    # 캐시된 결과 확인
    if redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
        except Exception as e:
            print(f"⚠️ Redis 캐시 읽기 실패: {e}")
    
    try:
        analyzer = ChurnAnalyzer(db)
        report = analyzer.get_detailed_verification_report(month, threshold)
        
        # 캐시 저장 (30분)
        if redis_client:
            try:
                redis_client.setex(cache_key, 1800, json.dumps(report, default=str))
            except Exception as e:
                print(f"⚠️ Redis 캐시 쓰기 실패: {e}")
        
        return report
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"검증 리포트 생성 실패: {str(e)}")

@router.delete("/cache/clear")
async def clear_cache():
    """캐시 전체 삭제"""
    try:
        deleted_count = invalidate_cache(reason="manual_clear")
        
        return {"message": f"{deleted_count}개 캐시 키가 삭제되었습니다."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/results/{analysis_id}")
async def get_analysis_result(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """저장된 분석 결과 조회 (세그먼트 분석 결과 포함)"""
    try:
        analysis = db.query(ChurnAnalysis).filter(ChurnAnalysis.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")
        
        # results JSON 파싱
        if analysis.results:
            result_data = json.loads(analysis.results)
            
            # 세그먼트 분석 결과 추출
            segments = result_data.get('segments', {})
            
            return {
                "id": analysis.id,
                "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None,
                "start_month": analysis.start_month,
                "end_month": analysis.end_month,
                "total_churn_rate": analysis.total_churn_rate,
                "active_users": analysis.active_users,
                "churned_users": analysis.churned_users,
                "reactivated_users": analysis.reactivated_users,
                "long_term_inactive": analysis.long_term_inactive,
                "segments": segments,  # 세그먼트 분석 결과 포함
                "metrics": result_data.get('metrics', {}),
                "trends": result_data.get('trends', {}),
                "insights": result_data.get('insights', []),
                "actions": result_data.get('actions', []),
                "execution_time_seconds": analysis.execution_time_seconds,
                "status": analysis.status
            }
        else:
            return {
                "id": analysis.id,
                "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None,
                "start_month": analysis.start_month,
                "end_month": analysis.end_month,
                "total_churn_rate": analysis.total_churn_rate,
                "active_users": analysis.active_users,
                "segments": {},  # 빈 세그먼트 결과
                "error": "분석 결과 데이터가 없습니다"
            }
            
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"결과 데이터 파싱 실패: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"분석 결과 조회 실패: {str(e)}")

@router.get("/analysis/results")
async def list_analysis_results(
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """저장된 분석 결과 목록 조회"""
    try:
        query = db.query(ChurnAnalysis)
        
        if start_month:
            query = query.filter(ChurnAnalysis.start_month >= start_month)
        if end_month:
            query = query.filter(ChurnAnalysis.end_month <= end_month)
        
        analyses = query.order_by(ChurnAnalysis.analysis_date.desc()).limit(limit).all()
        
        results = []
        for analysis in analyses:
            # results JSON에서 세그먼트 정보 추출
            segments_summary = {}
            if analysis.results:
                try:
                    result_data = json.loads(analysis.results)
                    segments = result_data.get('segments', {})
                    # 세그먼트 타입별 개수 요약
                    for seg_type, seg_data in segments.items():
                        if isinstance(seg_data, list):
                            segments_summary[seg_type] = len(seg_data)
                        else:
                            segments_summary[seg_type] = 1 if seg_data else 0
                except:
                    pass
            
            results.append({
                "id": analysis.id,
                "analysis_date": analysis.analysis_date.isoformat() if analysis.analysis_date else None,
                "start_month": analysis.start_month,
                "end_month": analysis.end_month,
                "total_churn_rate": analysis.total_churn_rate,
                "active_users": analysis.active_users,
                "has_segments": len(segments_summary) > 0,  # 세그먼트 분석 여부
                "segments_summary": segments_summary,  # 세그먼트 요약
                "status": analysis.status,
                "execution_time_seconds": analysis.execution_time_seconds
            })
        
        return {
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"분석 결과 목록 조회 실패: {str(e)}")

@app.get("/api/churn/analysis/monthly")
async def get_monthly_churned_users(month: str, db: Session = Depends(get_db)):
    """
    특정 월의 이탈자 목록 반환
    
    Args:
        month: 분석 월 (YYYY-MM 형식)
    
    Returns:
        이탈자 user_hash 목록 및 메트릭
    """
    try:
        analyzer = ChurnAnalyzer(db)
        
        # 월별 메트릭 계산
        metrics = analyzer.get_monthly_metrics(month)
        
        # 상세 검증 리포트에서 이탈자 목록 추출
        verification = analyzer.get_detailed_verification_report(month)
        churned_users = verification.get("user_lists", {}).get("churned_users", [])
        
        return {
            "success": True,
            "month": month,
            "churned_count": len(churned_users),
            "churned_users": churned_users[:50],  # 최대 50명
            "metrics": {
                "churn_rate": metrics.get("churn_rate", 0),
                "active_users": metrics.get("active_users", 0),
                "previous_active_users": metrics.get("previous_active_users", 0),
                "churned_users": metrics.get("churned_users", 0),
                "retained_users": metrics.get("retained_users", 0)
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"이탈자 목록 조회 실패: {str(e)}"
        )

async def save_analysis_result(result: dict, db: Session):
    """분석 결과를 DB에 저장 (백그라운드 작업)"""
    try:
        config = result.get('config', {})
        metrics = result.get('metrics', {})
        segments = result.get('segments', {})  # 세그먼트 분석 결과 확인
        
        # 세그먼트 분석 결과가 있는지 로그 출력
        if segments:
            segment_types = list(segments.keys())
            print(f"[INFO] 세그먼트 분석 결과 저장: {segment_types}")
            for seg_type, seg_data in segments.items():
                if isinstance(seg_data, list):
                    print(f"  - {seg_type}: {len(seg_data)}개 세그먼트")
                else:
                    print(f"  - {seg_type}: {type(seg_data).__name__}")
        else:
            print("[WARNING] 세그먼트 분석 결과가 없습니다!")
        
        # 전체 결과를 JSON으로 직렬화 (LONGTEXT로 저장 가능)
        results_json = json.dumps(result, default=str, ensure_ascii=False)
        results_size = len(results_json.encode('utf-8'))
        print(f"[INFO] 저장할 결과 데이터 크기: {results_size:,} bytes ({results_size/1024:.1f} KB)")
        
        analysis_record = ChurnAnalysis(
            analysis_date=datetime.now(),
            start_month=config.get('start_month'),
            end_month=config.get('end_month'),
            total_churn_rate=metrics.get('churn_rate'),
            active_users=metrics.get('active_users'),
            churned_users=metrics.get('churned_users'),
            reactivated_users=metrics.get('reactivated_users'),
            long_term_inactive=metrics.get('long_term_inactive'),
            analysis_config=json.dumps(config, ensure_ascii=False),
            results=results_json,  # 전체 result에 segments 포함됨 (LONGTEXT)
            execution_time_seconds=result.get('execution_time_seconds')
        )
        
        db.add(analysis_record)
        db.commit()
        print(f"[INFO] 분석 결과 저장 완료 (ID: {analysis_record.id}, 세그먼트 포함)")
        
    except Exception as e:
        print(f"[ERROR] 분석 결과 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

if __name__ == "__main__":
    import uvicorn
    # 데이터베이스 초기화
    print("[INFO] 데이터베이스 초기화 중...")
    init_db()
    print("[INFO] 이탈률 분석 서버 시작 중...")
    print("[INFO] http://localhost:8000 에서 API 서버 실행")
    print("[INFO] API 문서: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
