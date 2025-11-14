# 🚀 트렌드 분석 MySQL 설정 가이드

## ✅ 완료된 작업

1. ✅ **테이블 생성 SQL** - `db/migration_add_trend_keywords.sql`
2. ✅ **더미 데이터 SQL** - `db/trend_dummy_data.sql`
3. ✅ **API 엔드포인트 수정** - `/api/trends`가 이제 MySQL에서 데이터 조회
4. ✅ **README 업데이트** - 설명 문서 추가

## 📋 설정 단계 (3단계)

### 1단계: 데이터베이스 테이블 생성

PowerShell 또는 CMD에서 실행:

```bash
mysql -u root -p wmai_db < db/migration_add_trend_keywords.sql
```

또는 MySQL Workbench에서:
1. `db/migration_add_trend_keywords.sql` 파일 열기
2. 전체 선택 후 실행

**생성되는 테이블:**
- `trend_keywords` - 키워드 및 검색 횟수
- `trend_stats_cache` - 게시글/댓글 통계 캐시

### 2단계: 더미 데이터 삽입

```bash
mysql -u root -p wmai_db < db/trend_dummy_data.sql
```

**삽입되는 데이터:**
- 최근 7일간의 트렌드 키워드 (인공지능, 챗GPT, 검색, 추천 등 20개)
- 날짜별로 점차 증가하는 검색 횟수
- 통계 캐시 (게시글 1,250개, 댓글 6,780개)

### 3단계: 서버 실행 및 테스트

```bash
# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는
python run_server.py
```

**브라우저에서 테스트:**
1. http://localhost:8000/trends - 트렌드 대시보드 페이지
2. http://localhost:8000/api/trends - API 직접 호출 (JSON 응답)

## 🧪 테스트 확인 사항

### API 응답 확인

브라우저에서 `http://localhost:8000/api/trends`를 열면 다음과 같은 JSON을 볼 수 있습니다:

```json
{
  "summary": {
    "total_posts": 1250,
    "total_comments": 6780,
    "total_searches": 2850,
    "unique_keywords": 20
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
  "source": "mysql"  // ← 이것이 "mysql"이면 성공!
}
```

**중요:** `"source": "mysql"`이면 MySQL에서 정상적으로 데이터를 가져온 것입니다.  
`"source": "fallback"`이면 오류가 발생한 것이므로 아래 문제 해결을 참조하세요.

### 트렌드 대시보드 확인

`http://localhost:8000/trends`에서:
- ✅ 키워드 목록이 표시되는지
- ✅ 타임라인 차트가 보이는지
- ✅ 증감률이 계산되는지

## 🐛 문제 해결

### "source": "fallback" 오류

**원인:** MySQL 테이블이 없거나 데이터베이스 연결 실패

**해결 방법:**

1. **테이블 확인**
```sql
USE wmai_db;
SHOW TABLES LIKE 'trend%';
```

2. **데이터 확인**
```sql
SELECT COUNT(*) FROM trend_keywords;
SELECT COUNT(*) FROM trend_stats_cache;
```

3. **데이터베이스 설정 확인** (`.env` 또는 `match_config.env`)
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=wmai_db
```

### MySQL 연결 오류

```bash
# MySQL 서버 상태 확인
mysql -u root -p -e "STATUS"

# 데이터베이스 생성 (없는 경우)
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS wmai_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 빈 데이터 오류

더미 데이터를 다시 삽입:

```bash
mysql -u root -p wmai_db < db/trend_dummy_data.sql
```

## 📊 데이터 수동 추가

### 새 키워드 추가

```sql
USE wmai_db;

INSERT INTO trend_keywords (keyword, search_count, search_date, category)
VALUES ('새로운키워드', 100, CURDATE(), 'general')
ON DUPLICATE KEY UPDATE 
    search_count = search_count + VALUES(search_count);
```

### 통계 업데이트

```sql
INSERT INTO trend_stats_cache (stat_date, total_posts, total_comments)
VALUES (
    CURDATE(),
    (SELECT COUNT(*) FROM board),
    (SELECT COUNT(*) FROM comment)
)
ON DUPLICATE KEY UPDATE 
    total_posts = VALUES(total_posts),
    total_comments = VALUES(total_comments);
```

## 📝 주요 변경 사항

### 이전 (외부 API)
```python
# dad.dothome.co.kr API 호출
response = await client.get("https://dad.dothome.co.kr/...")
```

### 현재 (MySQL)
```python
# MySQL 데이터베이스 조회
with get_db_connection() as conn:
    cursor.execute("SELECT keyword, COUNT(*) FROM trend_keywords...")
```

## 🎯 다음 단계 (선택사항)

1. **실제 데이터 수집**: 게시글/댓글에서 키워드 자동 추출
2. **스케줄러 설정**: 매일 자동으로 통계 업데이트
3. **카테고리 분류**: AI를 활용한 키워드 카테고리 자동 분류
4. **실시간 업데이트**: WebSocket을 통한 실시간 트렌드 업데이트

## 📚 관련 문서

- `db/README_TRENDS.md` - 상세 기술 문서
- `README.md` - 프로젝트 전체 문서
- `app/api/routes_api.py` - API 구현 코드

## ✨ 완료!

이제 트렌드 분석 시스템이 MySQL 기반으로 작동합니다! 🎉

