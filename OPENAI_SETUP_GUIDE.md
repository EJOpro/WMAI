# OpenAI API 설정 가이드

## 🔑 OpenAI API 키 설정

AI 기반 인사이트 기능을 사용하려면 OpenAI API 키가 필요합니다.

### 1. OpenAI API 키 발급

1. [OpenAI Platform](https://platform.openai.com/)에 로그인
2. API Keys 섹션으로 이동
3. "Create new secret key" 클릭
4. 생성된 키를 안전한 곳에 복사

### 2. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# OpenAI API 설정
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini

# 데이터베이스 설정
DATABASE_URL=sqlite:///./churn_analysis.db
SQL_ECHO=false

# Redis 설정 (선택사항)
REDIS_URL=redis://localhost:6379/0

# 환경 설정
ENVIRONMENT=development
```

### 3. API 키 교체

`OPENAI_API_KEY=sk-your-actual-api-key-here` 부분에서 `sk-your-actual-api-key-here`를 실제 발급받은 API 키로 교체하세요.

### 4. 서버 재시작

환경 변수 설정 후 서버를 재시작하면 AI 인사이트 기능이 활성화됩니다:

```bash
python run_server.py
```

## 🔍 설정 확인

서버 시작 시 다음과 같은 로그가 나타나면 정상적으로 설정된 것입니다:

```
[INFO] OpenAI 클라이언트 초기화 완료
```

만약 다음과 같은 경고가 나타나면 API 키가 설정되지 않은 것입니다:

```
[WARNING] OPENAI_API_KEY가 설정되지 않았습니다. LLM 기능이 비활성화됩니다.
```

## 💡 비용 관리

- GPT-4o-mini 모델은 비용 효율적인 모델입니다
- 분석당 약 $0.001-0.005 정도의 비용이 발생합니다
- OpenAI 대시보드에서 사용량을 모니터링할 수 있습니다

## 🚫 API 키 없이 사용

API 키를 설정하지 않아도 기본적인 이탈 분석은 가능합니다. 다만 AI 기반 인사이트와 권장 액션은 제공되지 않습니다.

## 🔒 보안 주의사항

- `.env` 파일을 Git에 커밋하지 마세요
- API 키를 코드에 직접 하드코딩하지 마세요
- 사용하지 않는 API 키는 즉시 삭제하세요
