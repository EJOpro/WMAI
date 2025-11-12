"""
이미지 분석 결과 데이터베이스 로거
"""
import json
from typing import Dict, Optional, List
from app.database import execute_query


class ImageAnalysisLogger:
    """이미지 분석 로그 저장"""
    
    @staticmethod
    def log_analysis(
        filename: str,
        original_name: str,
        file_size: int,
        board_id: Optional[int] = None,
        nsfw_result: Optional[Dict] = None,
        vision_result: Optional[Dict] = None,
        is_blocked: bool = False,
        block_reason: str = "",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_time: float = 0.0
    ) -> int:
        """
        이미지 분석 결과 저장
        
        Args:
            filename: 저장된 파일명 (UUID)
            original_name: 원본 파일명
            file_size: 파일 크기
            board_id: 연결된 게시글 ID
            nsfw_result: NSFW 검사 결과 딕셔너리
            vision_result: Vision API 결과 딕셔너리
            is_blocked: 차단 여부
            block_reason: 차단 사유
            ip_address: IP 주소
            user_agent: User Agent
            response_time: 분석 소요 시간
            
        Returns:
            생성된 로그 ID
        """
        try:
            # NSFW 결과 파싱
            nsfw_checked = bool(nsfw_result) if nsfw_result else False
            is_nsfw = nsfw_result.get('is_nsfw', False) if nsfw_result else False
            nsfw_confidence = nsfw_result.get('confidence', 0) if nsfw_result else None
            
            # Vision 결과 파싱
            vision_checked = bool(vision_result) if vision_result else False
            immoral_score = vision_result.get('immoral_score', 0) if vision_result else None
            spam_score = vision_result.get('spam_score', 0) if vision_result else None
            vision_confidence = vision_result.get('confidence', 0) if vision_result else None
            detected_types = json.dumps(vision_result.get('types', [])) if vision_result else None
            has_text = vision_result.get('has_text', False) if vision_result else False
            extracted_text = vision_result.get('extracted_text', '') if vision_result else None
            
            # 데이터베이스에 저장 (reasoning 필드 제거됨)
            log_id = execute_query("""
                INSERT INTO image_analysis_logs (
                    filename, original_name, file_size, board_id,
                    nsfw_checked, is_nsfw, nsfw_confidence,
                    vision_checked, immoral_score, spam_score, vision_confidence,
                    detected_types, has_text, extracted_text,
                    is_blocked, block_reason,
                    ip_address, user_agent, response_time
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s
                )
            """, (
                filename, original_name, file_size, board_id,
                nsfw_checked, is_nsfw, nsfw_confidence,
                vision_checked, immoral_score, spam_score, vision_confidence,
                detected_types, has_text, extracted_text,
                is_blocked, block_reason,
                ip_address, user_agent, response_time
            ))
            
            return log_id
            
        except Exception as e:
            print(f"[ERROR] 이미지 분석 로그 저장 실패: {e}")
            return 0
    
    @staticmethod
    def get_blocked_images(limit: int = 100) -> List[Dict]:
        """
        차단된 이미지 목록 조회
        
        Args:
            limit: 조회 개수
            
        Returns:
            차단된 이미지 목록
        """
        try:
            results = execute_query("""
                SELECT * FROM v_blocked_images
                LIMIT %s
            """, (limit,), fetch_all=True)
            
            return results if results else []
            
        except Exception as e:
            print(f"[ERROR] 차단 이미지 조회 실패: {e}")
            return []
    
    @staticmethod
    def get_image_log(log_id: int) -> Optional[Dict]:
        """
        특정 이미지 로그 조회
        
        Args:
            log_id: 로그 ID
            
        Returns:
            로그 정보 딕셔너리
        """
        try:
            result = execute_query("""
                SELECT * FROM image_analysis_logs
                WHERE id = %s
            """, (log_id,), fetch_one=True)
            
            return result
            
        except Exception as e:
            print(f"[ERROR] 이미지 로그 조회 실패: {e}")
            return None


# 싱글톤 인스턴스
image_logger = ImageAnalysisLogger()

