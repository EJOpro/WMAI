# 트렌드 분석 MySQL 구현 가이드

## 📋 개요

트렌드 분석 시스템을 외부 API가 아닌 MySQL 데이터베이스 기반으로 변경했습니다.

## 🗄️ 데이터베이스 설정

### 1단계: 테이블 생성

```bash
mysql -u root -p wmai_db < db/migration_add_trend_keywords.sql
```

이 명령어로 다음 테이블이 생성됩니다:
- `trend_keywords`: 키워드 및 검색 횟수 저장
- `trend_stats_cache`: 게시글/댓글 통계 캐시

### 2단계: 더미 데이터 삽입

```bash
mysql -u root -p wmai_db < db/trend_dummy_data.sql
```

이 명령어로 최근 7일간의 트렌드 키워드 더미 데이터가 삽입됩니다.

## 📊 테이블 구조

### trend_keywords 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGINT UNSIGNED | 기본 키 (자동 증가) |
| keyword | VARCHAR(100) | 키워드 |
| search_count | INT UNSIGNED | 검색 횟수 |
| search_date | DATE | 검색 날짜 |
| category | VARCHAR(50) | 카테고리 (general, tech, entertainment, news) |
| created_at | TIMESTAMP | 생성 시간 |
| updated_at | TIMESTAMP | 수정 시간 |

**인덱스:**
- `idx_search_date` (search_date DESC)
- `idx_keyword` (keyword)
- `idx_search_count` (search_count DESC)
- `uk_keyword_date` (keyword, search_date) - UNIQUE

### trend_stats_cache 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT UNSIGNED | 기본 키 |
| stat_date | DATE | 통계 날짜 |
| total_posts | INT UNSIGNED | 게시글 수 |
| total_comments | INT UNSIGNED | 댓글 수 |
| total_views | INT UNSIGNED | 조회수 |
| total_likes | INT UNSIGNED | 좋아요 |
| created_at | TIMESTAMP | 생성 시간 |
| updated_at | TIMESTAMP | 수정 시간 |

## 🔄 API 변경사항

### 엔드포인트: GET /api/trends

**이전:** 외부 API (dad.dothome.co.kr) 호출  
**현재:** MySQL 데이터베이스 조회

### 응답 구조

```json
{
  "summary": {
    "total_posts": 1250,
    "total_comments": 6780,
    "total_searches": 2850,
    "unique_keywords": 20,
    "total_trends": 20,
    "new_trends": 3,
    "rising_trends": 15
  },
  "keywords": [
    {"word": "인공지능", "count": 450},
    {"word": "챗GPT", "count": 380}
  ],
  "trends": [
    {
      "keyword": "인공지능",
      "mentions": 450,
      "change": 12.5,
      "category": "상승"
    }
  ],
  "timeline": [
    {"date": "2025-01-06", "count": 1450},
    {"date": "2025-01-07", "count": 1680}
  ],
  "source": "mysql",
  "timestamp": "2025-01-12T10:30:00"
}
```

## 📈 데이터 추가 방법

### 수동 데이터 추가

```sql
INSERT INTO trend_keywords (keyword, search_count, search_date, category)
VALUES ('새키워드', 100, CURDATE(), 'general')
ON DUPLICATE KEY UPDATE 
    search_count = search_count + VALUES(search_count),
    updated_at = CURRENT_TIMESTAMP;
```

### 통계 캐시 업데이트

```sql
INSERT INTO trend_stats_cache (stat_date, total_posts, total_comments)
VALUES (
    CURDATE(),
    (SELECT COUNT(*) FROM board),
    (SELECT COUNT(*) FROM comment)
)
ON DUPLICATE KEY UPDATE 
    total_posts = VALUES(total_posts),
    total_comments = VALUES(total_comments),
    updated_at = CURRENT_TIMESTAMP;
```

## 🔧 유지보수

### 오래된 데이터 삭제

```sql
-- 30일 이전 데이터 삭제
DELETE FROM trend_keywords WHERE search_date < CURDATE() - INTERVAL 30 DAY;

-- 통계 캐시 정리 (90일 이전)
DELETE FROM trend_stats_cache WHERE stat_date < CURDATE() - INTERVAL 90 DAY;
```

### 데이터 조회 예시

```sql
-- 최근 7일 인기 키워드 Top 10
SELECT 
    keyword,
    SUM(search_count) as total_count
FROM trend_keywords
WHERE search_date >= CURDATE() - INTERVAL 7 DAY
GROUP BY keyword
ORDER BY total_count DESC
LIMIT 10;

-- 날짜별 검색 트렌드
SELECT 
    search_date,
    SUM(search_count) as daily_total
FROM trend_keywords
WHERE search_date >= CURDATE() - INTERVAL 7 DAY
GROUP BY search_date
ORDER BY search_date;
```

## 🚀 서버 실행

```bash
# 메인 애플리케이션 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 브라우저에서 접속
http://localhost:8000/trends
```

## ⚠️ 주의사항

1. **데이터베이스 연결**: `match_config.env` 또는 `.env` 파일에 데이터베이스 설정이 올바른지 확인하세요.

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=wmai_db
```

2. **Fallback 처리**: MySQL 조회 실패 시 자동으로 더미 데이터를 반환합니다.

3. **성능 최적화**: 대량 데이터 발생 시 인덱스를 추가로 생성하거나 파티셔닝을 고려하세요.

## 📝 파일 목록

- `db/migration_add_trend_keywords.sql` - 테이블 생성 마이그레이션
- `db/trend_dummy_data.sql` - 더미 데이터 삽입
- `app/api/routes_api.py` - API 엔드포인트 (수정됨)
- `db/README_TRENDS.md` - 이 문서

## 🐛 문제 해결

### 테이블이 없다는 오류가 발생하는 경우

```bash
# 마이그레이션 파일을 다시 실행
mysql -u root -p wmai_db < db/migration_add_trend_keywords.sql
```

### 데이터가 표시되지 않는 경우

```bash
# 더미 데이터 재삽입
mysql -u root -p wmai_db < db/trend_dummy_data.sql
```

### 데이터베이스 연결 오류

- `.env` 파일의 데이터베이스 설정 확인
- MySQL 서버가 실행 중인지 확인
- 데이터베이스 `wmai_db`가 생성되어 있는지 확인

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS wmai_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

