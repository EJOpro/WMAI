-- 댓글 신고 기능을 위한 마이그레이션
-- 실행: mysql -u root -p < db/migration_add_comment_report.sql
-- 또는: Get-Content db/migration_add_comment_report.sql | mysql -u root -p

USE wmai_db;

-- report 테이블에 comment_id 컬럼 추가
ALTER TABLE report 
ADD COLUMN comment_id INT NULL AFTER board_id,
ADD CONSTRAINT fk_report_comment 
FOREIGN KEY (comment_id) REFERENCES comment(id) ON DELETE CASCADE;

-- comment_id 인덱스 추가
CREATE INDEX idx_report_comment ON report(comment_id);

SELECT '✅ 마이그레이션 완료: report 테이블에 comment_id 필드가 추가되었습니다.' AS status;

