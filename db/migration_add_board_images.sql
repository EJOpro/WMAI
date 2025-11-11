-- 게시판 이미지 첨부 기능 추가
-- 작성일: 2025-11-11
-- 설명: board 테이블에 images 컬럼 추가 (JSON 타입)

USE `wmai_db`;

-- images 컬럼 추가
ALTER TABLE board 
ADD COLUMN images JSON DEFAULT NULL COMMENT '첨부 이미지 정보 (JSON 배열)';

-- 이미지 정보 JSON 구조 예시:
-- [
--   {"filename": "uuid1.jpg", "original_name": "photo1.jpg", "size": 1234567},
--   {"filename": "uuid2.png", "original_name": "photo2.png", "size": 2345678}
-- ]

-- 인덱스는 JSON 컬럼이므로 불필요
-- 마이그레이션 완료
SELECT 'Migration completed: board.images column added' AS status;

