-- 마이그레이션: 유저 삭제 시 게시글/댓글 유지 (ON DELETE SET NULL)
-- 실행 전 반드시 데이터베이스 백업을 수행하세요!

USE wmai_db;

-- 1. board 테이블 수정
-- 기존 외래키 제약조건 삭제
ALTER TABLE board DROP FOREIGN KEY fk_board_user;

-- user_id 컬럼을 NULL 허용으로 변경
ALTER TABLE board MODIFY COLUMN user_id INT NULL;

-- 새로운 외래키 제약조건 추가 (ON DELETE SET NULL)
ALTER TABLE board 
ADD CONSTRAINT fk_board_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- 2. comment 테이블 수정
-- 기존 외래키 제약조건 삭제
ALTER TABLE comment DROP FOREIGN KEY fk_comment_user;

-- user_id 컬럼을 NULL 허용으로 변경
ALTER TABLE comment MODIFY COLUMN user_id INT NULL;

-- 새로운 외래키 제약조건 추가 (ON DELETE SET NULL)
ALTER TABLE comment 
ADD CONSTRAINT fk_comment_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- 완료 메시지
SELECT '마이그레이션 완료: 이제 유저 삭제 시 게시글/댓글이 유지되며 "탈퇴한 사용자"로 표시됩니다.' as message;

