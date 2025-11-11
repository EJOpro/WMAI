-- 일일보고서에서 reviewing 상태 제거 마이그레이션
-- 2025-11-09: reviewing 상태를 pending으로 변경하고 ENUM에서 제거

-- 1. 기존 reviewing 상태의 신고들을 pending으로 변경
UPDATE report SET status = 'pending' WHERE status = 'reviewing';

-- 2. status 컬럼의 ENUM에서 reviewing 제거
ALTER TABLE report MODIFY COLUMN status ENUM('pending','completed','rejected') DEFAULT 'pending';
