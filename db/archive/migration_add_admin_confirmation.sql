-- ethics_logs 테이블에 관리자 확정 관련 컬럼 추가
-- 작성일: 2025-11-08

-- 관리자 확정 여부
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS admin_confirmed TINYINT(1) DEFAULT 0;

-- 확정 타입 (immoral/spam/clean)
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS confirmed_type VARCHAR(20) DEFAULT NULL;

-- 확정 시간
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS confirmed_at DATETIME DEFAULT NULL;

-- 확정한 관리자 ID
ALTER TABLE ethics_logs ADD COLUMN IF NOT EXISTS confirmed_by INT DEFAULT NULL;

-- 인덱스 추가 (확정 여부로 필터링 시 성능 향상)
ALTER TABLE ethics_logs ADD INDEX IF NOT EXISTS idx_admin_confirmed (admin_confirmed);
ALTER TABLE ethics_logs ADD INDEX IF NOT EXISTS idx_confirmed_type (confirmed_type);

