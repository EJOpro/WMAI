-- 트렌드 분석을 위한 집계 테이블 추가
-- wmai_db에 추가되는 마이그레이션

USE wmai_db;

-- ============================================
-- 차원 테이블 (Dimension Tables)
-- ============================================

-- 페이지 차원
CREATE TABLE IF NOT EXISTS dim_page (
    page_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    page_path VARCHAR(2048) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_page_path (page_path(767))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- UTM 차원
CREATE TABLE IF NOT EXISTS dim_utm (
    utm_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_utm_combination (utm_source(100), utm_medium(100), utm_campaign(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 디바이스 차원 (사전 정의)
CREATE TABLE IF NOT EXISTS dim_device (
    device_id TINYINT UNSIGNED PRIMARY KEY,
    device_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_device_name (device_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 사전 정의 디바이스 데이터 삽입
INSERT INTO dim_device (device_id, device_name) VALUES
    (1, 'desktop'),
    (2, 'mobile'),
    (3, 'tablet')
ON DUPLICATE KEY UPDATE device_name=VALUES(device_name);

-- 국가 차원
CREATE TABLE IF NOT EXISTS dim_country (
    country_id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    country_iso2 CHAR(2) NOT NULL,
    country_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_country_iso2 (country_iso2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기본 국가 데이터 삽입 (한국)
INSERT INTO dim_country (country_iso2, country_name) VALUES
    ('KR', 'South Korea'),
    ('US', 'United States'),
    ('JP', 'Japan')
ON DUPLICATE KEY UPDATE country_name=VALUES(country_name);

-- ============================================
-- 팩트 테이블 (Fact Tables)
-- ============================================

-- 원시 이벤트 팩트 테이블
CREATE TABLE IF NOT EXISTS fact_events (
    event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_time TIMESTAMP(3) NOT NULL,
    session_id CHAR(36) NOT NULL COMMENT 'UUID',
    user_hash VARCHAR(64) NOT NULL COMMENT 'SHA-256 해시',
    page_id BIGINT UNSIGNED NOT NULL,
    utm_id BIGINT UNSIGNED,
    device_id TINYINT UNSIGNED NOT NULL,
    country_id SMALLINT UNSIGNED,
    event_type VARCHAR(50) NOT NULL,
    event_value JSON,
    referrer VARCHAR(2048),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_time (event_time),
    INDEX idx_session_id (session_id),
    INDEX idx_user_hash (user_hash),
    INDEX idx_page_id (page_id),
    INDEX idx_utm_id (utm_id),
    INDEX idx_device_id (device_id),
    INDEX idx_country_id (country_id),
    INDEX idx_event_type (event_type),
    FOREIGN KEY (page_id) REFERENCES dim_page(page_id),
    FOREIGN KEY (utm_id) REFERENCES dim_utm(utm_id),
    FOREIGN KEY (device_id) REFERENCES dim_device(device_id),
    FOREIGN KEY (country_id) REFERENCES dim_country(country_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 집계 테이블 (Aggregation Tables)
-- ============================================

-- 1분 단위 집계
CREATE TABLE IF NOT EXISTS agg_1m (
    bucket_ts TIMESTAMP NOT NULL,
    page_id BIGINT UNSIGNED,
    utm_id BIGINT UNSIGNED,
    device_id TINYINT UNSIGNED,
    country_id SMALLINT UNSIGNED,
    pv BIGINT UNSIGNED DEFAULT 0,
    sessions BIGINT UNSIGNED DEFAULT 0,
    conv BIGINT UNSIGNED DEFAULT 0,
    uv_hll VARBINARY(1024) COMMENT 'HyperLogLog 상태',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (bucket_ts, page_id, utm_id, device_id, country_id),
    INDEX idx_bucket_ts (bucket_ts),
    INDEX idx_page_id (page_id),
    INDEX idx_utm_id (utm_id),
    INDEX idx_device_id (device_id),
    INDEX idx_country_id (country_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5분 단위 집계
CREATE TABLE IF NOT EXISTS agg_5m (
    bucket_ts TIMESTAMP NOT NULL,
    page_id BIGINT UNSIGNED,
    utm_id BIGINT UNSIGNED,
    device_id TINYINT UNSIGNED,
    country_id SMALLINT UNSIGNED,
    pv BIGINT UNSIGNED DEFAULT 0,
    sessions BIGINT UNSIGNED DEFAULT 0,
    conv BIGINT UNSIGNED DEFAULT 0,
    uv_hll VARBINARY(1024) COMMENT 'HyperLogLog 상태',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (bucket_ts, page_id, utm_id, device_id, country_id),
    INDEX idx_bucket_ts (bucket_ts),
    INDEX idx_page_id (page_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 1시간 단위 집계
CREATE TABLE IF NOT EXISTS agg_1h (
    bucket_ts TIMESTAMP NOT NULL,
    page_id BIGINT UNSIGNED,
    utm_id BIGINT UNSIGNED,
    device_id TINYINT UNSIGNED,
    country_id SMALLINT UNSIGNED,
    pv BIGINT UNSIGNED DEFAULT 0,
    sessions BIGINT UNSIGNED DEFAULT 0,
    conv BIGINT UNSIGNED DEFAULT 0,
    uv_hll VARBINARY(1024) COMMENT 'HyperLogLog 상태',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (bucket_ts, page_id, utm_id, device_id, country_id),
    INDEX idx_bucket_ts (bucket_ts),
    INDEX idx_page_id (page_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 커뮤니티 트렌드 분석 테이블
-- ============================================

-- 커뮤니티 차원
CREATE TABLE IF NOT EXISTS dim_community (
    community_id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    community_name VARCHAR(100) NOT NULL COMMENT '커뮤니티명 (예: 루리웹, 디시인사이드)',
    community_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_community_name (community_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 게시글 테이블
CREATE TABLE IF NOT EXISTS community_posts (
    post_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    community_id SMALLINT UNSIGNED NOT NULL,
    board_name VARCHAR(100) COMMENT '게시판명',
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(100),
    post_url VARCHAR(500),
    view_count INT UNSIGNED DEFAULT 0,
    like_count INT UNSIGNED DEFAULT 0,
    posted_at TIMESTAMP NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_community_id (community_id),
    INDEX idx_posted_at (posted_at),
    INDEX idx_board_name (board_name),
    FULLTEXT idx_title_content (title, content) WITH PARSER ngram,
    FOREIGN KEY (community_id) REFERENCES dim_community(community_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 댓글 테이블
CREATE TABLE IF NOT EXISTS community_comments (
    comment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    post_id BIGINT UNSIGNED NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(100),
    like_count INT UNSIGNED DEFAULT 0,
    commented_at TIMESTAMP NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_post_id (post_id),
    INDEX idx_commented_at (commented_at),
    FULLTEXT idx_content (content) WITH PARSER ngram,
    FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 키워드 추출 캐시 테이블 (성능 최적화용)
CREATE TABLE IF NOT EXISTS keyword_cache (
    cache_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(255) NOT NULL COMMENT 'start_end_community_filter 조합',
    keywords JSON NOT NULL COMMENT '추출된 키워드 배열',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    UNIQUE KEY uk_cache_key (cache_key),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 마이그레이션 완료 확인
-- ============================================
SELECT 'Trend tables migration completed successfully!' AS status;


