-- =====================================================
-- 트렌드 더미 데이터 삽입
-- =====================================================
-- 작성일: 2025-01-12
-- 설명: 테스트용 트렌드 키워드 더미 데이터
-- 실행 방법: mysql -u root -p wmai_db < db/trend_dummy_data.sql
-- =====================================================

USE wmai_db;

-- 기존 더미 데이터 삭제 (선택사항)
-- DELETE FROM trend_keywords WHERE created_at >= CURDATE() - INTERVAL 7 DAY;

-- 최근 7일간의 트렌드 키워드 더미 데이터 삽입
-- 날짜별로 다양한 키워드와 검색 횟수 생성

-- 오늘 (가장 인기 있는 날)
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 450, CURDATE(), 'tech'),
('챗GPT', 380, CURDATE(), 'tech'),
('검색', 320, CURDATE(), 'general'),
('추천', 280, CURDATE(), 'general'),
('Python', 250, CURDATE(), 'tech'),
('질문', 230, CURDATE(), 'general'),
('맛집', 210, CURDATE(), 'entertainment'),
('여행', 195, CURDATE(), 'entertainment'),
('영화', 180, CURDATE(), 'entertainment'),
('리뷰', 175, CURDATE(), 'general'),
('스마트폰', 165, CURDATE(), 'tech'),
('게임', 155, CURDATE(), 'entertainment'),
('뉴스', 145, CURDATE(), 'news'),
('날씨', 140, CURDATE(), 'general'),
('쇼핑', 135, CURDATE(), 'general'),
('건강', 130, CURDATE(), 'general'),
('운동', 125, CURDATE(), 'general'),
('음악', 120, CURDATE(), 'entertainment'),
('책', 115, CURDATE(), 'entertainment'),
('요리', 110, CURDATE(), 'entertainment')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;

-- 1일 전
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 400, CURDATE() - INTERVAL 1 DAY, 'tech'),
('챗GPT', 350, CURDATE() - INTERVAL 1 DAY, 'tech'),
('검색', 300, CURDATE() - INTERVAL 1 DAY, 'general'),
('추천', 260, CURDATE() - INTERVAL 1 DAY, 'general'),
('Python', 240, CURDATE() - INTERVAL 1 DAY, 'tech'),
('질문', 220, CURDATE() - INTERVAL 1 DAY, 'general'),
('맛집', 200, CURDATE() - INTERVAL 1 DAY, 'entertainment'),
('여행', 185, CURDATE() - INTERVAL 1 DAY, 'entertainment'),
('영화', 170, CURDATE() - INTERVAL 1 DAY, 'entertainment'),
('리뷰', 165, CURDATE() - INTERVAL 1 DAY, 'general'),
('스마트폰', 155, CURDATE() - INTERVAL 1 DAY, 'tech'),
('게임', 145, CURDATE() - INTERVAL 1 DAY, 'entertainment'),
('뉴스', 140, CURDATE() - INTERVAL 1 DAY, 'news'),
('날씨', 135, CURDATE() - INTERVAL 1 DAY, 'general'),
('쇼핑', 130, CURDATE() - INTERVAL 1 DAY, 'general')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;

-- 2일 전
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 380, CURDATE() - INTERVAL 2 DAY, 'tech'),
('챗GPT', 320, CURDATE() - INTERVAL 2 DAY, 'tech'),
('검색', 280, CURDATE() - INTERVAL 2 DAY, 'general'),
('추천', 250, CURDATE() - INTERVAL 2 DAY, 'general'),
('Python', 230, CURDATE() - INTERVAL 2 DAY, 'tech'),
('질문', 210, CURDATE() - INTERVAL 2 DAY, 'general'),
('맛집', 190, CURDATE() - INTERVAL 2 DAY, 'entertainment'),
('여행', 175, CURDATE() - INTERVAL 2 DAY, 'entertainment'),
('영화', 160, CURDATE() - INTERVAL 2 DAY, 'entertainment'),
('리뷰', 155, CURDATE() - INTERVAL 2 DAY, 'general')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;

-- 3일 전
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 360, CURDATE() - INTERVAL 3 DAY, 'tech'),
('챗GPT', 300, CURDATE() - INTERVAL 3 DAY, 'tech'),
('검색', 270, CURDATE() - INTERVAL 3 DAY, 'general'),
('추천', 240, CURDATE() - INTERVAL 3 DAY, 'general'),
('Python', 220, CURDATE() - INTERVAL 3 DAY, 'tech'),
('질문', 200, CURDATE() - INTERVAL 3 DAY, 'general'),
('맛집', 180, CURDATE() - INTERVAL 3 DAY, 'entertainment'),
('여행', 165, CURDATE() - INTERVAL 3 DAY, 'entertainment'),
('영화', 150, CURDATE() - INTERVAL 3 DAY, 'entertainment'),
('리뷰', 145, CURDATE() - INTERVAL 3 DAY, 'general')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;

-- 4일 전
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 340, CURDATE() - INTERVAL 4 DAY, 'tech'),
('챗GPT', 280, CURDATE() - INTERVAL 4 DAY, 'tech'),
('검색', 260, CURDATE() - INTERVAL 4 DAY, 'general'),
('추천', 230, CURDATE() - INTERVAL 4 DAY, 'general'),
('Python', 210, CURDATE() - INTERVAL 4 DAY, 'tech'),
('질문', 190, CURDATE() - INTERVAL 4 DAY, 'general'),
('맛집', 170, CURDATE() - INTERVAL 4 DAY, 'entertainment'),
('여행', 155, CURDATE() - INTERVAL 4 DAY, 'entertainment'),
('영화', 140, CURDATE() - INTERVAL 4 DAY, 'entertainment'),
('리뷰', 135, CURDATE() - INTERVAL 4 DAY, 'general')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;

-- 5일 전
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 320, CURDATE() - INTERVAL 5 DAY, 'tech'),
('챗GPT', 260, CURDATE() - INTERVAL 5 DAY, 'tech'),
('검색', 250, CURDATE() - INTERVAL 5 DAY, 'general'),
('추천', 220, CURDATE() - INTERVAL 5 DAY, 'general'),
('Python', 200, CURDATE() - INTERVAL 5 DAY, 'tech'),
('질문', 180, CURDATE() - INTERVAL 5 DAY, 'general'),
('맛집', 160, CURDATE() - INTERVAL 5 DAY, 'entertainment'),
('여행', 145, CURDATE() - INTERVAL 5 DAY, 'entertainment'),
('영화', 130, CURDATE() - INTERVAL 5 DAY, 'entertainment'),
('리뷰', 125, CURDATE() - INTERVAL 5 DAY, 'general')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;

-- 6일 전
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 300, CURDATE() - INTERVAL 6 DAY, 'tech'),
('챗GPT', 240, CURDATE() - INTERVAL 6 DAY, 'tech'),
('검색', 240, CURDATE() - INTERVAL 6 DAY, 'general'),
('추천', 210, CURDATE() - INTERVAL 6 DAY, 'general'),
('Python', 190, CURDATE() - INTERVAL 6 DAY, 'tech'),
('질문', 170, CURDATE() - INTERVAL 6 DAY, 'general'),
('맛집', 150, CURDATE() - INTERVAL 6 DAY, 'entertainment'),
('여행', 135, CURDATE() - INTERVAL 6 DAY, 'entertainment'),
('영화', 120, CURDATE() - INTERVAL 6 DAY, 'entertainment'),
('리뷰', 115, CURDATE() - INTERVAL 6 DAY, 'general')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;

-- 통계 캐시 데이터 삽입 (게시글/댓글 수)
INSERT INTO trend_stats_cache (stat_date, total_posts, total_comments, total_views, total_likes) VALUES
(CURDATE(), 1250, 6780, 15600, 3420),
(CURDATE() - INTERVAL 1 DAY, 1180, 6450, 14800, 3280),
(CURDATE() - INTERVAL 2 DAY, 1150, 6200, 14200, 3150),
(CURDATE() - INTERVAL 3 DAY, 1100, 5980, 13800, 3050),
(CURDATE() - INTERVAL 4 DAY, 1080, 5750, 13400, 2980),
(CURDATE() - INTERVAL 5 DAY, 1050, 5600, 13000, 2900),
(CURDATE() - INTERVAL 6 DAY, 1020, 5450, 12600, 2850)
ON DUPLICATE KEY UPDATE 
    total_posts = VALUES(total_posts),
    total_comments = VALUES(total_comments),
    total_views = VALUES(total_views),
    total_likes = VALUES(total_likes),
    updated_at = CURRENT_TIMESTAMP;

SELECT '✅ 트렌드 더미 데이터 삽입 완료' AS status;
SELECT COUNT(*) AS 'Total Keywords' FROM trend_keywords;
SELECT COUNT(*) AS 'Total Stats' FROM trend_stats_cache;

