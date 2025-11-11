-- 게시글 신고 기능을 위한 마이그레이션
-- 실행: mysql -u root -p < db/migration_add_board_report.sql

USE wmai_db;

-- report 테이블에 board_id 컬럼 추가
ALTER TABLE report 
ADD COLUMN board_id INT NULL AFTER report_type,
ADD CONSTRAINT fk_report_board 
FOREIGN KEY (board_id) REFERENCES board(id) ON DELETE CASCADE;

-- board_id 인덱스 추가
CREATE INDEX idx_report_board ON report(board_id);

-- 참고: MySQL 8.0 이전 버전에서는 partial index를 지원하지 않으므로,
-- 중복 신고 방지는 애플리케이션 레벨에서 처리합니다.

SELECT '✅ 마이그레이션 완료: report 테이블에 board_id 필드가 추가되었습니다.' AS status;

