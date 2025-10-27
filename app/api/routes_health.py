"""
💚 헬스체크 라우터
서버 상태 모니터링용
"""

from fastapi import APIRouter
from datetime import datetime
import sys
import psutil  # 시스템 리소스 확인 (선택사항)

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
async def health_check():
    """
    헬스체크 엔드포인트
    
    **용도:**
    - 서버 상태 확인
    - 로드 밸런서 헬스체크
    - 모니터링 도구 연동
    """
    
    try:
        # 시스템 정보 (psutil 있을 때만)
        try:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            system_info = {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory_percent}%"
            }
        except:
            system_info = {"note": "psutil not installed"}
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "Community Admin Frontend",
            "version": "1.0.0",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "system": system_info
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/ping")
async def ping():
    """간단한 핑 체크"""
    return {"message": "pong", "timestamp": datetime.now().isoformat()}

