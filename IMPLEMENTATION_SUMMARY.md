# 이미지 윤리/스팸 필터링 구현 완료

## 구현 개요
게시판 이미지 업로드 시 자동으로 부적절한 콘텐츠를 감지하고 차단하는 하이브리드 필터링 시스템을 구현했습니다.

## 1단계: NSFW 감지 모델 (1차 필터)

### 파일: `ethics/nsfw_detector.py`
- **모델**: Hugging Face의 `Falconsai/nsfw_image_detection`
- **역할**: 음란물/부적절한 이미지 빠른 감지 (1차 필터)
- **장점**: 무료, 빠른 속도, 로컬 실행
- **기준**: 80% 이상 신뢰도로 NSFW 판정 시 차단

```python
from ethics.nsfw_detector import get_nsfw_detector

detector = get_nsfw_detector()
result = detector.analyze(image_path)
# result: {'is_nsfw': bool, 'confidence': float, 'label': str}
```

## 2단계: OpenAI Vision API (2차 검증)

### 파일: `ethics/vision_analyzer.py`
- **모델**: GPT-4o (Vision 지원)
- **역할**: 상세한 이미지 분석 및 텍스트 추출
- **기능**:
  - 비윤리적 콘텐츠 감지 (음란물, 폭력, 혐오 등)
  - 스팸성 콘텐츠 감지 (광고, 홍보)
  - 이미지 내 텍스트 OCR 및 분석
- **차단 기준**:
  - 비윤리 점수 ≥ 80 && 신뢰도 ≥ 80
  - 비윤리 점수 ≥ 90 && 신뢰도 ≥ 70
  - 스팸 점수 ≥ 70 && 신뢰도 ≥ 70

```python
from ethics.vision_analyzer import get_vision_analyzer

analyzer = get_vision_analyzer()
result = analyzer.analyze_image(image_path)
# result: {
#   'immoral_score': 0-100,
#   'spam_score': 0-100,
#   'confidence': 0-100,
#   'types': ['욕설', '음란물', ...],
#   'reasoning': '판단 근거',
#   'has_text': bool,
#   'extracted_text': str
# }
```

## 3단계: 데이터베이스 로그 시스템

### 마이그레이션: `db/migration_add_image_logs.sql`

#### 테이블: `image_analysis_logs`
- **이미지 정보**: filename, original_name, file_size, board_id
- **NSFW 결과**: nsfw_checked, is_nsfw, nsfw_confidence
- **Vision API 결과**: immoral_score, spam_score, vision_confidence, detected_types
- **차단 정보**: is_blocked, block_reason
- **메타데이터**: ip_address, user_agent, response_time, created_at

#### 뷰: `v_blocked_images`
관리자가 차단된 이미지를 쉽게 조회할 수 있는 뷰

### 로거: `ethics/image_db_logger.py`
```python
from ethics.image_db_logger import image_logger

log_id = image_logger.log_analysis(
    filename='uuid.jpg',
    original_name='photo.jpg',
    file_size=1024000,
    board_id=123,
    nsfw_result={...},
    vision_result={...},
    is_blocked=True,
    block_reason='부적절한 이미지'
)
```

## 4단계: 게시판 API 통합

### 파일: `app/api/routes_board.py`

#### 하이브리드 분석 함수
```python
async def analyze_images_hybrid(
    saved_images: List[dict],
    board_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Tuple[bool, str, List[int]]
```

**분석 흐름**:
1. **1차 NSFW 검사** (빠르고 경량)
2. **2차 Vision API 검증** (NSFW 의심 or 추가 검증 필요 시)
3. **로그 저장** (모든 분석 결과)
4. **차단 시 이미지 삭제** 및 게시글 차단

#### 적용 API
- `POST /board/posts`: 게시글 작성 시 이미지 분석
- `PUT /board/posts/{post_id}`: 게시글 수정 시 새 이미지 분석

## 5단계: 관리자 대시보드 API

### 파일: `app/api/routes_admin.py`

#### 추가된 API 엔드포인트

1. **차단된 이미지 조회**
   ```
   GET /admin/images/blocked?page=1&limit=20
   ```

2. **이미지 분석 로그 조회**
   ```
   GET /admin/images/logs?page=1&limit=50&blocked_only=true
   ```

3. **이미지 분석 통계**
   ```
   GET /admin/images/stats
   ```
   - 총 분석 수, 차단 수
   - NSFW/비윤리/스팸 점수 평균
   - 일별 통계 (최근 7일)

## 의존성 추가

### `requirements.txt`
```
Pillow>=10.0.0
```
(transformers, openai는 기존에 설치됨)

## 사용 방법

### 1. 마이그레이션 실행
```sql
mysql -u root -p wmai_db < db/migration_add_image_logs.sql
```

또는 MySQL Workbench에서:
```sql
source db/migration_add_image_logs.sql;
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 확인
`.env` 파일에 OpenAI API 키가 있는지 확인:
```
OPENAI_API_KEY=your_api_key_here
```

### 4. 서버 실행
```bash
python run_server.py
```

## 동작 방식

1. **사용자가 이미지 업로드**
2. **1차 NSFW 검사** (로컬, 빠름)
   - NSFW 80% 이상 → 즉시 차단
3. **2차 Vision API 검증**
   - NSFW 60-80% (경계선) → Vision 확인
   - NSFW 아님 → Vision으로 스팸/텍스트 검증
4. **결과 저장** (image_analysis_logs)
5. **차단 시**:
   - 이미지 파일 삭제
   - 게시글 상태 'blocked'로 변경
   - 사용자에게 차단 사유 알림

## 관리자 기능

### 차단된 이미지 검토
1. 관리자 대시보드 접속
2. `/admin/images/blocked` API로 차단 목록 조회
3. 각 이미지별로:
   - NSFW 점수
   - Vision API 분석 결과 (비윤리/스팸 점수)
   - 감지된 유형 (욕설, 음란물, 광고 등)
   - 판단 근거
   - 업로더 정보

### 통계 확인
- 전체 분석 이미지 수
- 차단률
- 평균 분석 시간
- 일별 트렌드

## 비용 최적화

1. **NSFW 1차 필터**: 무료 (로컬 실행)
2. **Vision API**: 필요 시에만 호출
   - 이미지당 약 $0.01-0.03
   - NSFW로 즉시 차단 시 Vision 호출 안 함

## 확장 가능성

- [ ] 관리자 피드백을 통한 임계값 자동 조정
- [ ] 차단된 이미지 검토 후 복구 기능
- [ ] 이미지 내 텍스트를 기존 텍스트 필터와 연동
- [ ] 벡터DB에 차단 사례 저장 (학습 데이터)

## 트러블슈팅

### NSFW 모델 로드 실패
```bash
pip install transformers torch Pillow
```

### Vision API 실패
- `.env` 파일에 `OPENAI_API_KEY` 확인
- API 크레딧 잔액 확인

### 마이그레이션 오류
- MySQL 버전 확인 (5.7+ 필요)
- `wmai_db` 데이터베이스 존재 확인

## 테스트 방법

1. 게시글 작성 시 정상 이미지 업로드 → 통과
2. NSFW 이미지 업로드 → 차단 메시지
3. 광고/스팸 이미지 업로드 → Vision API 분석 후 차단
4. 관리자 페이지에서 로그 확인

---

**구현 완료일**: 2025-11-11
**작성자**: AI Assistant

