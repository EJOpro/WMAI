"""
게시판 API 라우터
게시글 및 댓글 CRUD 기능 제공
"""
from fastapi import APIRouter, Request, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Tuple
from datetime import datetime
from app.auth import get_current_user
from app.database import execute_query, get_db_connection
from app.settings import settings
import pymysql
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import time
import uuid
import json
import shutil
from pathlib import Path

router = APIRouter(tags=["board"])

# 백그라운드 작업용 executor
background_executor = ThreadPoolExecutor(max_workers=4)

# 이미지 업로드 설정
UPLOAD_DIR = Path("app/static/uploads/board")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGES = 5  # 게시글당 최대 이미지 개수

# 업로드 디렉토리 확인 및 생성
if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] 업로드 디렉토리 생성: {UPLOAD_DIR}")


def validate_image(file: UploadFile) -> Tuple[bool, str]:
    """
    이미지 파일 검증
    
    Args:
        file: 업로드된 파일
    
    Returns:
        (검증 성공 여부, 에러 메시지)
    """
    # 파일 확장자 검증
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"허용되지 않는 파일 형식입니다. 허용 형식: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # MIME 타입 검증
    if file.content_type not in ALLOWED_MIME_TYPES:
        return False, f"허용되지 않는 파일 타입입니다. (MIME: {file.content_type})"
    
    return True, ""


async def save_image(file: UploadFile) -> dict:
    """
    이미지 파일 저장
    
    Args:
        file: 업로드된 파일
    
    Returns:
        이미지 메타데이터 딕셔너리
    
    Raises:
        HTTPException: 파일 크기 초과 또는 저장 실패
    """
    # 파일 크기 검증
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 크기가 너무 큽니다. 최대 {MAX_FILE_SIZE / 1024 / 1024}MB까지 업로드 가능합니다."
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 파일은 업로드할 수 없습니다."
        )
    
    # 고유한 파일명 생성 (UUID)
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # 파일 저장
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        print(f"[INFO] 이미지 저장 완료: {unique_filename} ({file_size} bytes)")
        
        return {
            "filename": unique_filename,
            "original_name": file.filename,
            "size": file_size
        }
    except Exception as e:
        print(f"[ERROR] 이미지 저장 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 저장 중 오류가 발생했습니다."
        )


def delete_images(images_json: str):
    """
    게시글의 이미지 파일들 삭제
    
    Args:
        images_json: 이미지 정보가 담긴 JSON 문자열
    """
    if not images_json:
        return
    
    try:
        images = json.loads(images_json)
        if not isinstance(images, list):
            return
        
        for image in images:
            filename = image.get("filename")
            if filename:
                file_path = UPLOAD_DIR / filename
                if file_path.exists():
                    try:
                        file_path.unlink()
                        print(f"[INFO] 이미지 삭제 완료: {filename}")
                    except Exception as e:
                        print(f"[WARN] 이미지 삭제 실패: {filename}, {e}")
    except json.JSONDecodeError:
        print(f"[WARN] 이미지 JSON 파싱 실패: {images_json}")
    except Exception as e:
        print(f"[ERROR] 이미지 삭제 중 오류: {e}")


# Ethics 분석 관련 import
try:
    from ethics.ethics_hybrid_predictor import HybridEthicsAnalyzer
    from ethics.ethics_db_logger import db_logger
    ETHICS_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Ethics 모듈 import 실패: {e}")
    ETHICS_AVAILABLE = False

# 이미지 분석 관련 import
try:
    from ethics.nsfw_detector import get_nsfw_detector
    from ethics.vision_analyzer import get_vision_analyzer
    from ethics.image_db_logger import image_logger
    IMAGE_ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] Image 분석 모듈 import 실패: {e}")
    IMAGE_ANALYSIS_AVAILABLE = False

# 전역 analyzer 인스턴스
ethics_analyzer = None


def get_ethics_analyzer():
    """Ethics analyzer 싱글톤 패턴"""
    global ethics_analyzer
    if not ETHICS_AVAILABLE:
        return None
    
    if ethics_analyzer is None:
        try:
            ethics_analyzer = HybridEthicsAnalyzer()
            print("[INFO] Ethics analyzer 초기화 완료")
        except Exception as e:
            print(f"[ERROR] Ethics analyzer 초기화 실패: {e}")
            return None
    return ethics_analyzer


def should_block_content(result: dict) -> Tuple[bool, str]:
    """
    분석 결과를 바탕으로 차단 여부 결정
    
    Returns:
        (차단여부, 차단사유)
    """
    # 즉시 차단 (auto_blocked) 최우선 체크
    if result.get('auto_blocked', False):
        auto_block_reason = result.get('auto_block_reason', 'unknown')
        if auto_block_reason == 'immoral':
            return True, "관리자 확정 비윤리 사례와 유사하여 즉시 차단되었습니다"
        elif auto_block_reason == 'spam':
            return True, "관리자 확정 스팸 사례와 유사하여 즉시 차단되었습니다"
        else:
            return True, "관리자 확정 사례와 유사하여 즉시 차단되었습니다"
    
    final_score = result.get('final_score', 0)
    final_confidence = result.get('final_confidence', 0)
    spam_score = result.get('spam_score', 0)
    spam_confidence = result.get('spam_confidence', 0)
    
    # None 값 처리 (즉시 차단이 아닌데 None이면 0으로 처리)
    if final_score is None:
        final_score = 0
    if final_confidence is None:
        final_confidence = 0
    if spam_score is None:
        spam_score = 0
    if spam_confidence is None:
        spam_confidence = 0
    
    # 차단 기준 1: 비윤리 점수 >= 80 AND 신뢰도 >= 80
    if final_score >= 80 and final_confidence >= 80:
        return True, "부적절한 내용이 포함되어 있습니다"
    
    # 차단 기준 2: 비윤리 점수 >= 90 AND 신뢰도 >= 70
    if final_score >= 90 and final_confidence >= 70:
        return True, "부적절한 내용이 포함되어 있습니다"
    
    # 차단 기준 3: 스팸 점수 >= 70 AND 신뢰도 >= 70
    if spam_score >= 70 and spam_confidence >= 70:
        return True, "스팸으로 의심되는 내용이 포함되어 있습니다"
    
    return False, ""


async def analyze_and_log_content(text: str, ip_address: str = None, user_agent: str = None) -> Tuple[str, dict, str]:
    """
    콘텐츠 분석 및 로그 저장
    
    Args:
        text: 분석할 텍스트
        ip_address: 클라이언트 IP 주소
        user_agent: User Agent 문자열
    
    Returns:
        (status, result, block_reason)
    """
    try:
        analyzer = get_ethics_analyzer()
        if analyzer is None:
            print("[WARN] Ethics analyzer 없음 - 분석 건너뜀")
            return 'exposed', None, ""
        
        # 분석 시간 측정 시작
        start_time = time.time()
        
        # 분석 실행
        result = analyzer.analyze(text)
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        
        # 차단 여부 결정
        should_block, block_reason = should_block_content(result)
        status = 'blocked' if should_block else 'exposed'
        
        # 로그 저장 (ethics_logs 테이블)
        try:
            log_id = db_logger.log_analysis(
                text=text,
                score=result['final_score'],
                confidence=result['final_confidence'],
                spam=result['spam_score'],
                spam_confidence=result['spam_confidence'],
                types=result.get('types', []),
                ip_address=ip_address,
                user_agent=user_agent,
                response_time=response_time,
                rag_applied=result.get('adjustment_applied', False),
                auto_blocked=result.get('auto_blocked', False)
            )
            
            # RAG 상세 정보 저장 (RAG가 적용된 경우)
            if result.get('adjustment_applied', False) and log_id:
                try:
                    db_logger.log_rag_details(
                        ethics_log_id=log_id,
                        similar_case_count=result.get('similar_cases_count', 0),
                        max_similarity=result.get('max_similarity', 0.0),  # 이미 0-1 범위
                        original_immoral_score=result.get('base_score', result['final_score']),
                        original_spam_score=result.get('base_spam_score', result.get('spam_score', 0.0)),  # RAG 보정 전 스팸 점수
                        adjusted_immoral_score=result.get('adjusted_immoral_score', result['final_score']),
                        adjusted_spam_score=result.get('adjusted_spam_score', result['spam_score']),
                        adjustment_weight=result.get('adjustment_weight', 0.0),
                        confidence_boost=0.0,  # 별도 계산 필요 시 추가
                        similar_cases=result.get('rag_similar_cases', []),
                        rag_response_time=response_time
                    )
                except Exception as rag_log_error:
                    print(f"[WARN] RAG 로그 저장 실패: {rag_log_error}")
            
            # 즉시 차단인 경우 점수가 None이므로 출력 형식 변경
            immoral_str = f"{result['final_score']:.1f}" if result.get('final_score') is not None else "N/A (즉시차단)"
            spam_str = f"{result['spam_score']:.1f}" if result.get('spam_score') is not None else "N/A (즉시차단)"
            print(f"[INFO] Ethics 분석 완료 - status: {status}, 비윤리: {immoral_str}, 스팸: {spam_str}, 응답시간: {response_time:.3f}초")
        except Exception as log_error:
            print(f"[WARN] 로그 저장 실패: {log_error}")
        
        # ⚡ 신뢰도 70 이상인 케이스 자동 저장 (RAG 벡터DB) - 비동기로 백그라운드 처리
        # 즉시 차단 케이스는 이미 유사 사례가 있으므로 저장 건너뜀
        try:
            if (analyzer and hasattr(analyzer, '_auto_save_high_confidence_case_async') 
                and not result.get('auto_blocked', False)
                and result.get('final_score') is not None
                and result.get('spam_score') is not None):
                analyzer._auto_save_high_confidence_case_async(
                    text=text,
                    immoral_score=result['final_score'],
                    spam_score=result['spam_score'],
                    confidence=result['final_confidence'],
                    spam_confidence=result['spam_confidence']
                )
        except Exception as save_error:
            print(f"[WARN] 자동 저장 실패: {save_error}")
        
        return status, result, block_reason
        
    except Exception as e:
        print(f"[ERROR] Ethics 분석 실패: {e}")
        return 'exposed', None, ""  # 분석 실패 시 일단 노출


def analyze_and_update_post(post_id: int, text: str, ip_address: str = None):
    """
    백그라운드에서 게시글 분석 및 상태 업데이트
    
    Args:
        post_id: 게시글 ID
        text: 분석할 텍스트
        ip_address: IP 주소
    """
    try:
        analyzer = get_ethics_analyzer()
        if analyzer is None:
            print(f"[WARN] 게시글 {post_id} - Analyzer 없음, 백그라운드 분석 건너뜀")
            return
        
        # 분석 시간 측정 시작
        start_time = time.time()
        
        # 분석 실행
        result = analyzer.analyze(text)
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        
        # 차단 여부 결정
        should_block, block_reason = should_block_content(result)
        status = 'blocked' if should_block else 'exposed'
        
        # 게시글 상태 업데이트
        execute_query(
            "UPDATE board SET status = %s WHERE id = %s",
            (status, post_id)
        )
        
        # 로그 저장
        try:
            log_id = db_logger.log_analysis(
                text=text,
                score=result['final_score'],
                confidence=result['final_confidence'],
                spam=result['spam_score'],
                spam_confidence=result['spam_confidence'],
                types=result.get('types', []),
                ip_address=ip_address,
                user_agent=None,  # 백그라운드 작업이므로 user_agent 없음
                response_time=response_time,
                rag_applied=result.get('adjustment_applied', False),
                auto_blocked=result.get('auto_blocked', False)
            )
            
            # RAG 상세 정보 저장 (RAG가 적용된 경우)
            if result.get('adjustment_applied', False) and log_id:
                try:
                    db_logger.log_rag_details(
                        ethics_log_id=log_id,
                        similar_case_count=result.get('similar_cases_count', 0),
                        max_similarity=result.get('max_similarity', 0.0),  # 이미 0-1 범위
                        original_immoral_score=result.get('base_score', result['final_score']),
                        original_spam_score=result.get('base_spam_score', result.get('spam_score', 0.0)),  # RAG 보정 전 스팸 점수
                        adjusted_immoral_score=result.get('adjusted_immoral_score', result['final_score']),
                        adjusted_spam_score=result.get('adjusted_spam_score', result['spam_score']),
                        adjustment_weight=result.get('adjustment_weight', 0.0),
                        confidence_boost=0.0,  # 별도 계산 필요 시 추가
                        similar_cases=result.get('rag_similar_cases', []),
                        rag_response_time=response_time
                    )
                except Exception as rag_log_error:
                    print(f"[WARN] 게시글 {post_id} - RAG 로그 저장 실패: {rag_log_error}")
        except Exception as log_error:
            print(f"[WARN] 게시글 {post_id} - 로그 저장 실패: {log_error}")
        
        # ⚡ 신뢰도 70 이상인 케이스 자동 저장 (RAG 벡터DB) - 비동기로 백그라운드 처리
        # 즉시 차단 케이스는 이미 유사 사례가 있으므로 저장 건너뜀
        try:
            if (analyzer and hasattr(analyzer, '_auto_save_high_confidence_case_async')
                and not result.get('auto_blocked', False)
                and result.get('final_score') is not None
                and result.get('spam_score') is not None):
                analyzer._auto_save_high_confidence_case_async(
                    text=text,
                    immoral_score=result['final_score'],
                    spam_score=result['spam_score'],
                    confidence=result['final_confidence'],
                    spam_confidence=result['spam_confidence'],
                    post_id=str(post_id),
                    user_id=""
                )
        except Exception as save_error:
            print(f"[WARN] 게시글 {post_id} - 자동 저장 실패: {save_error}")
        
        # 즉시 차단인 경우 점수가 None이므로 출력 형식 변경
        immoral_str = f"{result['final_score']:.1f}" if result.get('final_score') is not None else "N/A (즉시차단)"
        spam_str = f"{result['spam_score']:.1f}" if result.get('spam_score') is not None else "N/A (즉시차단)"
        print(f"[INFO] 백그라운드 분석 완료 - post_id: {post_id}, status: {status}, 비윤리: {immoral_str}, 스팸: {spam_str}, 응답시간: {response_time:.3f}초")
        
    except Exception as e:
        print(f"[ERROR] 게시글 {post_id} - 백그라운드 분석 실패: {e}")


async def analyze_images_hybrid(
    saved_images: List[dict],
    board_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Tuple[bool, str, List[int]]:
    """
    이미지 하이브리드 분석 (NSFW 1차 + Vision API 2차)
    
    Args:
        saved_images: 저장된 이미지 정보 리스트
        board_id: 게시글 ID
        ip_address: IP 주소
        user_agent: User Agent
        
    Returns:
        (차단 여부, 차단 사유, 로그 ID 리스트)
    """
    if not IMAGE_ANALYSIS_AVAILABLE:
        print("[WARN] 이미지 분석 모듈 사용 불가 - 분석 건너뜀")
        return False, "", []
    
    log_ids = []
    
    for image in saved_images:
        start_time = time.time()
        image_path = UPLOAD_DIR / image['filename']
        
        nsfw_result = None
        vision_result = None
        is_blocked = False
        block_reason = ""
        
        try:
            # 1차 필터: NSFW 검사 (빠르고 저렴)
            nsfw_detector = get_nsfw_detector()
            if nsfw_detector:
                nsfw_result = nsfw_detector.analyze(str(image_path))
                print(f"[INFO] NSFW 검사: {image['filename']}, "
                      f"NSFW={nsfw_result.get('is_nsfw')}, "
                      f"신뢰도={nsfw_result.get('confidence', 0):.1f}%")
                
                # NSFW 임계값 체크 (80% 이상)
                if nsfw_detector.should_block(nsfw_result, threshold=80.0):
                    is_blocked = True
                    block_reason = "부적절한 이미지가 감지되었습니다 (NSFW)"
                    print(f"[WARN] NSFW 차단: {image['filename']}")
            
            # 2차 검증: Vision API (NSFW가 의심되거나 추가 검증 필요 시)
            # Vision API 실행 조건:
            # 1. NSFW 검사 실패
            # 2. NSFW 경계선 (60-80%)
            # 3. NSFW 아님 + 신뢰도 낮음 (<80%) - 추가 검증 필요
            should_use_vision = (
                nsfw_result is None or  # NSFW 검사 실패 시 Vision으로 검증
                (nsfw_result.get('is_nsfw') and 60 <= nsfw_result.get('confidence', 0) < 80) or  # NSFW 경계선
                (not nsfw_result.get('is_nsfw') and nsfw_result.get('confidence', 0) < 80)  # 정상이지만 신뢰도 낮음
            )
            
            # 비용 절감 옵션: 정상 판정 + 높은 신뢰도(80% 이상)면 Vision 건너뛰기
            # 필요시 아래 주석을 해제하여 모든 정상 이미지에 Vision API 실행 가능
            # should_use_vision = should_use_vision or not nsfw_result.get('is_nsfw')
            
            if should_use_vision:
                vision_analyzer = get_vision_analyzer()
                if vision_analyzer:
                    vision_result = vision_analyzer.analyze_image(str(image_path))
                    print(f"[INFO] Vision API 검사: {image['filename']}, "
                          f"비윤리={vision_result.get('immoral_score', 0):.1f}, "
                          f"스팸={vision_result.get('spam_score', 0):.1f}")
                    
                    # Vision API 차단 판단
                    if vision_result.get('is_blocked', False):
                        is_blocked = True
                        _, block_reason = vision_analyzer.should_block_image(vision_result)
                        print(f"[WARN] Vision API 차단: {image['filename']}")
            
            # 분석 시간 계산
            response_time = time.time() - start_time
            
            # 로그 저장
            log_id = image_logger.log_analysis(
                filename=image['filename'],
                original_name=image['original_name'],
                file_size=image['size'],
                board_id=board_id,
                nsfw_result=nsfw_result,
                vision_result=vision_result,
                is_blocked=is_blocked,
                block_reason=block_reason,
                ip_address=ip_address,
                user_agent=user_agent,
                response_time=response_time
            )
            
            if log_id:
                log_ids.append(log_id)
            
            # 차단된 이미지 발견 시 즉시 반환
            if is_blocked:
                # 모든 이미지 삭제
                for img in saved_images:
                    try:
                        (UPLOAD_DIR / img['filename']).unlink()
                        print(f"[INFO] 차단된 이미지 삭제: {img['filename']}")
                    except:
                        pass
                
                return True, block_reason, log_ids
                
        except Exception as e:
            print(f"[ERROR] 이미지 분석 실패: {image['filename']}, {e}")
            # 분석 실패 시 로그만 남기고 통과
            try:
                log_id = image_logger.log_analysis(
                    filename=image['filename'],
                    original_name=image['original_name'],
                    file_size=image['size'],
                    board_id=board_id,
                    block_reason=f"분석 실패: {str(e)}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                if log_id:
                    log_ids.append(log_id)
            except:
                pass
    
    return False, "", log_ids


def analyze_and_update_comment(comment_id: int, text: str, ip_address: str = None):
    """
    백그라운드에서 댓글 분석 및 상태 업데이트
    
    Args:
        comment_id: 댓글 ID
        text: 분석할 텍스트
        ip_address: IP 주소
    """
    try:
        analyzer = get_ethics_analyzer()
        if analyzer is None:
            print(f"[WARN] 댓글 {comment_id} - Analyzer 없음, 백그라운드 분석 건너뜀")
            return
        
        # 분석 시간 측정 시작
        start_time = time.time()
        
        # 분석 실행
        result = analyzer.analyze(text)
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        
        # 차단 여부 결정
        should_block, block_reason = should_block_content(result)
        status = 'blocked' if should_block else 'exposed'
        
        # 댓글 상태 업데이트
        execute_query(
            "UPDATE comment SET status = %s WHERE id = %s",
            (status, comment_id)
        )
        
        # 로그 저장
        try:
            db_logger.log_analysis(
                text=text,
                score=result['final_score'],
                confidence=result['final_confidence'],
                spam=result['spam_score'],
                spam_confidence=result['spam_confidence'],
                types=result.get('types', []),
                ip_address=ip_address,
                user_agent=None,  # 백그라운드 작업이므로 user_agent 없음
                response_time=response_time,
                rag_applied=result.get('adjustment_applied', False),
                auto_blocked=result.get('auto_blocked', False)
            )
        except Exception as log_error:
            print(f"[WARN] 댓글 {comment_id} - 로그 저장 실패: {log_error}")
        
        # ⚡ 신뢰도 70 이상인 케이스 자동 저장 (RAG 벡터DB) - 비동기로 백그라운드 처리
        # 즉시 차단 케이스는 이미 유사 사례가 있으므로 저장 건너뜀
        try:
            if (analyzer and hasattr(analyzer, '_auto_save_high_confidence_case_async')
                and not result.get('auto_blocked', False)
                and result.get('final_score') is not None
                and result.get('spam_score') is not None):
                analyzer._auto_save_high_confidence_case_async(
                    text=text,
                    immoral_score=result['final_score'],
                    spam_score=result['spam_score'],
                    confidence=result['final_confidence'],
                    spam_confidence=result['spam_confidence'],
                    post_id=str(comment_id),
                    user_id=""
                )
        except Exception as save_error:
            print(f"[WARN] 댓글 {comment_id} - 자동 저장 실패: {save_error}")
        
        # 즉시 차단인 경우 점수가 None이므로 출력 형식 변경
        immoral_str = f"{result['final_score']:.1f}" if result.get('final_score') is not None else "N/A (즉시차단)"
        spam_str = f"{result['spam_score']:.1f}" if result.get('spam_score') is not None else "N/A (즉시차단)"
        print(f"[INFO] 백그라운드 분석 완료 - comment_id: {comment_id}, status: {status}, 비윤리: {immoral_str}, 스팸: {spam_str}, 응답시간: {response_time:.3f}초")
        
    except Exception as e:
        print(f"[ERROR] 댓글 {comment_id} - 백그라운드 분석 실패: {e}")


def analyze_churn_risk_and_store(post_id: int, user_id: int, text: str, created_at: str, title: str = ""):
    """
    백그라운드에서 이탈 위험도 분석 및 저장
    
    텍스트를 문장 단위로 분할하고, 각 문장별로 위험도를 분석하여
    임계값 이상인 고위험 문장만 선별적으로 저장합니다.
    
    Args:
        post_id: 게시글 ID
        user_id: 사용자 ID
        text: 게시글 내용
        created_at: 생성 시간
        title: 게시글 제목 (문맥 분석용)
    """
    try:
        from chrun_backend.rag_pipeline.text_splitter import split_text_to_sentences
        from chrun_backend.rag_pipeline.risk_scorer import RiskScorer
        from datetime import datetime
        
        print(f"[INFO] 게시글 {post_id} - 이탈 위험도 분석 시작", flush=True)
        print(f"[DEBUG] 게시글 {post_id} - 제목: {title}", flush=True)
        print(f"[DEBUG] 게시글 {post_id} - 텍스트 길이: {len(text)}자", flush=True)
        print(f"[DEBUG] 게시글 {post_id} - 텍스트 내용: {text[:100]}...", flush=True)
        
        # 1. 텍스트를 문장 단위로 분할
        created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if isinstance(created_at, str) else created_at
        
        # 제목을 user_context로 전달 (문맥 분석용)
        user_context = {"title": title} if title else None
        
        sentences = split_text_to_sentences(
            text=text,
            user_id=user_id,  # 숫자 그대로 전달 (users.id와 매칭)
            post_id=f"board_{post_id}",
            created_at=created_at_dt,
            user_context=user_context
        )
        
        print(f"[DEBUG] 게시글 {post_id} - split_text_to_sentences 반환 결과: {len(sentences) if sentences else 0}개 문장", flush=True)
        
        if not sentences:
            print(f"[WARN] 게시글 {post_id} - 분할된 문장이 없음 (필터링됨 또는 분할 실패)", flush=True)
            return
        
        print(f"[INFO] 게시글 {post_id} - {len(sentences)}개 문장으로 분할 완료")
        
        # 분할된 문장 출력
        for i, sent_data in enumerate(sentences, 1):
            sent_text = sent_data.get('sentence', '')
            print(f"[INFO]   문장 {i}: \"{sent_text[:80]}...\"")
        
        # 2. RiskScorer로 각 문장의 위험도 분석
        # _save_to_high_risk_store가 내부적으로 호출되어 고위험 문장만 자동 저장됨
        scorer = RiskScorer()
        result = scorer.score_sentences(sentences, store_high_risk=False)
        
        # 분석 결과 추출
        all_scored = result.get('all_scored', [])
        high_risk_candidates = result.get('high_risk_candidates', [])
        
        # 전체 위험도 계산 (최고 위험도 문장 기준)
        max_risk_score = max([s.get('risk_score', 0.0) for s in all_scored], default=0.0)
        
        # 모든 문장의 위험도 출력
        print(f"[INFO] 게시글 {post_id} - 문장별 위험도 분석 결과:")
        for i, scored in enumerate(all_scored, 1):
            sentence = scored.get('sentence', '')
            risk_score = scored.get('risk_score', 0.0)
            is_high = scored.get('is_high_risk', False)
            status = "🔴 고위험" if is_high else "✅ 정상"
            print(f"[INFO]   {i}. [{status}] 위험도 {risk_score:.3f} - \"{sentence[:60]}...\"")
        
        if high_risk_candidates:
            print(f"[INFO] ⚠️ 게시글 {post_id} - {len(high_risk_candidates)}개의 고위험 문장 감지! (임계값: 0.75)")
            for i, candidate in enumerate(high_risk_candidates, 1):
                sentence = candidate.get('sentence', '')
                risk_score = candidate.get('risk_score', 0.0)
                print(f"[INFO]   {i}. \"{sentence[:60]}...\" (위험도: {risk_score:.3f})")
        else:
            print(f"[INFO] ✅ 게시글 {post_id} - 고위험 문장 없음 (최고 위험도: {max_risk_score:.3f}, 임계값: 0.75)")
        
    except Exception as e:
        print(f"[ERROR] 게시글 {post_id} - 이탈 위험도 분석 실패: {e}")
        import traceback
        traceback.print_exc()


def analyze_and_process_report(report_id: int, content: str, reason: str, target_type: str, target_id: int):
    """
    백그라운드에서 신고 분석 및 자동 처리
    
    Args:
        report_id: 신고 ID
        content: 신고된 콘텐츠 (게시글 또는 댓글 내용)
        reason: 신고 사유
        target_type: 'board' 또는 'comment'
        target_id: 대상 ID (board_id 또는 comment_id)
    """
    try:
        # OpenAI API 키 확인
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            print(f"[WARN] 신고 {report_id} - OpenAI API 키가 설정되지 않아 분석을 건너뜁니다")
            return
        
        # 환경변수 설정 (match_backend에서 사용)
        os.environ['OPENAI_API_KEY'] = api_key
        
        # match_backend의 analyze_with_ai 함수 import 및 실행
        try:
            from match_backend.core import analyze_with_ai
        except ImportError:
            print(f"[WARN] 신고 {report_id} - match_backend를 import할 수 없어 분석을 건너뜁니다")
            return
        
        # AI 분석 수행
        print(f"[INFO] 신고 {report_id} 분석 시작 - type: {target_type}, target_id: {target_id}")
        ai_result = analyze_with_ai(content, reason)
        
        score = ai_result.get('score', 50)
        result_type = ai_result.get('type', '부분일치')
        analysis = ai_result.get('analysis', '')
        
        # 결과 타입을 DB enum 값으로 매핑
        result_enum = {
            '일치': 'match',
            '부분일치': 'partial_match',
            '불일치': 'mismatch'
        }.get(result_type, 'partial_match')
        
        # report_analysis 테이블에 결과 저장
        execute_query("""
            INSERT INTO report_analysis (report_id, result, confidence, analysis)
            VALUES (%s, %s, %s, %s)
        """, (report_id, result_enum, score, analysis))
        
        # 점수에 따라 자동 처리
        if score >= 81:
            # 일치: 게시글/댓글 차단, 신고 승인
            if target_type == 'board':
                execute_query(
                    "UPDATE board SET status = 'blocked' WHERE id = %s",
                    (target_id,)
                )
            else:  # comment
                execute_query(
                    "UPDATE comment SET status = 'blocked' WHERE id = %s",
                    (target_id,)
                )
            
            # processing_note (AI 분석 내용 제외)
            processing_note = f"AI 자동 처리 (점수: {score}): 신고 내용과 일치하여 콘텐츠 차단"
            execute_query("""
                UPDATE report 
                SET status = 'completed', 
                    processed_date = NOW(),
                    processing_note = %s
                WHERE id = %s
            """, (processing_note, report_id))
            
            print(f"[INFO] 신고 {report_id} 자동 승인 - {target_type} {target_id} 차단됨 (점수: {score})")
            
        elif score <= 29:
            # 불일치: 신고 거부, 게시글/댓글 유지
            processing_note = f"AI 자동 처리 (점수: {score}): 신고 내용과 불일치하여 거부"
            execute_query("""
                UPDATE report 
                SET status = 'rejected',
                    processed_date = NOW(),
                    processing_note = %s
                WHERE id = %s
            """, (processing_note, report_id))
            
            print(f"[INFO] 신고 {report_id} 자동 거부 - {target_type} {target_id} 유지됨 (점수: {score})")
            
        else:
            # 부분일치: pending 상태 유지, 관리자 검토 필요
            processing_note = f"AI 분석 완료 (점수: {score}): 부분일치로 관리자 검토 필요"
            execute_query("""
                UPDATE report 
                SET processing_note = %s
                WHERE id = %s
            """, (processing_note, report_id))
            
            print(f"[INFO] 신고 {report_id} 부분일치 - 관리자 검토 필요 (점수: {score})")
        
    except Exception as e:
        print(f"[ERROR] 신고 {report_id} 자동 분석 실패: {e}")
        # 오류 발생 시 신고는 pending 상태로 유지


class PostCreate(BaseModel):
    title: str
    content: str
    category: str = "free"


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


@router.get("/board/posts")
async def get_posts(
    request: Request,
    category: Optional[str] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None
):
    """
    게시글 목록 조회
    
    Query Params:
        category: 카테고리 필터 (선택)
        page: 페이지 번호 (기본 1)
        limit: 페이지당 게시글 수 (기본 20)
    """
    # 파라미터 기본값 설정
    if page is None or page < 1:
        page = 1
    if limit is None or limit < 1 or limit > 100:
        limit = 20
    
    offset = (page - 1) * limit
    
    # 기본 쿼리 (LEFT JOIN으로 탈퇴한 사용자 처리)
    query = """
        SELECT 
            b.id, b.title, b.content, b.category, b.status,
            b.like_count, b.view_count, b.created_at, b.updated_at,
            u.id as user_id, COALESCE(u.username, '탈퇴한 사용자') as username
        FROM board b
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.status = 'exposed'
    """
    params = []
    
    # 카테고리 필터
    if category:
        query += " AND b.category = %s"
        params.append(category)
    
    query += " ORDER BY b.created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    posts = execute_query(query, tuple(params), fetch_all=True)
    
    # 전체 개수 조회
    count_query = "SELECT COUNT(*) as total FROM board WHERE status = 'exposed'"
    count_params = []
    if category:
        count_query += " AND category = %s"
        count_params.append(category)
    
    total_result = execute_query(count_query, tuple(count_params) if count_params else (), fetch_one=True)
    total = total_result['total'] if total_result else 0
    
    # 결과 포맷팅
    formatted_posts = []
    for post in posts:
        formatted_posts.append({
            'id': post['id'],
            'title': post['title'],
            'content': post['content'][:200],  # 미리보기용 200자
            'category': post['category'],
            'like_count': post['like_count'],
            'view_count': post['view_count'],
            'created_at': post['created_at'].isoformat() if post['created_at'] else None,
            'updated_at': post['updated_at'].isoformat() if post['updated_at'] else None,
            'author': {
                'id': post['user_id'],
                'username': post['username']
            }
        })
    
    return {
        'success': True,
        'posts': formatted_posts,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': (total + limit - 1) // limit
        }
    }


@router.get("/board/search-results")
async def get_search_result_posts(
    request: Request,
    post_ids: str,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "latest"
):
    """
    검색 결과 기반 게시글 조회
    
    Query Params:
        post_ids: 쉼표로 구분된 게시글 ID 목록
        page: 페이지 번호 (기본 1)
        limit: 페이지당 게시글 수 (기본 20)
        sort_by: 정렬 방식 (latest, popular, similarity)
    """
    try:
        # post_ids 파싱
        if not post_ids.strip():
            return {
                'success': True,
                'posts': [],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': 0,
                    'total_pages': 0
                }
            }
        
        id_list = [int(id.strip()) for id in post_ids.split(',') if id.strip().isdigit()]
        
        if not id_list:
            return {
                'success': True,
                'posts': [],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': 0,
                    'total_pages': 0
                }
            }
        
        # IN 절을 위한 플레이스홀더 생성
        placeholders = ','.join(['%s'] * len(id_list))
        
        # 기본 쿼리
        query = f"""
            SELECT 
                b.id, b.title, b.content, b.category, b.status,
                b.like_count, b.view_count, b.created_at, b.updated_at,
                u.id as user_id, COALESCE(u.username, '탈퇴한 사용자') as username
            FROM board b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE b.status = 'exposed' AND b.id IN ({placeholders})
        """
        
        # 정렬 추가
        if sort_by == "latest":
            query += " ORDER BY b.created_at DESC"
        elif sort_by == "popular":
            query += " ORDER BY (b.like_count + b.view_count) DESC, b.created_at DESC"
        elif sort_by == "similarity":
            # 검색 결과 순서 유지 (FIELD 함수 사용)
            field_order = ','.join(map(str, id_list))
            query += f" ORDER BY FIELD(b.id, {field_order})"
        else:
            query += " ORDER BY b.created_at DESC"
        
        posts = execute_query(query, tuple(id_list), fetch_all=True)
        
        # 결과 포맷팅 및 메타데이터 추가
        formatted_posts = []
        board_count = 0
        comment_count = 0
        
        for post in posts:
            # 문서 타입 결정 (기본값: board)
            doc_type = 'board'  # 현재는 게시글만 검색하므로 board로 고정
            
            if doc_type == 'board':
                board_count += 1
            else:
                comment_count += 1
            
            formatted_posts.append({
                'id': post['id'],
                'title': post['title'],
                'content': post['content'][:200],  # 미리보기용 200자
                'category': post['category'],
                'like_count': post['like_count'],
                'view_count': post['view_count'],
                'created_at': post['created_at'].isoformat() if post['created_at'] else None,
                'updated_at': post['updated_at'].isoformat() if post['updated_at'] else None,
                'author': {
                    'id': post['user_id'],
                    'username': post['username']
                },
                # 검색 메타데이터 추가
                'doc_type': doc_type,
                'similarity_score': 100 - (id_list.index(post['id']) * 10) if post['id'] in id_list else 0,
                'search_method': 'ensemble',
                'chunk_index': 0,
                'chunk_count': 1
            })
        
        total = len(formatted_posts)
        
        # 검색 메타데이터
        search_metadata = {
            'search_method': 'BM25+Vector 앙상블',
            'total_results': total,
            'board_count': board_count,
            'comment_count': comment_count,
            'search_time_ms': 0  # 실제 검색 시간은 프론트엔드에서 계산
        }
        
        return {
            'success': True,
            'posts': formatted_posts,
            'search_metadata': search_metadata,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'total_pages': (total + limit - 1) // limit if total > 0 else 0
            }
        }
        
    except Exception as e:
        print(f"[ERROR] 검색 결과 조회 실패: {e}")
        return {
            'success': False,
            'error': str(e),
            'posts': [],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': 0,
                'total_pages': 0
            }
        }


@router.get("/board/posts/{post_id}")
async def get_post(request: Request, post_id: int):
    """게시글 상세 조회 (조회수 증가)"""
    
    # 조회수 증가
    execute_query(
        "UPDATE board SET view_count = view_count + 1 WHERE id = %s",
        (post_id,)
    )
    
    # 게시글 조회 (LEFT JOIN으로 탈퇴한 사용자 처리, images 컬럼 포함)
    post = execute_query("""
        SELECT 
            b.id, b.title, b.content, b.category, b.status,
            b.like_count, b.view_count, b.created_at, b.updated_at, b.images,
            u.id as user_id, COALESCE(u.username, '탈퇴한 사용자') as username
        FROM board b
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.id = %s AND b.status = 'exposed'
    """, (post_id,), fetch_one=True)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 이미지 정보 파싱
    images = []
    if post.get('images'):
        try:
            images = json.loads(post['images']) if isinstance(post['images'], str) else post['images']
        except (json.JSONDecodeError, TypeError):
            images = []
    
    # 댓글 조회 (LEFT JOIN으로 탈퇴한 사용자 처리)
    comments = execute_query("""
        SELECT 
            c.id, c.content, c.parent_id, c.status,
            c.created_at, c.updated_at,
            u.id as user_id, COALESCE(u.username, '탈퇴한 사용자') as username
        FROM comment c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE c.board_id = %s AND c.status = 'exposed'
        ORDER BY c.parent_id IS NULL DESC, c.parent_id, c.created_at
    """, (post_id,), fetch_all=True)
    
    # 댓글 트리 구조 생성
    comment_map = {}
    root_comments = []
    
    for comment in comments:
        comment_obj = {
            'id': comment['id'],
            'content': comment['content'],
            'parent_id': comment['parent_id'],
            'created_at': comment['created_at'].isoformat() if comment['created_at'] else None,
            'updated_at': comment['updated_at'].isoformat() if comment['updated_at'] else None,
            'author': {
                'id': comment['user_id'],
                'username': comment['username']
            },
            'replies': []
        }
        comment_map[comment['id']] = comment_obj
        
        if comment['parent_id'] is None:
            root_comments.append(comment_obj)
        else:
            if comment['parent_id'] in comment_map:
                comment_map[comment['parent_id']]['replies'].append(comment_obj)
    
    # 현재 사용자 확인 (user_id가 NULL이면 탈퇴한 사용자이므로 is_author는 False)
    current_user = get_current_user(request)
    is_author = current_user and post['user_id'] and current_user['user_id'] == post['user_id']
    
    return {
        'success': True,
        'post': {
            'id': post['id'],
            'title': post['title'],
            'content': post['content'],
            'category': post['category'],
            'like_count': post['like_count'],
            'view_count': post['view_count'],
            'created_at': post['created_at'].isoformat() if post['created_at'] else None,
            'updated_at': post['updated_at'].isoformat() if post['updated_at'] else None,
            'author': {
                'id': post['user_id'],
                'username': post['username']
            },
            'is_author': is_author,
            'images': images
        },
        'comments': root_comments
    }


@router.post("/board/posts")
async def create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form("free"),
    images: List[UploadFile] = File(default=[])
):
    """게시글 작성 (로그인 필요, 이미지 첨부 가능)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 입력 검증
    if not title or len(title) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="제목은 2자 이상이어야 합니다"
        )
    
    # 이미지 개수 검증
    if len(images) > MAX_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이미지는 최대 {MAX_IMAGES}개까지 업로드할 수 있습니다"
        )
    
    # 이미지 검증 및 저장
    saved_images = []
    for image in images:
        if image.filename:  # 파일이 실제로 업로드된 경우
            # 이미지 검증
            is_valid, error_msg = validate_image(image)
            if not is_valid:
                # 이미 저장된 이미지 삭제
                for saved_img in saved_images:
                    try:
                        (UPLOAD_DIR / saved_img["filename"]).unlink()
                    except:
                        pass
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # 이미지 저장
            try:
                image_data = await save_image(image)
                saved_images.append(image_data)
            except HTTPException:
                # 이미 저장된 이미지 삭제
                for saved_img in saved_images:
                    try:
                        (UPLOAD_DIR / saved_img["filename"]).unlink()
                    except:
                        pass
                raise
    
    # 텍스트 비윤리/스팸 자동 분석 (동기 방식)
    content_text = f"{title}\n{content}"
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')
    content_status, analysis_result, block_reason = await analyze_and_log_content(content_text, client_ip, user_agent)
    
    # 이미지 정보 JSON 변환
    images_json = json.dumps(saved_images) if saved_images else None
    
    # 게시글 생성 (분석된 status로 저장)
    post_id = execute_query("""
        INSERT INTO board (user_id, title, content, category, status, images)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user['user_id'], title, content, category, content_status, images_json))
    
    # 이미지 윤리/스팸 분석 (하이브리드: NSFW + Vision API)
    if saved_images:
        images_blocked, image_block_reason, image_log_ids = await analyze_images_hybrid(
            saved_images=saved_images,
            board_id=post_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if images_blocked:
            # 이미지가 차단된 경우 게시글도 차단 처리
            execute_query(
                "UPDATE board SET status = 'blocked' WHERE id = %s",
                (post_id,)
            )
            return {
                'success': False,
                'message': f'게시글이 자동 차단되었습니다: {image_block_reason}',
                'blocked': True,
                'reason': image_block_reason
            }
    
    # ⭐ 새로 추가: RAG 기반 이탈 위험도 분석 (백그라운드)
    try:
        print(f"[DEBUG] 게시글 {post_id} - content_status: {content_status}, 백그라운드 작업 제출 시도...", flush=True)
        if content_status != 'blocked':  # 차단되지 않은 경우만 분석
            background_executor.submit(
                analyze_churn_risk_and_store,
                post_id,
                user['user_id'],
                data.content,  # 본문만 (제목은 별도 전달)
                datetime.now().isoformat(),
                data.title  # 제목을 문맥으로 전달
            )
            print(f"[INFO] 게시글 {post_id} - 백그라운드 이탈 위험도 분석 시작됨 (제목 포함)", flush=True)
        else:
            print(f"[INFO] 게시글 {post_id} - 차단됨, 이탈 위험도 분석 건너뜀", flush=True)
    except Exception as e:
        print(f"[ERROR] 게시글 {post_id} - 백그라운드 작업 제출 실패: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    # 이벤트 기록 (게시글 작성)
    try:
        from chrun_backend.user_hash_utils import get_user_hash_for_event
        user_hash = get_user_hash_for_event(user['user_id'])
        execute_query(
            "INSERT INTO events (user_hash, action, channel, created_at) VALUES (%s, %s, %s, %s)",
            (user_hash, 'post', 'web', datetime.now())
        )
    except Exception as e:
        # 이벤트 기록 실패해도 게시글 작성은 성공 처리
        print(f"[WARNING] 이벤트 기록 실패 (무시): {e}")
    
    # 응답 메시지
    if content_status == 'blocked':
        # 차단된 경우 업로드된 이미지도 삭제
        if images_json:
            delete_images(images_json)
        return {
            'success': False,
            'message': f'게시글이 자동 차단되었습니다: {block_reason}',
            'blocked': True,
            'reason': block_reason
        }
    
    return {
        'success': True,
        'message': '게시글이 작성되었습니다',
        'post_id': post_id
    }


@router.get("/board/posts/{post_id}/status")
async def check_post_status(request: Request, post_id: int):
    """
    게시글 상태 확인 (분석 결과 확인용)
    작성자만 자신의 게시글 상태 확인 가능
    """
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 조회 (모든 상태 포함)
    post = execute_query("""
        SELECT id, user_id, title, status
        FROM board
        WHERE id = %s
    """, (post_id,), fetch_one=True)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if post['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 게시글만 확인할 수 있습니다"
        )
    
    return {
        'success': True,
        'post_id': post['id'],
        'status': post['status'],
        'title': post['title']
    }


@router.put("/board/posts/{post_id}")
async def update_post(
    request: Request,
    post_id: int,
    title: str = Form(None),
    content: str = Form(None),
    category: str = Form(None),
    images: List[UploadFile] = File(default=[]),
    deleted_images: str = Form(default="")  # JSON 문자열: 삭제할 이미지 파일명 목록
):
    """게시글 수정 (작성자만, 이미지 추가/삭제 가능)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 조회 (이미지 정보 포함)
    post = execute_query(
        "SELECT user_id, images FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if post['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="게시글을 수정할 권한이 없습니다"
        )
    
    # 업데이트할 필드 수집
    update_fields = []
    params = []
    
    if title is not None:
        if len(title) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="제목은 2자 이상이어야 합니다"
            )
        update_fields.append("title = %s")
        params.append(title)
    
    if content is not None:
        update_fields.append("content = %s")
        params.append(content)
    
    if category is not None:
        update_fields.append("category = %s")
        params.append(category)
    
    # 기존 이미지 처리
    existing_images = []
    if post.get('images'):
        try:
            existing_images = json.loads(post['images']) if isinstance(post['images'], str) else post['images']
        except (json.JSONDecodeError, TypeError):
            existing_images = []
    
    # 삭제할 이미지 처리
    if deleted_images:
        try:
            deleted_list = json.loads(deleted_images) if deleted_images else []
            for filename in deleted_list:
                # 실제 파일 삭제
                file_path = UPLOAD_DIR / filename
                if file_path.exists():
                    try:
                        file_path.unlink()
                        print(f"[INFO] 이미지 삭제: {filename}")
                    except Exception as e:
                        print(f"[WARN] 이미지 삭제 실패: {filename}, {e}")
                
                # 목록에서 제거
                existing_images = [img for img in existing_images if img.get('filename') != filename]
        except json.JSONDecodeError:
            pass
    
    # 새 이미지 업로드
    new_images = []
    for image in images:
        if image.filename:  # 파일이 실제로 업로드된 경우
            # 이미지 검증
            is_valid, error_msg = validate_image(image)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # 이미지 저장
            try:
                image_data = await save_image(image)
                new_images.append(image_data)
            except HTTPException:
                raise
    
    # 기존 이미지 + 새 이미지 병합
    all_images = existing_images + new_images
    
    # 최대 개수 검증
    if len(all_images) > MAX_IMAGES:
        # 새로 업로드된 이미지 삭제
        for img in new_images:
            try:
                (UPLOAD_DIR / img['filename']).unlink()
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"이미지는 최대 {MAX_IMAGES}개까지 업로드할 수 있습니다"
        )
    
    # 새 이미지 윤리/스팸 분석
    if new_images:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')
        
        images_blocked, image_block_reason, image_log_ids = await analyze_images_hybrid(
            saved_images=new_images,
            board_id=post_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if images_blocked:
            # 새로 업로드된 이미지가 차단된 경우
            # (이미 삭제됨, 게시글 상태는 변경하지 않음)
            return {
                'success': False,
                'message': f'이미지가 차단되었습니다: {image_block_reason}',
                'blocked': True,
                'reason': image_block_reason
            }
    
    # 이미지 정보 업데이트
    if deleted_images or new_images:
        images_json = json.dumps(all_images) if all_images else None
        update_fields.append("images = %s")
        params.append(images_json)
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 내용이 없습니다"
        )
    
    # 업데이트 실행
    params.append(post_id)
    query = f"UPDATE board SET {', '.join(update_fields)} WHERE id = %s"
    execute_query(query, tuple(params))
    
    return {
        'success': True,
        'message': '게시글이 수정되었습니다'
    }


@router.delete("/board/posts/{post_id}")
async def delete_post(request: Request, post_id: int):
    """게시글 삭제 (작성자만) - soft delete"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 조회 (이미지 정보 포함)
    post = execute_query(
        "SELECT user_id, images FROM board WHERE id = %s AND status != 'deleted'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if post['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="게시글을 삭제할 권한이 없습니다"
        )
    
    # Soft delete
    execute_query(
        "UPDATE board SET status = 'deleted' WHERE id = %s",
        (post_id,)
    )
    
    # 첨부된 이미지 파일 삭제
    if post.get('images'):
        images_json = post['images'] if isinstance(post['images'], str) else json.dumps(post['images'])
        delete_images(images_json)
    
    return {
        'success': True,
        'message': '게시글이 삭제되었습니다'
    }


@router.post("/board/posts/{post_id}/like")
async def toggle_like(request: Request, post_id: int):
    """좋아요 토글 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 존재 확인
    post = execute_query(
        "SELECT like_count FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 좋아요 증가 (간단한 버전 - 실제로는 별도 테이블로 관리)
    execute_query(
        "UPDATE board SET like_count = like_count + 1 WHERE id = %s",
        (post_id,)
    )
    
    return {
        'success': True,
        'message': '좋아요가 반영되었습니다',
        'like_count': post['like_count'] + 1
    }


# ===== 댓글 API =====

@router.post("/board/posts/{post_id}/comments")
async def create_comment(request: Request, post_id: int, data: CommentCreate):
    """댓글 작성 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 존재 확인
    post = execute_query(
        "SELECT id FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 입력 검증
    if not data.content or len(data.content) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="댓글은 2자 이상이어야 합니다"
        )
    
    # 대댓글인 경우 부모 댓글 확인
    if data.parent_id:
        parent = execute_query(
            "SELECT id FROM comment WHERE id = %s AND board_id = %s AND status = 'exposed'",
            (data.parent_id, post_id),
            fetch_one=True
        )
        
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="부모 댓글을 찾을 수 없습니다"
            )
    
    # 비윤리/스팸 자동 분석 (동기 방식)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')
    content_status, analysis_result, block_reason = await analyze_and_log_content(data.content, client_ip, user_agent)
    
    # 댓글 생성 (분석된 status로 저장)
    comment_id = execute_query("""
        INSERT INTO comment (board_id, user_id, content, parent_id, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (post_id, user['user_id'], data.content, data.parent_id, content_status))
    
    # ⭐ 댓글에 대한 이탈 위험도 분석 (백그라운드)
    try:
        print(f"[DEBUG] 댓글 {comment_id} - content_status: {content_status}, 백그라운드 작업 제출 시도...", flush=True)
        if content_status != 'blocked':  # 차단되지 않은 경우만 분석
            background_executor.submit(
                analyze_churn_risk_and_store,
                comment_id,
                user['user_id'],
                data.content,
                datetime.now().isoformat()
            )
            print(f"[INFO] 댓글 {comment_id} - 백그라운드 이탈 위험도 분석 시작됨", flush=True)
        else:
            print(f"[INFO] 댓글 {comment_id} - 차단됨, 이탈 위험도 분석 건너뜀", flush=True)
    except Exception as e:
        print(f"[ERROR] 댓글 {comment_id} - 백그라운드 작업 제출 실패: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    # 이벤트 기록 (댓글 작성)
    try:
        from chrun_backend.user_hash_utils import get_user_hash_for_event
        user_hash = get_user_hash_for_event(user['user_id'])
        execute_query(
            "INSERT INTO events (user_hash, action, channel, created_at) VALUES (%s, %s, %s, %s)",
            (user_hash, 'comment', 'web', datetime.now())
        )
    except Exception as e:
        # 이벤트 기록 실패해도 댓글 작성은 성공 처리
        print(f"[WARNING] 이벤트 기록 실패 (무시): {e}")
    
    # 응답 메시지
    if content_status == 'blocked':
        return {
            'success': False,
            'message': f'댓글이 자동 차단되었습니다: {block_reason}',
            'blocked': True,
            'reason': block_reason
        }
    
    return {
        'success': True,
        'message': '댓글이 작성되었습니다',
        'comment_id': comment_id
    }


@router.get("/board/comments/{comment_id}/status")
async def check_comment_status(request: Request, comment_id: int):
    """
    댓글 상태 확인 (분석 결과 확인용)
    작성자만 자신의 댓글 상태 확인 가능
    """
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 조회 (모든 상태 포함)
    comment = execute_query("""
        SELECT id, user_id, content, status
        FROM comment
        WHERE id = %s
    """, (comment_id,), fetch_one=True)
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if comment['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 댓글만 확인할 수 있습니다"
        )
    
    return {
        'success': True,
        'comment_id': comment['id'],
        'status': comment['status'],
        'content': comment['content']
    }


@router.put("/board/comments/{comment_id}")
async def update_comment(request: Request, comment_id: int, data: CommentUpdate):
    """댓글 수정 (작성자만)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 조회
    comment = execute_query(
        "SELECT user_id FROM comment WHERE id = %s AND status = 'exposed'",
        (comment_id,),
        fetch_one=True
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if comment['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="댓글을 수정할 권한이 없습니다"
        )
    
    # 입력 검증
    if not data.content or len(data.content) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="댓글은 2자 이상이어야 합니다"
        )
    
    # 댓글 수정
    execute_query(
        "UPDATE comment SET content = %s WHERE id = %s",
        (data.content, comment_id)
    )
    
    return {
        'success': True,
        'message': '댓글이 수정되었습니다'
    }


@router.delete("/board/comments/{comment_id}")
async def delete_comment(request: Request, comment_id: int):
    """댓글 삭제 (작성자만) - soft delete"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 조회
    comment = execute_query(
        "SELECT user_id FROM comment WHERE id = %s AND status != 'deleted'",
        (comment_id,),
        fetch_one=True
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 작성자 확인
    if comment['user_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="댓글을 삭제할 권한이 없습니다"
        )
    
    # Soft delete
    execute_query(
        "UPDATE comment SET status = 'deleted' WHERE id = %s",
        (comment_id,)
    )
    
    return {
        'success': True,
        'message': '댓글이 삭제되었습니다'
    }


@router.get("/board/categories")
async def get_categories():
    """사용 가능한 카테고리 목록"""
    categories = [
        {'value': 'free', 'label': '자유게시판'},
        {'value': 'notice', 'label': '공지사항'},
        {'value': 'qna', 'label': '질문답변'},
        {'value': 'review', 'label': '후기'},
        {'value': 'tips', 'label': '팁/노하우'},
    ]
    
    return {
        'success': True,
        'categories': categories
    }


# ===== 신고 API =====

class ReportCreate(BaseModel):
    """신고 생성 모델"""
    reason: str  # '욕설 및 비방', '도배 및 광고', '사생활 침해', '저작권 침해'
    detail: Optional[str] = None  # 상세 사유 (선택)


@router.post("/board/posts/{post_id}/report")
async def report_post(request: Request, post_id: int, data: ReportCreate):
    """게시글 신고 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 게시글 존재 확인
    post = execute_query(
        "SELECT id, user_id, title, content FROM board WHERE id = %s AND status = 'exposed'",
        (post_id,),
        fetch_one=True
    )
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    # 자기 게시글은 신고 불가
    if post['user_id'] and post['user_id'] == user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 게시글은 신고할 수 없습니다"
        )
    
    # 신고 사유 검증
    valid_reasons = ['욕설 및 비방', '도배 및 광고', '사생활 침해', '저작권 침해']
    if data.reason not in valid_reasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"올바른 신고 사유를 선택해주세요: {', '.join(valid_reasons)}"
        )
    
    # 중복 신고 확인 (같은 사용자가 같은 게시글을 이미 신고했는지)
    existing_report = execute_query("""
        SELECT id FROM report 
        WHERE reporter_id = %s 
        AND board_id = %s 
        AND status = 'pending'
    """, (user['user_id'], post_id), fetch_one=True)
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 신고한 게시글입니다"
        )
    
    # 신고 내용 생성 (게시글 정보 저장)
    reported_content = f"[제목] {post['title']}\n[내용] {post['content'][:200]}{'...' if len(post['content']) > 200 else ''}"
    
    # 신고 생성
    report_id = execute_query("""
        INSERT INTO report 
        (report_type, board_id, reported_content, report_reason, report_detail, reporter_id, status, priority)
        VALUES ('board', %s, %s, %s, %s, %s, 'pending', 'normal')
    """, (post_id, reported_content, data.reason, data.detail, user['user_id']))
    
    # 백그라운드에서 AI 일치 분석 시작 (전체 게시글 내용 사용)
    full_content = f"[제목] {post['title']}\n[내용] {post['content']}"
    background_executor.submit(
        analyze_and_process_report,
        report_id,
        full_content,
        data.reason,
        'board',
        post_id
    )
    
    return {
        'success': True,
        'message': '신고가 접수되었습니다. 검토 후 조치하겠습니다.',
        'report_id': report_id
    }


@router.get("/board/posts/{post_id}/report/check")
async def check_report_status(request: Request, post_id: int):
    """게시글 신고 여부 확인 (로그인 필요)"""
    
    user = get_current_user(request)
    if not user:
        return {'reported': False}
    
    # 사용자가 이 게시글을 신고했는지 확인
    report = execute_query("""
        SELECT id, report_reason, status 
        FROM report 
        WHERE reporter_id = %s AND board_id = %s AND status = 'pending'
    """, (user['user_id'], post_id), fetch_one=True)
    
    return {
        'reported': bool(report),
        'report_reason': report['report_reason'] if report else None,
        'report_id': report['id'] if report else None
    }


@router.post("/board/comments/{comment_id}/report")
async def report_comment(request: Request, comment_id: int, data: ReportCreate):
    """댓글 신고 (로그인 필요)"""
    
    # 인증 확인
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다"
        )
    
    # 댓글 존재 확인
    comment = execute_query(
        "SELECT id, user_id, content, board_id FROM comment WHERE id = %s AND status = 'exposed'",
        (comment_id,),
        fetch_one=True
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다"
        )
    
    # 자기 댓글은 신고 불가
    if comment['user_id'] and comment['user_id'] == user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자신의 댓글은 신고할 수 없습니다"
        )
    
    # 신고 사유 검증
    valid_reasons = ['욕설 및 비방', '도배 및 광고', '사생활 침해', '저작권 침해']
    if data.reason not in valid_reasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"올바른 신고 사유를 선택해주세요: {', '.join(valid_reasons)}"
        )
    
    # 중복 신고 확인 (같은 사용자가 같은 댓글을 이미 신고했는지)
    existing_report = execute_query("""
        SELECT id FROM report 
        WHERE reporter_id = %s 
        AND comment_id = %s 
        AND status = 'pending'
    """, (user['user_id'], comment_id), fetch_one=True)
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 신고한 댓글입니다"
        )
    
    # 신고 내용 생성 (댓글 정보 저장)
    reported_content = f"[댓글] {comment['content'][:200]}{'...' if len(comment['content']) > 200 else ''}"
    
    # 신고 생성
    report_id = execute_query("""
        INSERT INTO report 
        (report_type, comment_id, reported_content, report_reason, report_detail, reporter_id, status, priority)
        VALUES ('comment', %s, %s, %s, %s, %s, 'pending', 'normal')
    """, (comment_id, reported_content, data.reason, data.detail, user['user_id']))
    
    # 백그라운드에서 AI 일치 분석 시작 (전체 댓글 내용 사용)
    full_content = comment['content']
    background_executor.submit(
        analyze_and_process_report,
        report_id,
        full_content,
        data.reason,
        'comment',
        comment_id
    )
    
    return {
        'success': True,
        'message': '신고가 접수되었습니다. 검토 후 조치하겠습니다.',
        'report_id': report_id
    }


@router.get("/board/comments/{comment_id}/report/check")
async def check_comment_report_status(request: Request, comment_id: int):
    """댓글 신고 여부 확인 (로그인 필요)"""
    
    user = get_current_user(request)
    if not user:
        return {'reported': False}
    
    # 사용자가 이 댓글을 신고했는지 확인
    report = execute_query("""
        SELECT id, report_reason, status 
        FROM report 
        WHERE reporter_id = %s AND comment_id = %s AND status = 'pending'
    """, (user['user_id'], comment_id), fetch_one=True)
    
    return {
        'reported': bool(report),
        'report_reason': report['report_reason'] if report else None,
        'report_id': report['id'] if report else None
    }

