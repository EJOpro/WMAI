-- =====================================================
-- WMAI 데이터베이스 통합 마이그레이션 파일
-- =====================================================
-- 작성일: 2025-11-10
-- 설명: 모든 마이그레이션을 하나로 통합한 파일
-- 실행 방법: mysql -u root -p wmai_db < db/migrations_all.sql
-- 주의: 반드시 데이터베이스 백업 후 실행하세요!
-- =====================================================

USE wmai_db;

-- =====================================================
-- 1. 유저 삭제 시 게시글/댓글 유지 (ON DELETE SET NULL)
-- =====================================================

-- 1.1. board 테이블 수정
-- 기존 외래키 제약조건 삭제
ALTER TABLE board DROP FOREIGN KEY IF EXISTS fk_board_user;

-- user_id 컬럼을 NULL 허용으로 변경
ALTER TABLE board MODIFY COLUMN user_id INT NULL;

-- 새로운 외래키 제약조건 추가 (ON DELETE SET NULL)
ALTER TABLE board 
ADD CONSTRAINT fk_board_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- 1.2. comment 테이블 수정
-- 기존 외래키 제약조건 삭제
ALTER TABLE comment DROP FOREIGN KEY IF EXISTS fk_comment_user;

-- user_id 컬럼을 NULL 허용으로 변경
ALTER TABLE comment MODIFY COLUMN user_id INT NULL;

-- 새로운 외래키 제약조건 추가 (ON DELETE SET NULL)
ALTER TABLE comment 
ADD CONSTRAINT fk_comment_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

SELECT '✅ Step 1/5: 유저 삭제 설정 완료' AS status;

-- =====================================================
-- 2. 게시글 신고 기능 추가
-- =====================================================

-- report 테이블에 board_id 컬럼 추가
ALTER TABLE report 
ADD COLUMN IF NOT EXISTS board_id INT NULL AFTER report_type;

-- 외래키 제약조건 추가
ALTER TABLE report
ADD CONSTRAINT IF NOT EXISTS fk_report_board 
FOREIGN KEY (board_id) REFERENCES board(id) ON DELETE CASCADE;

-- board_id 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_report_board ON report(board_id);

SELECT '✅ Step 2/5: 게시글 신고 기능 추가 완료' AS status;

-- =====================================================
-- 3. 댓글 신고 기능 추가
-- =====================================================

-- report 테이블에 comment_id 컬럼 추가
ALTER TABLE report 
ADD COLUMN IF NOT EXISTS comment_id INT NULL AFTER board_id;

-- 외래키 제약조건 추가
ALTER TABLE report
ADD CONSTRAINT IF NOT EXISTS fk_report_comment 
FOREIGN KEY (comment_id) REFERENCES comment(id) ON DELETE CASCADE;

-- comment_id 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_report_comment ON report(comment_id);

SELECT '✅ Step 3/5: 댓글 신고 기능 추가 완료' AS status;

-- =====================================================
-- 4. Ethics 관리자 확정 기능 추가
-- =====================================================

-- 관리자 확정 여부
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS admin_confirmed TINYINT(1) DEFAULT 0;

-- 확정 타입 (immoral/spam/clean)
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS confirmed_type VARCHAR(20) DEFAULT NULL;

-- 확정 시간
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS confirmed_at DATETIME DEFAULT NULL;

-- 확정한 관리자 ID
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS confirmed_by INT DEFAULT NULL;

-- 인덱스 추가 (확정 여부로 필터링 시 성능 향상)
CREATE INDEX IF NOT EXISTS idx_admin_confirmed ON ethics_logs(admin_confirmed);
CREATE INDEX IF NOT EXISTS idx_confirmed_type ON ethics_logs(confirmed_type);

SELECT '✅ Step 4/5: Ethics 관리자 확정 기능 추가 완료' AS status;

-- =====================================================
-- 5. RAG 로그 테이블 생성
-- =====================================================

-- RAG 상세 로그 테이블 생성
CREATE TABLE IF NOT EXISTS ethics_rag_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ethics_log_id BIGINT NOT NULL,
  
  -- 유사 케이스 정보
  similar_case_count INT DEFAULT 0 COMMENT '검색된 유사 케이스 개수',
  max_similarity DOUBLE DEFAULT NULL COMMENT '최대 유사도 점수 (0-1)',
  
  -- 보정 전후 점수
  original_immoral_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 전 비윤리 점수',
  original_spam_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 전 스팸 점수',
  adjusted_immoral_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 후 비윤리 점수',
  adjusted_spam_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 후 스팸 점수',
  
  -- 보정 메타데이터
  adjustment_weight DOUBLE DEFAULT NULL COMMENT '보정 가중치 (0-1)',
  confidence_boost DOUBLE DEFAULT NULL COMMENT '신뢰도 증가량',
  adjustment_method VARCHAR(50) DEFAULT 'similarity_based' COMMENT '보정 방법',
  
  -- 유사 케이스 상세 정보 (JSON)
  similar_cases JSON DEFAULT NULL COMMENT '유사 케이스 상세 정보',
  
  -- RAG 처리 시간 및 성능
  rag_response_time DOUBLE DEFAULT NULL COMMENT 'RAG 처리 시간 (초)',
  vector_search_time DOUBLE DEFAULT NULL COMMENT '벡터 검색 시간 (초)',
  
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_rag_ethics_log 
    FOREIGN KEY (ethics_log_id) 
    REFERENCES ethics_logs(id) 
    ON DELETE CASCADE,
    
  INDEX idx_rag_ethics_log (ethics_log_id),
  INDEX idx_rag_created_at (created_at DESC),
  INDEX idx_rag_similarity (max_similarity),
  INDEX idx_rag_case_count (similar_case_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='RAG(Retrieval Augmented Generation) 보정 상세 로그';

SELECT '✅ Step 5/5: RAG 로그 테이블 생성 완료' AS status;

-- =====================================================
-- 마이그레이션 완료
-- =====================================================

SELECT '
🎉 모든 마이그레이션이 성공적으로 완료되었습니다!

적용된 마이그레이션:
1. 유저 삭제 시 게시글/댓글 유지 설정
2. 게시글 신고 기능 추가
3. 댓글 신고 기능 추가
4. Ethics 관리자 확정 기능 추가
5. RAG 로그 테이블 생성

' AS message;


