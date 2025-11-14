"""간단하게 트렌드 테이블 생성"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv('match_config.env')

# 데이터베이스 연결
conn = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', '3306')),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'wmai_db'),
    charset='utf8mb4'
)

cursor = conn.cursor()

print("1. trend_keywords 테이블 생성...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS trend_keywords (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL,
    search_count INT UNSIGNED DEFAULT 0,
    search_date DATE NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_search_date (search_date DESC),
    INDEX idx_keyword (keyword),
    INDEX idx_search_count (search_count DESC),
    UNIQUE KEY uk_keyword_date (keyword, search_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
print("   [OK]")

print("2. trend_stats_cache 테이블 생성...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS trend_stats_cache (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL,
    total_posts INT UNSIGNED DEFAULT 0,
    total_comments INT UNSIGNED DEFAULT 0,
    total_views INT UNSIGNED DEFAULT 0,
    total_likes INT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
print("   [OK]")

conn.commit()

# 더미 데이터 삽입
print("3. 더미 데이터 삽입...")

# 오늘
cursor.execute("""
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
('쇼핑', 135, CURDATE(), 'general')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count)
""")
print("   [OK] 오늘 데이터 15개")

# 1일 전
cursor.execute("""
INSERT INTO trend_keywords (keyword, search_count, search_date, category) VALUES
('인공지능', 400, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 'tech'),
('챗GPT', 350, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 'tech'),
('검색', 300, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 'general'),
('추천', 260, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 'general'),
('Python', 240, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 'tech')
ON DUPLICATE KEY UPDATE 
    search_count = VALUES(search_count)
""")
print("   [OK] 1일 전 데이터 5개")

# 통계 캐시
cursor.execute("""
INSERT INTO trend_stats_cache (stat_date, total_posts, total_comments) VALUES
(CURDATE(), 1250, 6780)
ON DUPLICATE KEY UPDATE 
    total_posts = VALUES(total_posts),
    total_comments = VALUES(total_comments)
""")
print("   [OK] 통계 캐시")

conn.commit()
cursor.close()
conn.close()

print("\n[완료] 모든 설정이 완료되었습니다!")
print("\n다음 단계:")
print("  uvicorn app.main:app --reload")
print("  http://localhost:8000/trends")

