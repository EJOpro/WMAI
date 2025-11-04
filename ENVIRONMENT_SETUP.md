# 환경변수 설정 가이드

WMAI 프로젝트의 임베딩 서비스 및 기타 기능을 사용하기 위한 환경변수 설정 방법을 안내합니다.

## 1. .env 파일 생성

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# =============================================================================
# OpenAI API 설정 (필수 - 임베딩 서비스용)
# =============================================================================
OPENAI_API_KEY=sk-your-openai-api-key-here

# =============================================================================
# 기타 선택적 설정
# =============================================================================
# Flask 개발 모드
FLASK_ENV=development
FLASK_DEBUG=True

# 로그 레벨
LOG_LEVEL=INFO

# 고위험 문장 판단 임계값 (기본값: 0.75)
RISK_THRESHOLD=0.75

# 임베딩 모델 (기본값: text-embedding-3-small)
EMBEDDING_MODEL=text-embedding-3-small
```

## 2. OpenAI API 키 발급 방법

1. [OpenAI Platform](https://platform.openai.com/api-keys) 접속
2. 로그인 후 "Create new secret key" 클릭
3. 키 이름 입력 후 생성
4. 생성된 키를 복사하여 `.env` 파일의 `OPENAI_API_KEY` 값으로 설정

⚠️ **주의사항**: 
- API 키는 절대 코드에 하드코딩하지 마세요
- `.env` 파일은 git에 커밋하지 마세요 (이미 .gitignore에 포함됨)
- API 키는 안전한 곳에 보관하세요

## 3. 설정 확인 방법

### 3.1 환경변수 로드 확인
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('OPENAI_API_KEY 설정됨:', bool(os.getenv('OPENAI_API_KEY')))"
```

### 3.2 임베딩 서비스 테스트
```bash
cd chrun_backend/rag_pipeline
python embedding_service.py
```

### 3.3 전체 시스템 테스트
```bash
python run_server.py
```

## 4. 임베딩 서비스 사용법

### 4.1 기본 사용법
```python
from chrun_backend.rag_pipeline.embedding_service import get_embedding

# 단일 문장 임베딩
text = "이 서비스는 정말 좋아요!"
embedding = get_embedding(text)
print(f"임베딩 차원: {len(embedding)}")  # 1536차원
```

### 4.2 배치 처리
```python
from chrun_backend.rag_pipeline.embedding_service import get_embeddings_batch

texts = [
    "서비스가 마음에 들어요",
    "이용하기 어려워요", 
    "도움이 많이 되었습니다"
]

embeddings = get_embeddings_batch(texts)
print(f"생성된 임베딩 개수: {len(embeddings)}")
```

### 4.3 환경 설정 확인
```python
from chrun_backend.rag_pipeline.embedding_service import check_environment

status = check_environment()
print(status)
# 출력 예시:
# {
#     'openai_api_key_set': True,
#     'embedding_model': 'text-embedding-3-small',
#     'embedding_dimension': 1536,
#     'environment_file_exists': True
# }
```

## 5. 문제 해결

### 5.1 API 키가 없는 경우
- 증상: "OPENAI_API_KEY가 설정되지 않았습니다" 경고 메시지
- 해결: `.env` 파일에 올바른 API 키 설정

### 5.2 OpenAI 패키지가 없는 경우
- 증상: "OpenAI 패키지가 설치되지 않았습니다" 오류
- 해결: `pip install openai` 실행

### 5.3 API 호출 오류
- 증상: "임베딩 생성 중 오류 발생" 메시지
- 가능한 원인:
  - 잘못된 API 키
  - 할당량 초과 (429 오류)
  - 네트워크 연결 문제
  - 텍스트 길이 초과

### 5.4 더미 벡터 반환
- 증상: 모든 값이 0.0인 벡터 반환
- 원인: API 키 미설정 또는 오류 발생 시 fallback 동작
- 해결: 환경변수 설정 확인 및 API 키 유효성 검증

## 6. 비용 최적화 팁

1. **개발 시 API 호출 제한**: 테스트용 더미 데이터 활용
2. **배치 처리 활용**: 여러 텍스트를 한 번에 처리
3. **캐싱 구현**: 동일한 텍스트의 중복 임베딩 방지
4. **텍스트 전처리**: 불필요한 공백/특수문자 제거

## 7. 보안 고려사항

1. **API 키 보안**:
   - 환경변수로만 관리
   - 코드에 하드코딩 금지
   - 정기적인 키 교체

2. **로그 보안**:
   - API 키가 로그에 노출되지 않도록 주의
   - 민감한 텍스트 내용 로깅 제한

3. **접근 제어**:
   - 프로덕션 환경에서 API 키 접근 권한 제한
   - 서버 환경변수 암호화 고려

---

문의사항이나 추가 도움이 필요한 경우, 프로젝트 관리자에게 연락하세요.
