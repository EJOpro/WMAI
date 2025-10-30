"""인제스트 API 라우터"""
from fastapi import APIRouter, HTTPException, status, Request
from backend.models.schemas import BatchEventsRequest, ErrorResponse
from backend.services.ingest import ingest_service
from loguru import logger
import uuid

router = APIRouter(prefix="/collect", tags=["Ingest"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Events accepted"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def collect_events(request: Request, batch: BatchEventsRequest):
    """
    이벤트 배치 수집
    
    브라우저 SDK가 1분 마이크로배치로 이벤트를 전송합니다.
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Received {len(batch.events)} events")
        
        # 이벤트 인제스트
        success_count, errors = ingest_service.ingest_events(batch.events)
        
        if errors:
            logger.warning(f"[{request_id}] Partial success: {success_count}/{len(batch.events)}, errors: {errors[:5]}")
        else:
            logger.info(f"[{request_id}] All {success_count} events ingested successfully")
        
        return {
            "status": "accepted",
            "request_id": request_id,
            "accepted": success_count,
            "rejected": len(errors),
            "errors": errors[:10] if errors else []  # 최대 10개 에러만 반환
        }
        
    except Exception as e:
        logger.error(f"[{request_id}] Ingest failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

