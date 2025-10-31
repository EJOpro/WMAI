from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from typing import Optional

# 환경 변수 로드
load_dotenv('match_config.env')

# FastAPI 앱 생성
app = FastAPI(
    title="커뮤니티 신고 검증 플랫폼",
    description="AI 기반 신고 내용 검증 시스템",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 요청/응답 모델
class ReportRequest(BaseModel):
    post_content: str
    reason: str

class ReportResponse(BaseModel):
    id: int
    post_content: str
    reason: str
    result_type: str
    score: int
    analysis: str
    css_class: str
    timestamp: str
    status: str
    post_action: Optional[str] = None

# 데이터베이스 함수들
def load_reports_db():
    """JSON 파일에서 신고 데이터 로드"""
    try:
        if os.path.exists('match_reports_db.json'):
            with open('match_reports_db.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []

def save_reports_db(reports):
    """JSON 파일에 신고 데이터 저장"""
    try:
        with open('match_reports_db.json', 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise Exception(f"데이터 저장 오류: {str(e)}")

def analyze_with_ai(post, reason):
    """OpenAI API를 사용하여 게시글과 신고 내용을 분석합니다."""
    
    prompt = f"""
다음 게시글과 신고 내용을 분석하여 일치 여부를 정확하게 판단해주세요.

게시글:
{post}

신고 내용:
{reason}

다음 형식으로 정확히 응답해주세요:
점수: [0-100 사이의 숫자]
판단: [일치/불일치/부분일치 중 하나]
분석: [상세한 분석 내용]
"""
    
    try:
        from openai import OpenAI
        client = OpenAI()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        # AI 응답 파싱
        ai_response = response.choices[0].message.content
        
        # 응답에서 점수, 판단, 분석 추출
        lines = ai_response.strip().split('\n')
        score = 0
        result_type = "부분일치"
        analysis = ai_response
        
        for line in lines:
            if '점수:' in line or 'score:' in line.lower():
                try:
                    score = int(''.join(filter(str.isdigit, line)))
                except:
                    score = 50
            elif '판단:' in line or 'result:' in line.lower():
                if '일치' in line and '불일치' not in line and '부분' not in line:
                    result_type = "일치"
                elif '불일치' in line:
                    result_type = "불일치"
                else:
                    result_type = "부분일치"
            elif '분석:' in line or 'analysis:' in line.lower():
                analysis = line.split(':', 1)[1].strip() if ':' in line else ai_response
        
        # CSS 클래스 결정
        if result_type == "일치":
            css_class = "result-match"
        elif result_type == "불일치":
            css_class = "result-mismatch"
        else:
            css_class = "result-partial"
        
        return {
            "score": score,
            "type": result_type,
            "css_class": css_class,
            "analysis": analysis
        }
        
    except Exception as e:
        raise Exception(f"분석 중 오류가 발생했습니다: {str(e)}")

def save_report_to_db(post_content, reason, ai_result):
    """신고를 데이터베이스에 저장 (모든 신고 저장)"""
    try:
        if not ai_result:
            raise Exception("AI 분석 결과가 없어 처리할 수 없습니다.")
            
        result_type = ai_result.get('type', '부분일치')
        confidence = ai_result.get('score', 50)
        
        # 모든 신고를 DB에 저장
        reports = load_reports_db()
        new_id = max([r.get('id', 0) for r in reports], default=0) + 1
        
        # 결과에 따른 상태 설정
        if result_type == '일치':
            status = 'completed'
            post_status = 'deleted'
            post_action = '게시글이 자동 삭제되었습니다.'
            priority = 'high'
            processing_note = 'AI 자동 처리: 신고 내용과 일치하여 게시글 삭제'
            
        elif result_type == '불일치':
            status = 'rejected'
            post_status = 'maintained'
            post_action = '게시글이 자동 유지되었습니다.'
            priority = 'low'
            processing_note = 'AI 자동 처리: 신고 내용과 불일치하여 게시글 유지'
            
        else:  # 부분일치
            status = 'pending'
            post_status = 'pending_review'
            post_action = None
            priority = 'medium'
            processing_note = None
        
        new_report = {
            'id': new_id,
            'reportDate': datetime.now().isoformat(),
            'reportType': reason,
            'reportedContent': post_content,
            'reportReason': reason,
            'reporterId': 'fastapi_user',
            'aiAnalysis': {
                'result': result_type,
                'confidence': confidence,
                'analysis': ai_result.get('analysis', '')
            },
            'status': status,
            'priority': priority,
            'assignedTo': 'AI_System' if result_type != '부분일치' else None,
            'processedDate': datetime.now().isoformat() if result_type != '부분일치' else None,
            'processingNote': processing_note,
            'postStatus': post_status,
            'postAction': post_action
        }
        
        reports.append(new_report)
        save_reports_db(reports)
        
        return new_report
        
    except Exception as e:
        raise Exception(f"데이터베이스 저장 오류: {str(e)}")

# 메인 페이지
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("match_index.html", {"request": request})

# 신고 분석 API
@app.post("/api/analyze", response_model=ReportResponse)
async def analyze_report(report: ReportRequest):
    try:
        # API 키 확인
        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다")
        
        # AI 분석 수행
        result = analyze_with_ai(report.post_content, report.reason)
        
        # 데이터베이스에 저장
        saved_report = save_report_to_db(report.post_content, report.reason, result)
        
        return ReportResponse(
            id=saved_report['id'],
            post_content=report.post_content,
            reason=report.reason,
            result_type=result['type'],
            score=result['score'],
            analysis=result['analysis'],
            css_class=result['css_class'],
            timestamp=saved_report['reportDate'],
            status=saved_report['status'],
            post_action=saved_report.get('postAction')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 예시 데이터 API
@app.get("/api/examples")
async def get_examples():
    examples = {
        "1": {
            "post": "이 제품은 정말 최고입니다! 100% 천연 성분으로만 만들어졌고, 부작용이 전혀 없어요. 의사들도 추천하는 제품이라고 하네요. 지금 주문하면 50% 할인해드려요!",
            "reason": "도배 및 광고",
            "button_text": "📢 도배 및 광고"
        },
        "2": {
            "post": "오늘 날씨가 정말 좋네요. 공원에서 산책하면서 좋은 시간을 보냈습니다. 가족들과 함께 피크닉도 했어요.",
            "reason": "욕설 및 비방",
            "button_text": "💬 욕설 및 비방"
        },
        "3": {
            "post": "김철수씨는 서울시 강남구 테헤란로 123번지에 살고 있으며, 전화번호는 010-1234-5678입니다. 최근 이혼 소송 중이라고 하네요.",
            "reason": "사생활 침해",
            "button_text": "🔒 사생활 침해"
        },
        "4": {
            "post": "유명 작가의 최신 소설 전문을 공유합니다. [소설 전체 내용 무단 게재]",
            "reason": "저작권 침해",
            "button_text": "©️ 저작권 침해"
        }
    }
    return examples

# 관리자 페이지
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("match_admin.html", {"request": request})

# 관리자 API - 신고 목록 조회
@app.get("/api/reports")
async def get_reports():
    """신고 목록 API"""
    reports = load_reports_db()
    return {
        'success': True,
        'data': reports,
        'total': len(reports)
    }

# 관리자 API - 특정 신고 조회
@app.get("/api/reports/{report_id}")
async def get_report(report_id: int):
    """특정 신고 조회 API"""
    reports = load_reports_db()
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if report:
        return {
            'success': True,
            'data': report
        }
    else:
        raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")

# 관리자 API - 신고 상태 업데이트
@app.put("/api/reports/{report_id}")
async def update_report(report_id: int, request: Request):
    """신고 상태 업데이트 API"""
    try:
        data = await request.json()
        reports = load_reports_db()
        
        # 해당 신고 찾기
        report = next((r for r in reports if r['id'] == report_id), None)
        if not report:
            raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")
        
        # 상태 업데이트
        if 'status' in data:
            new_status = data['status']
            report['status'] = new_status
            report['processedDate'] = datetime.now().isoformat()
            
            # 게시글 처리 로직
            if new_status == 'completed':  # 승인 (신고 유효 -> 게시글 삭제)
                report['postStatus'] = 'deleted'
                report['postAction'] = '게시글이 삭제되었습니다.'
            elif new_status == 'rejected':  # 반려 (신고 무효 -> 게시글 유지)
                report['postStatus'] = 'maintained'
                report['postAction'] = '게시글이 유지됩니다.'
        
        if 'processingNote' in data:
            report['processingNote'] = data['processingNote']
        
        if 'assignedTo' in data:
            report['assignedTo'] = data['assignedTo']
        
        # 저장
        save_reports_db(reports)
        
        return {
            'success': True,
            'data': report,
            'message': '신고가 성공적으로 업데이트되었습니다.'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업데이트 중 오류가 발생했습니다: {str(e)}")

# 관리자 API - 신고 삭제
@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: int):
    """신고 삭제 API"""
    try:
        reports = load_reports_db()
        
        # 해당 신고 찾기
        report_index = next((i for i, r in enumerate(reports) if r['id'] == report_id), None)
        if report_index is None:
            raise HTTPException(status_code=404, detail="신고를 찾을 수 없습니다.")
        
        # 신고 삭제
        deleted_report = reports.pop(report_index)
        save_reports_db(reports)
        
        return {
            'success': True,
            'message': '신고가 성공적으로 삭제되었습니다.',
            'data': deleted_report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 중 오류가 발생했습니다: {str(e)}")

# 관리자 API - 통계 데이터
@app.get("/api/admin/stats")
async def get_admin_stats():
    """관리자 통계 데이터 API"""
    reports = load_reports_db()
    
    # 상태별 통계
    pending_count = len([r for r in reports if r.get('status') == 'pending'])
    completed_count = len([r for r in reports if r.get('status') == 'completed'])
    rejected_count = len([r for r in reports if r.get('status') == 'rejected'])
    
    # 유형별 통계
    type_stats = {}
    for report in reports:
        report_type = report.get('reportType', '기타')
        type_stats[report_type] = type_stats.get(report_type, 0) + 1
    
    return {
        'success': True,
        'data': {
            'status_stats': {
                'pending': pending_count,
                'completed': completed_count,
                'rejected': rejected_count,
                'total': len(reports)
            },
            'type_stats': type_stats,
            'recent_reports': reports[-10:] if reports else []  # 최근 10개
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
