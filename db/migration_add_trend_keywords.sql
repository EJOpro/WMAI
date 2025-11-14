-- =====================================================
-- 트렌드 키워드 테이블 생성 마이그레이션
-- =====================================================
-- 작성일: 2025-01-12
-- 설명: 트렌드 분석을 위한 키워드 저장 테이블 생성
-- 실행 방법: mysql -u root -p wmai_db < db/migration_add_trend_keywords.sql
-- =====================================================

USE wmai_db;

-- 트렌드 키워드 테이블
CREATE TABLE IF NOT EXISTS trend_keywords (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL COMMENT '키워드',
    search_count INT UNSIGNED DEFAULT 0 COMMENT '검색 횟수',
    search_date DATE NOT NULL COMMENT '검색 날짜',
    category VARCHAR(50) DEFAULT 'general' COMMENT '카테고리 (general, tech, entertainment, news, etc)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_search_date (search_date DESC),
    INDEX idx_keyword (keyword),
    INDEX idx_search_count (search_count DESC),
    INDEX idx_category (category),
    UNIQUE KEY uk_keyword_date (keyword, search_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 게시글/댓글 통계 캐시 테이블 (성능 최적화)
CREATE TABLE IF NOT EXISTS trend_stats_cache (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL COMMENT '통계 날짜',
    total_posts INT UNSIGNED DEFAULT 0 COMMENT '게시글 수',
    total_comments INT UNSIGNED DEFAULT 0 COMMENT '댓글 수',
    total_views INT UNSIGNED DEFAULT 0 COMMENT '조회수',
    total_likes INT UNSIGNED DEFAULT 0 COMMENT '좋아요',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT '✅ 트렌드 키워드 테이블 생성 완료' AS status;

