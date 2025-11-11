# 이미지 분석 대시보드 사용 가이드

## 개요
`ethics_dashboard`에 이미지 윤리/스팸 분석 기능이 추가되었습니다. 텍스트 분석과 이미지 분석을 탭으로 전환하며 확인할 수 있습니다.

## 접속 방법

### 1. 로그인
관리자 계정으로 로그인해야 합니다.

### 2. 대시보드 접속
```
http://localhost:8000/ethics_dashboard
```

## 화면 구성

### 탭 네비게이션
대시보드 상단에 2개의 탭이 있습니다:
- **📝 텍스트 분석**: 기존 텍스트 윤리/스팸 분석 로그
- **🖼️ 이미지 분석**: 새로 추가된 이미지 분석 로그

## 이미지 분석 탭 기능

### 1. 통계 카드 (4개)

#### 📊 총 분석 이미지
- 시스템이 분석한 전체 이미지 수

#### 🚫 차단된 이미지
- 부적절하다고 판단되어 차단된 이미지 수

#### ⚠️ NSFW 감지
- NSFW(Not Safe For Work)로 감지된 이미지 수
- 음란물, 부적절한 콘텐츠 등

#### ⏱️ 평균 분석 시간
- 이미지 1개당 평균 분석 소요 시간 (초)

### 2. 추가 통계 정보

```
평균 비윤리 점수: XX.X
평균 스팸 점수: XX.X
평균 NSFW 신뢰도: XX.X
```

- **비윤리 점수**: Vision API가 판단한 비윤리성 (0-100)
- **스팸 점수**: Vision API가 판단한 스팸성 (0-100)
- **NSFW 신뢰도**: NSFW 모델의 신뢰도 (0-100)

### 3. 필터 옵션

#### 상태 필터
- **전체**: 모든 이미지 로그
- **차단됨**: 차단된 이미지만
- **통과됨**: 통과된 이미지만

#### 페이지당 개수
- 10개, 20개(기본), 50개 선택 가능

### 4. 이미지 분석 로그 테이블

각 행에 다음 정보가 표시됩니다:

| 컬럼 | 설명 |
|------|------|
| **ID** | 로그 고유 번호 |
| **파일명** | 원본 파일명 (hover 시 UUID 파일명 표시) |
| **게시글** | 이미지가 첨부된 게시글 (링크 클릭 시 새 탭으로 이동) |
| **업로더** | 이미지를 업로드한 사용자 |
| **NSFW** | NSFW 판정 결과와 신뢰도 배지 |
| **비윤리** | Vision API 비윤리 점수 (색상 구분) |
| **스팸** | Vision API 스팸 점수 (색상 구분) |
| **차단** | 최종 차단 여부 배지 |
| **분석시간** | 분석 수행 시각 |
| **작업** | 상세보기 버튼 (👁️) |

#### 점수 색상 구분
- 🟢 **녹색** (0-39): 안전
- 🟡 **주황색** (40-69): 주의
- 🔴 **빨간색** (70-100): 위험

#### 배지 색상
- **🔴 차단됨**: 빨간색 배지
- **🟢 통과**: 녹색 배지
- **🔴 NSFW**: 빨간색 배지
- **🟢 정상**: 녹색 배지

### 5. 페이지네이션

테이블 하단에 페이지 이동 버튼:
- **⏮️ 처음**: 첫 페이지로
- **◀️ 이전**: 이전 페이지
- **페이지 정보**: 현재 페이지 / 전체 페이지
- **▶️ 다음**: 다음 페이지
- **⏭️ 마지막**: 마지막 페이지로

## 사용 시나리오

### 시나리오 1: 일일 모니터링
1. **ethics_dashboard** 접속
2. **이미지 분석** 탭 클릭
3. 통계 카드에서 당일 차단 건수 확인
4. 필터를 **차단됨**으로 설정
5. 차단된 이미지 목록 검토

### 시나리오 2: 특정 사용자 조사
1. 이미지 분석 탭에서 **업로더** 컬럼 확인
2. 의심스러운 사용자의 게시글 링크 클릭
3. 해당 게시글 확인

### 시나리오 3: 통계 분석
1. 통계 카드로 전체 차단률 확인
   - 차단률 = (차단된 이미지 / 총 분석 이미지) × 100
2. 평균 점수들을 확인하여 필터링 임계값 조정 검토
3. 평균 분석 시간으로 시스템 성능 모니터링

## 분석 흐름 이해하기

이미지가 업로드되면 다음과 같이 분석됩니다:

```
1. 이미지 업로드
   ↓
2. [1차] NSFW 감지 (로컬 모델, 빠름)
   - NSFW 80% 이상 → 즉시 차단 ✋
   ↓
3. [2차] Vision API 분석 (상세 분석)
   - 비윤리 콘텐츠 감지
   - 스팸 감지
   - 이미지 내 텍스트 추출
   ↓
4. 차단 기준 확인
   - 비윤리 ≥ 80 && 신뢰도 ≥ 80 → 차단
   - 비윤리 ≥ 90 && 신뢰도 ≥ 70 → 차단
   - 스팸 ≥ 70 && 신뢰도 ≥ 70 → 차단
   ↓
5. 로그 저장 (image_analysis_logs 테이블)
```

## 데이터베이스 테이블

### `image_analysis_logs`
모든 이미지 분석 결과가 저장됩니다.

**주요 필드:**
- `filename`: UUID 파일명
- `original_name`: 원본 파일명
- `board_id`: 게시글 ID
- `is_nsfw`: NSFW 판정
- `nsfw_confidence`: NSFW 신뢰도
- `immoral_score`: 비윤리 점수
- `spam_score`: 스팸 점수
- `vision_confidence`: Vision API 신뢰도
- `is_blocked`: 차단 여부
- `block_reason`: 차단 사유
- `created_at`: 분석 시각

### `v_blocked_images` (뷰)
차단된 이미지만 조회하는 뷰입니다.

## API 엔드포인트

대시보드는 다음 API를 사용합니다:

### 통계 조회
```
GET /admin/images/stats
```

**응답 예시:**
```json
{
  "success": true,
  "total_stats": {
    "total_analyzed": 150,
    "total_blocked": 12,
    "total_nsfw": 8,
    "avg_nsfw_confidence": 45.2,
    "avg_immoral_score": 23.5,
    "avg_spam_score": 18.7,
    "avg_response_time": 2.34
  },
  "daily_stats": [...]
}
```

### 로그 조회
```
GET /admin/images/logs?page=1&limit=20&blocked_only=false
```

**응답 예시:**
```json
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "filename": "abc123.jpg",
      "original_name": "photo.jpg",
      "board_id": 45,
      "board_title": "게시글 제목",
      "uploader_name": "user123",
      "is_nsfw": true,
      "nsfw_confidence": 85.5,
      "immoral_score": 92.0,
      "spam_score": 15.0,
      "is_blocked": true,
      "block_reason": "부적절한 이미지가 감지되었습니다 (NSFW)",
      "created_at": "2025-11-11T10:30:00"
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "limit": 20,
    "total_pages": 8
  }
}
```

## 트러블슈팅

### 1. 로그가 안 보여요
**확인사항:**
- 관리자 권한으로 로그인했는지 확인
- 데이터베이스 마이그레이션 실행 확인
  ```bash
  mysql -u root -p wmai_db < db/migration_add_image_logs.sql
  ```
- 브라우저 콘솔(F12)에서 에러 확인

### 2. 통계가 0으로 표시돼요
**원인:**
- 아직 이미지가 업로드되지 않았거나
- 분석이 실행되지 않았을 수 있습니다

**해결:**
- 게시글에 이미지를 업로드해보세요
- `/admin/images/logs` API를 직접 호출하여 데이터 확인

### 3. 필터가 작동하지 않아요
**해결:**
- 필터를 변경한 후 **적용** 버튼을 클릭하세요
- 페이지를 새로고침해보세요

### 4. "관리자 권한 필요" 오류
**해결:**
- 데이터베이스에서 사용자 role 확인:
  ```sql
  SELECT id, username, role FROM users WHERE username = '내아이디';
  ```
- role이 'admin'이 아니면:
  ```sql
  UPDATE users SET role = 'admin' WHERE username = '내아이디';
  ```

## 향후 개선 계획

- [ ] 이미지 썸네일 미리보기
- [ ] 상세 정보 모달 (detected_types, reasoning 등)
- [ ] 일별 통계 차트
- [ ] 차단 해제 기능
- [ ] 이미지 내 텍스트 하이라이트
- [ ] 벡터DB 연동 (학습 데이터 저장)
- [ ] 관리자 피드백 기능

## 관련 파일

### 프론트엔드
- `app/templates/pages/ethics_dashboard.html` - 대시보드 HTML
- `app/static/js/ethics_dashboard.js` - 대시보드 JavaScript
- `app/static/css/app.css` - 스타일시트

### 백엔드
- `app/api/routes_admin.py` - 관리자 API (이미지 관련)
- `app/api/routes_board.py` - 게시판 API (이미지 분석 통합)
- `ethics/nsfw_detector.py` - NSFW 감지 모델
- `ethics/vision_analyzer.py` - Vision API 분석
- `ethics/image_db_logger.py` - 로그 저장

### 데이터베이스
- `db/migration_add_image_logs.sql` - 테이블 생성 SQL

---

**작성일**: 2025-11-11  
**버전**: 1.0

