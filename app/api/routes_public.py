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

@router.get("/ethics_analyze", response_class=HTMLResponse)
async def ethics_analyze(request: Request):
    """비윤리/스팸지수 평가"""
    return templates.TemplateResponse(
        "pages/ethics_analyze.html",
        {"request": request, "title": "비윤리/스팸지수 평가"}
    )

@router.get("/ethics_dashboard", response_class=HTMLResponse)
async def ethics_dashboard(request: Request):
    """로그기록 대시보드"""
    return templates.TemplateResponse(
        "pages/ethics_dashboard.html",
        {"request": request, "title": "로그기록 대시보드"}
    )

@router.get("/churn", response_class=HTMLResponse)
async def churn_dashboard(request: Request):
    """이탈자 분석 시스템"""
    return templates.TemplateResponse(
        "pages/churn.html",
        {"request": request, "title": "이탈자 분석 시스템"}
    )

@router.get("/risk_dashboard", response_class=HTMLResponse)
async def risk_dashboard(request: Request):
    """이탈 징후 관리자 대시보드"""
    return templates.TemplateResponse(
        "pages/risk_dashboard.html",
        {"request": request, "title": "이탈 징후 관리자 대시보드"}
    )

@router.get("/reports/admin", response_class=HTMLResponse)
async def reports_admin(request: Request):
    """신고 관리 페이지"""
    return templates.TemplateResponse(
        "pages/match_reports_admin.html",
        {"request": request, "title": "신고 관리"}
    )

@router.get("/admin/rag-check", response_class=HTMLResponse)
async def admin_rag_check(request: Request):
    """RAG 기반 위험도 분석 테스트 페이지"""
    return templates.TemplateResponse(
        "pages/admin_rag_check.html",
        {"request": request, "title": "RAG 위험도 분석"}
    )


@router.get("/admin/rag-auto", response_class=HTMLResponse)
async def admin_rag_auto(request: Request):
    """자동 RAG 판정 결과 페이지"""
    return templates.TemplateResponse(
        "pages/admin_rag_auto.html",
        {"request": request, "title": "자동 RAG 판정 결과"}
    )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지"""
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request, "title": "로그인"}
    )

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """회원가입 페이지"""
    return templates.TemplateResponse(
        "pages/register.html",
        {"request": request, "title": "회원가입"}
    )

@router.get("/board", response_class=HTMLResponse)
async def board_list(request: Request):
    """게시판 목록 페이지"""
    return templates.TemplateResponse(
        "pages/board_list.html",
        {"request": request, "title": "게시판"}
    )

@router.get("/board/write", response_class=HTMLResponse)
async def board_write(request: Request):
    """게시글 작성 페이지"""
    return templates.TemplateResponse(
        "pages/board_write.html",
        {"request": request, "title": "글쓰기"}
    )

@router.get("/board/{post_id}", response_class=HTMLResponse)
async def board_detail(request: Request, post_id: int):
    """게시글 상세 페이지"""
    return templates.TemplateResponse(
        "pages/board_detail.html",
        {"request": request, "title": "게시글", "post_id": post_id}
    )

@router.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports_page(request: Request):
    """관리자 신고 관리 페이지"""
    return templates.TemplateResponse(
        "pages/admin_reports.html",
        {"request": request, "title": "관리자 - 신고 관리"}
    )

@router.get("/admin/churn-rag-analysis", response_class=HTMLResponse)
async def churn_rag_analysis(request: Request):
    """이탈자 RAG 분석 통합 페이지"""
    return templates.TemplateResponse(
        "pages/churn_rag_analysis.html",
        {"request": request, "title": "이탈자 RAG 분석"}
    )

