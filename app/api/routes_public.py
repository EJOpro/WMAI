from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """메인 페이지 - 검색창 및 주요 메뉴"""
    return templates.TemplateResponse(
        "pages/home.html",
        {"request": request, "title": "홈"}
    )

@router.get("/api-console", response_class=HTMLResponse)
async def api_console(request: Request):
    """API 콘솔 - API 테스트 인터페이스"""
    return templates.TemplateResponse(
        "pages/api_console.html",
        {"request": request, "title": "API 콘솔"}
    )

@router.get("/bounce", response_class=HTMLResponse)
async def bounce(request: Request):
    """이탈률 대시보드"""
    return templates.TemplateResponse(
        "pages/bounce.html",
        {"request": request, "title": "방문객 이탈률"}
    )

@router.get("/trends", response_class=HTMLResponse)
async def trends(request: Request):
    """트렌드 대시보드"""
    return templates.TemplateResponse(
        "pages/trends.html",
        {"request": request, "title": "트렌드 분석"}
    )

@router.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    """신고글 분류평가"""
    return templates.TemplateResponse(
        "pages/match_reports.html",
        {"request": request, "title": "신고글 분류"}
    )

@router.get("/hate", response_class=HTMLResponse)
async def hate(request: Request):
    """혐오지수 평가"""
    return templates.TemplateResponse(
        "pages/hate.html",
        {"request": request, "title": "혐오지수 평가"}
    )

@router.get("/reports/admin", response_class=HTMLResponse)
async def reports_admin(request: Request):
    """신고 관리 페이지"""
    return templates.TemplateResponse(
        "pages/match_reports_admin.html",
        {"request": request, "title": "신고 관리"}
    )

