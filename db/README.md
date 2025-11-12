# Database Migration Files

이 디렉토리는 데이터베이스 스키마 변경을 위한 마이그레이션 파일들을 포함합니다.

## 📁 디렉토리 구조

```
db/
├── migrations_all.sql              # 전체 스키마 (최신)
├── migration_add_board_images.sql  # 게시글 이미지 첨부 기능
├── migration_add_image_logs_no_reasoning.sql  # 이미지 분석 로그 (비용 최적화)
├── migration_remove_reviewing_status.sql      # reviewing 상태 제거
├── wmai_251029.sql                 # 백업 (2024-10-29)
├── wmai_251105.sql                 # 백업 (2024-11-05)
└── archive/                        # 구 마이그레이션 파일 보관
```

## 🔄 활성 마이그레이션 파일

### 1. `migration_add_board_images.sql`
**목적:** 게시글 이미지 첨부 기능 추가
- `board` 테이블에 `images` JSON 컬럼 추가
- 최대 5개 이미지, 파일당 5MB 제한
- 로컬 파일시스템 저장 (`app/static/uploads/board/`)

**실행 방법:**
```bash
mysql -u root -p1234 wmai -e "source db/migration_add_board_images.sql"
```

### 2. `migration_add_image_logs_no_reasoning.sql` ⭐ (최신)
**목적:** 이미지 윤리/스팸 분석 로그 저장 (비용 최적화 버전)
- `image_analysis_logs` 테이블 생성
- NSFW 1차 필터 + Vision API 2차 검증 결과 저장
- `reasoning` 필드 제외 (Vision API 토큰 **50% 절감**)
- `v_blocked_images` 뷰 생성

**실행 방법:**
```bash
mysql -u root -p1234 wmai -e "source db/migration_add_image_logs_no_reasoning.sql"
```

**테이블 구조:**
- NSFW 분석: `is_nsfw`, `nsfw_confidence`
- Vision API: `immoral_score`, `spam_score`, `vision_confidence`, `detected_types`
- 메타데이터: `ip_address`, `user_agent`, `response_time`

### 3. `migration_remove_reviewing_status.sql`
**목적:** 윤리 필터 reviewing 상태 제거
- `board`, `comments` 테이블의 `status` ENUM에서 'reviewing' 제거
- 차단된 게시글/댓글은 즉시 'blocked' 상태로 변경

**실행 방법:**
```bash
mysql -u root -p1234 wmai -e "source db/migration_remove_reviewing_status.sql"
```

## 📦 Archive 폴더

더 이상 사용되지 않는 마이그레이션 파일들을 보관합니다:
- `migration_add_image_logs.sql` - reasoning 포함 버전 (대체됨)
- `migration_remove_reasoning.sql` - 사용되지 않음
- `migration_add_admin_confirmation.sql` - 이전 기능
- `migration_add_board_report.sql` - 이전 기능
- `migration_add_comment_report.sql` - 이전 기능
- `migration_add_rag_logs.sql` - 이전 기능
- `migration_user_delete_set_null.sql` - 이전 기능

## 🚀 전체 스키마 적용

새로운 환경에서 전체 데이터베이스 구조를 생성하려면:

```bash
# 최신 백업 파일 사용
mysql -u root -p1234 wmai < db/wmai_251105.sql

# 또는 migrations_all.sql 사용
mysql -u root -p1234 wmai < db/migrations_all.sql
```

## ⚠️ 주의사항

1. **마이그레이션 순서**
   - 이미지 기능: `migration_add_board_images.sql` → `migration_add_image_logs_no_reasoning.sql`
   - 각 마이그레이션은 독립적으로 실행 가능

2. **백업**
   - 마이그레이션 실행 전 반드시 데이터베이스 백업
   ```bash
   mysqldump -u root -p1234 wmai > db/backup_$(date +%Y%m%d).sql
   ```

3. **롤백**
   - 대부분의 마이그레이션은 `DROP TABLE IF EXISTS` 또는 `ALTER TABLE DROP COLUMN`으로 롤백 가능
   - 데이터 손실 주의

## 📊 마이그레이션 히스토리

| 날짜 | 파일 | 설명 |
|------|------|------|
| 2024-11-11 | `migration_add_image_logs_no_reasoning.sql` | 이미지 분석 로그 (비용 최적화) |
| 2024-11-11 | `migration_add_board_images.sql` | 게시글 이미지 첨부 |
| 2024-11-11 | `migration_remove_reviewing_status.sql` | reviewing 상태 제거 |
| 2024-11-05 | `wmai_251105.sql` | 전체 스키마 백업 |
| 2024-10-29 | `wmai_251029.sql` | 전체 스키마 백업 |

## 🛠️ 유용한 명령어

### 테이블 확인
```bash
mysql -u root -p1234 wmai -e "SHOW TABLES;"
```

### 테이블 구조 확인
```bash
mysql -u root -p1234 wmai -e "DESCRIBE image_analysis_logs;"
```

### 뷰 확인
```bash
mysql -u root -p1234 wmai -e "SELECT * FROM v_blocked_images LIMIT 10;"
```

### 마이그레이션 상태 확인
```bash
# image_analysis_logs 테이블 존재 확인
mysql -u root -p1234 wmai -e "SHOW TABLES LIKE 'image_analysis_logs';"

# reasoning 컬럼 존재 확인 (없어야 정상)
mysql -u root -p1234 wmai -e "SHOW COLUMNS FROM image_analysis_logs LIKE 'reasoning';"
```

## 📝 변경 로그

### 2024-11-11
- ✅ 이미지 분석 로그 테이블 추가 (reasoning 제외)
- ✅ Vision API 비용 50% 절감
- ✅ 구 마이그레이션 파일 archive로 이동

### 이전 변경사항
- 게시글 이미지 첨부 기능
- 윤리 필터 reviewing 상태 제거
- 관리자 확인 시스템
- 신고 시스템
- RAG 로그 시스템

