"""
WMAA 핵심 비즈니스 로직
- AI 분석
- 데이터베이스 처리
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 환경 변수 로드 (프로젝트 루트의 match_config.env 파일)
env_path = os.path.join(os.path.dirname(__file__), '..', 'match_config.env')
load_dotenv(env_path)


def load_reports_db() -> List[Dict]:
    """JSON 파일에서 신고 데이터 로드"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'match_reports_db.json')
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"데이터 로드 오류: {e}")
    return []


def save_reports_db(reports: List[Dict]) -> None:
    """JSON 파일에 신고 데이터 저장"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'match_reports_db.json')
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise Exception(f"데이터 저장 오류: {str(e)}")


def analyze_with_ai(post: str, reason: str) -> Dict:
    """
    OpenAI API를 사용하여 게시글과 신고 내용을 분석합니다.
    
    Args:
        post: 신고된 게시글 내용
        reason: 신고 사유
        
    Returns:
        분석 결과 딕셔너리 (score, type, css_class, analysis)
    """
    
    prompt = f"""
다음 게시글과 신고 내용을 분석하여 일치 여부를 정확하게 판단해주세요.

게시글:
{post}

신고 내용:
{reason}

## 점수 부여 기준 (중요!)
- 81-100점: 신고 사유가 게시글과 명확하게 일치함. 즉시 삭제해야 할 명백한 위반
- 61-80점: 신고 사유가 게시글과 높은 확률로 일치함. 검토 후 삭제 필요  
- 31-60점: 신고 사유와 일부 관련성이 있으나 판단이 애매함. 관리자 검토 필요
- 11-30점: 신고 사유와 관련성이 낮음. 대부분 문제 없음
- 0-10점: 신고 사유가 게시글과 전혀 관련 없음. 오신고로 판단

다음 형식으로 정확히 응답해주세요:
점수: [위 기준에 따라 0-100 사이의 숫자만 입력]
판단: [판단 내용 - 점수만 참고하고 여기는 자유롭게 작성]
분석: [상세한 분석 내용과 근거]
"""
    
    try:
        # API 키 확인
        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key or api_key == 'your-api-key-here':
            raise Exception("OpenAI API 키가 설정되지 않았습니다. match_config.env 파일에 실제 API 키를 입력하세요.")
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

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
                # 판단 텍스트는 분석 내용으로만 사용 (실제 판정은 아래에서 점수 기반 결정)
                pass
            elif '분석:' in line or 'analysis:' in line.lower():
                analysis = line.split(':', 1)[1].strip() if ':' in line else ai_response
        
        # 점수 기반 자동 판정 (30-80점 부분일치)
        if score >= 81:
            result_type = "일치"
        elif score <= 29:
            result_type = "불일치"
        else:  # 30-80점
            result_type = "부분일치"
        
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


def save_report_to_db(post_content: str, reason: str, ai_result: Dict) -> Dict:
    """
    신고를 데이터베이스에 저장 (모든 신고 저장)
    
    Args:
        post_content: 게시글 내용
        reason: 신고 사유
        ai_result: AI 분석 결과
        
    Returns:
        저장된 신고 데이터
    """
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


def update_report_status(report_id: int, status: str, processing_note: Optional[str] = None) -> Dict:
    """
    신고 상태 업데이트
    
    Args:
        report_id: 신고 ID
        status: 새로운 상태 (completed, rejected, pending)
        processing_note: 처리 메모
        
    Returns:
        업데이트된 신고 데이터
    """
    reports = load_reports_db()
    
    # 해당 신고 찾기
    report = next((r for r in reports if r['id'] == report_id), None)
    if not report:
        raise ValueError("신고를 찾을 수 없습니다.")
    
    # 상태 업데이트
    report['status'] = status
    report['processedDate'] = datetime.now().isoformat()
    
    # 게시글 처리 로직
    if status == 'completed':  # 승인 (신고 유효 -> 게시글 삭제)
        report['postStatus'] = 'deleted'
        report['postAction'] = '게시글이 삭제되었습니다.'
    elif status == 'rejected':  # 반려 (신고 무효 -> 게시글 유지)
        report['postStatus'] = 'maintained'
        report['postAction'] = '게시글이 유지됩니다.'
    
    if processing_note:
        report['processingNote'] = processing_note
    
    # 저장
    save_reports_db(reports)
    
    return report


def get_report_by_id(report_id: int) -> Optional[Dict]:
    """
    ID로 신고 조회
    
    Args:
        report_id: 신고 ID
        
    Returns:
        신고 데이터 또는 None
    """
    reports = load_reports_db()
    return next((r for r in reports if r['id'] == report_id), None)

