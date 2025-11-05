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
from .database import db_manager

# 환경 변수 로드 (프로젝트 루트의 match_config.env 파일)
env_path = os.path.join(os.path.dirname(__file__), '..', 'match_config.env')
load_dotenv(env_path)


def load_reports_db() -> List[Dict]:
    """MySQL에서 신고 데이터 로드"""
    try:
        query = """
        SELECT 
            r.id,
            r.report_date as reportDate,
            r.report_type as reportType,
            r.reported_content as reportedContent,
            r.report_reason as reportReason,
            u.username as reporterId,
            r.status,
            r.priority,
            CASE 
                WHEN r.assigned_to IS NOT NULL THEN au.username 
                ELSE 'AI_System'
            END as assignedTo,
            r.processed_date as processedDate,
            r.processing_note as processingNote,
            r.post_status as postStatus,
            r.post_action as postAction,
            ra.result,
            ra.confidence,
            ra.analysis
        FROM report r
        LEFT JOIN users u ON r.reporter_id = u.id
        LEFT JOIN users au ON r.assigned_to = au.id
        LEFT JOIN report_analysis ra ON r.id = ra.report_id
        ORDER BY r.created_at DESC
        """
        
        results = db_manager.execute_query(query)
        
        # MySQL 결과를 기존 JSON 형식으로 변환
        reports = []
        for row in results:
            report = {
                'id': row['id'],
                'reportDate': row['reportDate'].isoformat() if row['reportDate'] else None,
                'reportType': row['reportType'],
                'reportedContent': row['reportedContent'],
                'reportReason': row['reportReason'],
                'reporterId': row['reporterId'] or 'unknown',
                'status': row['status'],
                'priority': row['priority'],
                'assignedTo': row['assignedTo'],
                'processedDate': row['processedDate'].isoformat() if row['processedDate'] else None,
                'processingNote': row['processingNote'],
                'postStatus': row['postStatus'],
                'postAction': row['postAction']
            }
            
            # AI 분석 결과가 있으면 추가
            if row['result']:
                # MySQL enum을 한글로 변환
                result_mapping = {
                    'match': '일치',
                    'partial_match': '부분일치',
                    'mismatch': '불일치'
                }
                
                report['aiAnalysis'] = {
                    'result': result_mapping.get(row['result'], row['result']),
                    'confidence': row['confidence'],
                    'analysis': row['analysis']
                }
            
            reports.append(report)
        
        return reports
        
    except Exception as e:
        print(f"데이터 로드 오류: {e}")
        return []


def save_reports_db(reports: List[Dict]) -> None:
    """MySQL에 신고 데이터 저장 (레거시 호환용 - 실제로는 save_report_to_db 사용)"""
    # 이 함수는 레거시 호환성을 위해 유지하지만 실제로는 사용하지 않음
    pass


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
    신고를 MySQL 데이터베이스에 저장
    
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
        
        # 결과에 따른 상태 설정
        if result_type == '일치':
            status = 'completed'
            post_status = 'deleted'
            post_action = 'delete'
            priority = 'high'
            processing_note = 'AI 자동 처리: 신고 내용과 일치하여 게시글 삭제'
            
        elif result_type == '불일치':
            status = 'rejected'
            post_status = 'approved'
            post_action = 'keep'
            priority = 'low'
            processing_note = 'AI 자동 처리: 신고 내용과 불일치하여 게시글 유지'
            
        else:  # 부분일치
            status = 'pending'
            post_status = 'pending_review'
            post_action = 'none'
            priority = 'normal'
            processing_note = None
        
        # 기본 사용자 ID 가져오기 (fastapi_user가 없으면 생성)
        user_query = "SELECT id FROM users WHERE username = 'fastapi_user'"
        user_result = db_manager.execute_query(user_query)
        
        if not user_result:
            # fastapi_user 생성
            insert_user_query = """
            INSERT INTO users (username, password, role) 
            VALUES ('fastapi_user', 'temp_password', 'user')
            """
            reporter_id = db_manager.execute_insert(insert_user_query)
        else:
            reporter_id = user_result[0]['id']
        
        # report 테이블에 신고 저장
        insert_report_query = """
        INSERT INTO report (
            report_date, report_type, reported_content, report_reason, 
            reporter_id, status, priority, assigned_to, processed_date, 
            processing_note, post_status, post_action
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        processed_date = datetime.now() if result_type != '부분일치' else None
        assigned_to = None  # AI_System은 실제 사용자가 아니므로 NULL
        
        report_params = (
            datetime.now(),
            reason,
            post_content,
            reason,
            reporter_id,
            status,
            priority,
            assigned_to,
            processed_date,
            processing_note,
            post_status,
            post_action
        )
        
        report_id = db_manager.execute_insert(insert_report_query, report_params)
        
        # report_analysis 테이블에 AI 분석 결과 저장
        # result 값을 MySQL enum에 맞게 변환
        mysql_result = {
            '일치': 'match',
            '부분일치': 'partial_match', 
            '불일치': 'mismatch'
        }.get(result_type, 'partial_match')
        
        insert_analysis_query = """
        INSERT INTO report_analysis (report_id, result, confidence, analysis)
        VALUES (%s, %s, %s, %s)
        """
        
        analysis_params = (
            report_id,
            mysql_result,
            confidence,
            ai_result.get('analysis', '')
        )
        
        db_manager.execute_insert(insert_analysis_query, analysis_params)
        
        # 저장된 데이터 반환 (기존 JSON 형식 유지)
        return {
            'id': report_id,
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
            'postAction': '게시글이 자동 삭제되었습니다.' if post_action == 'delete' else 
                         '게시글이 자동 유지되었습니다.' if post_action == 'keep' else None
        }
        
    except Exception as e:
        raise Exception(f"데이터베이스 저장 오류: {str(e)}")


def save_analysis_only_to_db(ai_result: Dict) -> Dict:
    """
    AI 분석 결과만 report_analysis 테이블에 저장 (테스트용)
    
    Args:
        ai_result: AI 분석 결과
        
    Returns:
        저장된 분석 데이터
    """
    try:
        if not ai_result:
            raise Exception("AI 분석 결과가 없습니다")
            
        result_type = ai_result.get('type', '부분일치')
        confidence = ai_result.get('score', 50)
        
        # result 값을 MySQL enum에 맞게 변환
        mysql_result = {
            '일치': 'match',
            '부분일치': 'partial_match', 
            '불일치': 'mismatch'
        }.get(result_type, 'partial_match')
        
        # report_analysis 테이블에만 저장 (report_id는 NULL)
        insert_analysis_query = """
        INSERT INTO report_analysis (report_id, result, confidence, analysis)
        VALUES (%s, %s, %s, %s)
        """
        
        analysis_params = (
            None,  # report_id는 NULL (테스트 분석)
            mysql_result,
            confidence,
            ai_result.get('analysis', '')
        )
        
        analysis_id = db_manager.execute_insert(insert_analysis_query, analysis_params)
        
        # 테스트용 응답 데이터 반환
        return {
            'id': analysis_id,
            'reportDate': datetime.now().isoformat(),
            'status': 'test_analysis',
            'aiAnalysis': {
                'result': result_type,
                'confidence': confidence,
                'analysis': ai_result.get('analysis', '')
            }
        }
        
    except Exception as e:
        raise Exception(f"분석 데이터 저장 오류: {str(e)}")


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
    try:
        # 게시글 처리 로직
        if status == 'completed':  # 승인 (신고 유효 -> 게시글 삭제)
            post_status = 'deleted'
            post_action = 'delete'
        elif status == 'rejected':  # 반려 (신고 무효 -> 게시글 유지)
            post_status = 'approved'
            post_action = 'keep'
        else:  # pending
            post_status = 'pending_review'
            post_action = 'none'
        
        # MySQL에서 신고 상태 업데이트
        update_query = """
        UPDATE report 
        SET status = %s, processed_date = %s, processing_note = %s, 
            post_status = %s, post_action = %s
        WHERE id = %s
        """
        
        update_params = (
            status,
            datetime.now(),
            processing_note,
            post_status,
            post_action,
            report_id
        )
        
        affected_rows = db_manager.execute_update(update_query, update_params)
        
        if affected_rows == 0:
            raise ValueError("신고를 찾을 수 없습니다.")
        
        # 업데이트된 신고 데이터 조회
        updated_report = get_report_by_id(report_id)
        if not updated_report:
            raise ValueError("업데이트된 신고를 조회할 수 없습니다.")
        
        return updated_report
        
    except Exception as e:
        raise Exception(f"신고 상태 업데이트 오류: {str(e)}")


def get_report_by_id(report_id: int) -> Optional[Dict]:
    """
    ID로 신고 조회
    
    Args:
        report_id: 신고 ID
        
    Returns:
        신고 데이터 또는 None
    """
    try:
        query = """
        SELECT 
            r.id,
            r.report_date as reportDate,
            r.report_type as reportType,
            r.reported_content as reportedContent,
            r.report_reason as reportReason,
            u.username as reporterId,
            r.status,
            r.priority,
            CASE 
                WHEN r.assigned_to IS NOT NULL THEN au.username 
                ELSE 'AI_System'
            END as assignedTo,
            r.processed_date as processedDate,
            r.processing_note as processingNote,
            r.post_status as postStatus,
            r.post_action as postAction,
            ra.result,
            ra.confidence,
            ra.analysis
        FROM report r
        LEFT JOIN users u ON r.reporter_id = u.id
        LEFT JOIN users au ON r.assigned_to = au.id
        LEFT JOIN report_analysis ra ON r.id = ra.report_id
        WHERE r.id = %s
        """
        
        results = db_manager.execute_query(query, (report_id,))
        
        if not results:
            return None
        
        row = results[0]
        report = {
            'id': row['id'],
            'reportDate': row['reportDate'].isoformat() if row['reportDate'] else None,
            'reportType': row['reportType'],
            'reportedContent': row['reportedContent'],
            'reportReason': row['reportReason'],
            'reporterId': row['reporterId'] or 'unknown',
            'status': row['status'],
            'priority': row['priority'],
            'assignedTo': row['assignedTo'],
            'processedDate': row['processedDate'].isoformat() if row['processedDate'] else None,
            'processingNote': row['processingNote'],
            'postStatus': row['postStatus'],
            'postAction': '게시글이 자동 삭제되었습니다.' if row['postAction'] == 'delete' else 
                         '게시글이 자동 유지되었습니다.' if row['postAction'] == 'keep' else None
        }
        
        # AI 분석 결과가 있으면 추가
        if row['result']:
            # MySQL enum을 한글로 변환
            result_mapping = {
                'match': '일치',
                'partial_match': '부분일치',
                'mismatch': '불일치'
            }
            
            report['aiAnalysis'] = {
                'result': result_mapping.get(row['result'], row['result']),
                'confidence': row['confidence'],
                'analysis': row['analysis']
            }
        
        return report
        
    except Exception as e:
        print(f"신고 조회 오류: {e}")
        return None


def get_reports_with_filters(
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    ai_result_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict:
    """
    필터링된 신고 목록 조회 (관리자 페이지용)
    
    Args:
        status_filter: 상태 필터 (pending, completed, rejected)
        type_filter: 신고 유형 필터
        ai_result_filter: AI 결과 필터 (match, partial_match, mismatch)
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        limit: 페이지 크기
        offset: 오프셋
        
    Returns:
        필터링된 신고 목록과 총 개수
    """
    try:
        # 기본 쿼리
        where_conditions = []
        params = []
        
        # 상태 필터
        if status_filter:
            where_conditions.append("r.status = %s")
            params.append(status_filter)
        
        # 신고 유형 필터
        if type_filter:
            where_conditions.append("r.report_type = %s")
            params.append(type_filter)
        
        # AI 결과 필터
        if ai_result_filter:
            where_conditions.append("ra.result = %s")
            params.append(ai_result_filter)
        
        # 날짜 필터
        if start_date:
            where_conditions.append("DATE(r.report_date) >= %s")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("DATE(r.report_date) <= %s")
            params.append(end_date)
        
        # WHERE 절 구성
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 총 개수 쿼리
        count_query = f"""
        SELECT COUNT(DISTINCT r.id) as total
        FROM report r
        LEFT JOIN report_analysis ra ON r.id = ra.report_id
        {where_clause}
        """
        
        count_result = db_manager.execute_query(count_query, tuple(params))
        total_count = count_result[0]['total'] if count_result else 0
        
        # 데이터 쿼리
        data_query = f"""
        SELECT 
            r.id,
            r.report_date as reportDate,
            r.report_type as reportType,
            r.reported_content as reportedContent,
            r.report_reason as reportReason,
            u.username as reporterId,
            r.status,
            r.priority,
            CASE 
                WHEN r.assigned_to IS NOT NULL THEN au.username 
                ELSE 'AI_System'
            END as assignedTo,
            r.processed_date as processedDate,
            r.processing_note as processingNote,
            r.post_status as postStatus,
            r.post_action as postAction,
            ra.result,
            ra.confidence,
            ra.analysis
        FROM report r
        LEFT JOIN users u ON r.reporter_id = u.id
        LEFT JOIN users au ON r.assigned_to = au.id
        LEFT JOIN report_analysis ra ON r.id = ra.report_id
        {where_clause}
        ORDER BY r.created_at DESC
        LIMIT %s OFFSET %s
        """
        
        # 페이징 파라미터 추가
        data_params = list(params) + [limit, offset]
        results = db_manager.execute_query(data_query, tuple(data_params))
        
        # 결과 변환
        reports = []
        for row in results:
            report = {
                'id': row['id'],
                'reportDate': row['reportDate'].isoformat() if row['reportDate'] else None,
                'reportType': row['reportType'],
                'reportedContent': row['reportedContent'],
                'reportReason': row['reportReason'],
                'reporterId': row['reporterId'] or 'unknown',
                'status': row['status'],
                'priority': row['priority'],
                'assignedTo': row['assignedTo'],
                'processedDate': row['processedDate'].isoformat() if row['processedDate'] else None,
                'processingNote': row['processingNote'],
                'postStatus': row['postStatus'],
                'postAction': '게시글이 자동 삭제되었습니다.' if row['postAction'] == 'delete' else 
                             '게시글이 자동 유지되었습니다.' if row['postAction'] == 'keep' else None
            }
            
            # AI 분석 결과가 있으면 추가
            if row['result']:
                result_mapping = {
                    'match': '일치',
                    'partial_match': '부분일치',
                    'mismatch': '불일치'
                }
                
                report['aiAnalysis'] = {
                    'result': result_mapping.get(row['result'], row['result']),
                    'confidence': row['confidence'],
                    'analysis': row['analysis']
                }
            
            reports.append(report)
        
        return {
            'reports': reports,
            'total': total_count,
            'limit': limit,
            'offset': offset
        }
        
    except Exception as e:
        raise Exception(f"필터링된 신고 조회 오류: {str(e)}")


def get_dashboard_stats() -> Dict:
    """
    관리자 대시보드용 통계 데이터
    
    Returns:
        대시보드 통계 정보
    """
    try:
        # 기본 통계
        stats_query = """
        SELECT 
            COUNT(*) as total_reports,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_reports,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_reports,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_reports,
            COUNT(CASE WHEN priority = 'high' THEN 1 END) as high_priority,
            COUNT(CASE WHEN priority = 'urgent' THEN 1 END) as urgent_priority
        FROM report
        """
        
        stats_result = db_manager.execute_query(stats_query)
        basic_stats = stats_result[0] if stats_result else {}
        
        # AI 분석 통계
        ai_stats_query = """
        SELECT 
            ra.result,
            COUNT(*) as count,
            AVG(ra.confidence) as avg_confidence
        FROM report_analysis ra
        GROUP BY ra.result
        """
        
        ai_results = db_manager.execute_query(ai_stats_query)
        ai_stats = {}
        
        for row in ai_results:
            result_mapping = {
                'match': '일치',
                'partial_match': '부분일치',
                'mismatch': '불일치'
            }
            
            ai_stats[result_mapping.get(row['result'], row['result'])] = {
                'count': row['count'],
                'avg_confidence': round(row['avg_confidence'], 1) if row['avg_confidence'] else 0
            }
        
        # 신고 유형별 통계
        type_stats_query = """
        SELECT 
            report_type,
            COUNT(*) as count
        FROM report
        GROUP BY report_type
        ORDER BY count DESC
        """
        
        type_results = db_manager.execute_query(type_stats_query)
        type_stats = {row['report_type']: row['count'] for row in type_results}
        
        # 일별 신고 트렌드 (최근 7일)
        trend_query = """
        SELECT 
            DATE(report_date) as report_day,
            COUNT(*) as daily_count,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count
        FROM report
        WHERE report_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY DATE(report_date)
        ORDER BY report_day DESC
        """
        
        trend_results = db_manager.execute_query(trend_query)
        daily_trends = []
        
        for row in trend_results:
            daily_trends.append({
                'date': row['report_day'].strftime('%Y-%m-%d') if row['report_day'] else None,
                'total': row['daily_count'],
                'completed': row['completed_count'],
                'rejected': row['rejected_count']
            })
        
        # 평균 처리 시간 계산
        processing_time_query = """
        SELECT 
            AVG(TIMESTAMPDIFF(HOUR, report_date, processed_date)) as avg_processing_hours
        FROM report
        WHERE processed_date IS NOT NULL
        """
        
        processing_result = db_manager.execute_query(processing_time_query)
        avg_processing_hours = processing_result[0]['avg_processing_hours'] if processing_result else 0
        
        return {
            'basic_stats': basic_stats,
            'ai_stats': ai_stats,
            'type_stats': type_stats,
            'daily_trends': daily_trends,
            'avg_processing_hours': round(avg_processing_hours, 1) if avg_processing_hours else 0
        }
        
    except Exception as e:
        raise Exception(f"대시보드 통계 조회 오류: {str(e)}")

