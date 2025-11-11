-- 이미지 분석 로그 테이블 추가
-- 작성일: 2025-11-11
-- 설명: 업로드된 이미지의 윤리/스팸 분석 결과 저장

USE `wmai_db`;

-- 이미지 분석 로그 테이블
CREATE TABLE IF NOT EXISTS image_analysis_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- 이미지 정보
    filename VARCHAR(255) NOT NULL COMMENT '저장된 파일명 (UUID)',
    original_name VARCHAR(255) COMMENT '원본 파일명',
    file_size INT COMMENT '파일 크기 (bytes)',
    board_id INT COMMENT '연결된 게시글 ID',
    
    -- NSFW 1차 필터 결과
    nsfw_checked BOOLEAN DEFAULT FALSE COMMENT 'NSFW 검사 여부',
    is_nsfw BOOLEAN DEFAULT FALSE COMMENT 'NSFW 판정',
    nsfw_confidence DECIMAL(5,2) COMMENT 'NSFW 신뢰도 (0-100)',
    
    -- Vision API 2차 검증 결과
    vision_checked BOOLEAN DEFAULT FALSE COMMENT 'Vision API 검사 여부',
    immoral_score DECIMAL(5,2) COMMENT '비윤리 점수 (0-100)',
    spam_score DECIMAL(5,2) COMMENT '스팸 점수 (0-100)',
    vision_confidence DECIMAL(5,2) COMMENT 'Vision API 신뢰도 (0-100)',
    detected_types JSON COMMENT '감지된 유형 ["욕설", "음란물", "광고"]',
    reasoning TEXT COMMENT '판단 근거',
    has_text BOOLEAN DEFAULT FALSE COMMENT '이미지 내 텍스트 포함 여부',
    extracted_text TEXT COMMENT '추출된 텍스트',
    
    -- 차단 정보
    is_blocked BOOLEAN DEFAULT FALSE COMMENT '차단 여부',
    block_reason VARCHAR(500) COMMENT '차단 사유',
    
    -- 메타데이터
    ip_address VARCHAR(45) COMMENT 'IP 주소',
    user_agent TEXT COMMENT 'User Agent',
    response_time DECIMAL(8,3) COMMENT '분석 소요 시간 (초)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '분석 일시',
    
    -- 외래 키
    CONSTRAINT fk_image_log_board FOREIGN KEY (board_id) 
        REFERENCES board(id) ON DELETE SET NULL,
    
    -- 인덱스
    INDEX idx_filename (filename),
    INDEX idx_board_id (board_id),
    INDEX idx_is_blocked (is_blocked),
    INDEX idx_created_at (created_at DESC)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='이미지 분석 로그 (NSFW + Vision API)';

-- 차단된 이미지 뷰 (관리자용)
CREATE OR REPLACE VIEW v_blocked_images AS
SELECT 
    l.id,
    l.filename,
    l.original_name,
    l.board_id,
    b.title as board_title,
    b.user_id as uploader_id,
    u.username as uploader_name,
    l.is_nsfw,
    l.nsfw_confidence,
    l.immoral_score,
    l.spam_score,
    l.detected_types,
    l.reasoning,
    l.block_reason,
    l.created_at
FROM image_analysis_logs l
LEFT JOIN board b ON l.board_id = b.id
LEFT JOIN users u ON b.user_id = u.id
WHERE l.is_blocked = TRUE
ORDER BY l.created_at DESC;

-- 마이그레이션 완료
SELECT 'Migration completed: image_analysis_logs table and view created' AS status;

