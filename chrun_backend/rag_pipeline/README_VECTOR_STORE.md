# 벡터 스토어 모듈 가이드

## 개요

벡터 스토어 모듈은 고위험 문장들을 벡터 데이터베이스에 저장하고 검색하는 기능을 제공합니다.
FAISS와 ChromaDB 어댑터를 지원하며, Top-k 검색을 통해 스케일 한계를 해결합니다.

## 주요 기능

### 1. 벡터DB 어댑터 (FAISS/ChromaDB)

- **ChromaDB**: 기본 백엔드, 영구 저장 및 메타데이터 관리
- **FAISS**: 고성능 벡터 검색, 대규모 데이터셋에 적합

### 2. 개인정보 보호

- 텍스트 내 개인정보 자동 마스킹 (이메일, 전화번호, 주민등록번호 등)
- 사용자 ID 익명화 (SHA-256 해시 기반)

### 3. 임베딩 메타데이터 저장

- 임베딩 모델 버전 (`embed_model_v`)
- 임베딩 차원 (`embed_dimension`)
- 타임스탬프 (`ts`)

### 4. High-Risk 확정 시 자동 Upsert

- `confirmed=true`로 설정 시 벡터DB에 자동 저장
- 라벨링 정보 (`who_labeled`, `segment`, `reason`) 포함

### 5. Top-k 검색

- 전수 비교 대신 벡터DB Top-k 검색으로 성능 향상
- `confirmed_only` 옵션으로 확정된 항목만 검색 가능

## 설치

### 필수 패키지

```bash
# ChromaDB (기본)
pip install chromadb

# FAISS (선택)
pip install faiss-cpu  # CPU 버전
# 또는
pip install faiss-gpu  # GPU 버전 (CUDA 필요)
```

### 환경 변수

```bash
# .env 파일
OPENAI_API_KEY=sk-your-openai-api-key-here
VECTOR_STORE_BACKEND=chroma  # 또는 "faiss"
```

## 사용법

### 1. 벡터 스토어 초기화

```python
from rag_pipeline.vector_store import get_vector_store

# ChromaDB 사용 (기본)
vector_store = get_vector_store(backend="chroma")

# FAISS 사용
vector_store = get_vector_store(backend="faiss")
```

### 2. High-Risk 청크 저장

```python
from rag_pipeline.embedding_service import get_embedding

# 임베딩 생성
sentence = "이 서비스 너무 싫어요. 그만둘래요."
embedding = get_embedding(sentence)

# 메타데이터 준비
metadata_dict = {
    "user_id": "user123",
    "post_id": "post456",
    "sentence": sentence,
    "risk_score": 0.85,
    "created_at": "2025-01-01T00:00:00",
}

# 벡터DB에 저장
vector_store.upsert_high_risk_chunk(
    embedding=embedding,
    metadata_dict=metadata_dict,
    confirmed=True,  # 확정된 항목
    who_labeled="admin",
    segment="high_risk",
    reason="탈퇴 의도 명시"
)
```

### 3. Top-k 검색

```python
# 쿼리 임베딩 생성
query_sentence = "더 이상 사용하고 싶지 않아요"
query_embedding = get_embedding(query_sentence)

# Top-k 검색
similar_chunks = vector_store.search_similar_chunks(
    embedding=query_embedding,
    top_k=5,
    similarity_threshold=0.7,
    confirmed_only=True  # 확정된 항목만 검색
)

# 결과 출력
for chunk in similar_chunks:
    print(f"문장: {chunk['sentence']}")
    print(f"유사도: {chunk['similarity_score']:.3f}")
    print(f"위험점수: {chunk['risk_score']:.3f}")
    print("---")
```

### 4. High-Risk 확정 시 Upsert

```python
from rag_pipeline.high_risk_store import update_feedback

# SQLite에서 confirmed 업데이트 및 벡터DB에 upsert
update_feedback(
    chunk_id="chunk_123",
    confirmed=True,
    who_labeled="admin",
    segment="high_risk",
    reason="관리자 확인 완료"
)
```

### 5. 통계 조회

```python
stats = vector_store.get_collection_stats()
print(f"총 문서 수: {stats['total_documents']}")
print(f"백엔드: {stats['backend']}")
print(f"임베딩 모델: {stats['embed_model']}")
print(f"임베딩 차원: {stats['embed_dimension']}")
```

## 인덱스 초기화

### 스크립트 사용

```bash
# 기본 초기화 (ChromaDB)
python -m rag_pipeline.init_vector_index

# FAISS 사용
python -m rag_pipeline.init_vector_index --backend faiss

# SQLite에서 데이터 마이그레이션
python -m rag_pipeline.init_vector_index --migrate --limit 1000

# 인덱스 초기화 (모든 데이터 삭제)
python -m rag_pipeline.init_vector_index --clear
```

### Python 코드로 초기화

```python
from rag_pipeline.init_vector_index import init_vector_index

result = init_vector_index(
    backend="chroma",
    collection_name="high_risk_sentences",
    migrate_from_sqlite=True,
    limit=1000
)

print(f"마이그레이션 완료: {result['migrated_count']}개")
```

## 개인정보 마스킹

### 자동 마스킹

벡터DB에 저장하기 전 자동으로 개인정보가 마스킹됩니다:

- **이메일**: `user@example.com` → `user***@***.com`
- **전화번호**: `010-1234-5678` → `010-****-****`
- **주민등록번호**: `123456-1******` → `123456-******`
- **신용카드**: `1234-5678-9012-3456` → `1234-****-****-3456`

### 사용자 ID 익명화

사용자 ID는 SHA-256 해시로 익명화됩니다:

```python
from rag_pipeline.privacy_utils import anonymize_user_id

original_id = "user_12345"
anonymized = anonymize_user_id(original_id)
# 결과: "user_a1b2c3d4" (해시 기반)
```

## 메타데이터 구조

벡터DB에 저장되는 메타데이터:

```json
{
  "chunk_id": "해시ID",
  "user_id": "익명화된_사용자ID",
  "post_id": "게시물ID",
  "sentence": "마스킹된_문장",
  "risk_score": 0.85,
  "created_at": "2025-01-01T00:00:00",
  "confirmed": true,
  "embed_model_v": "text-embedding-3-small",
  "embed_dimension": 1536,
  "ts": "2025-01-01T00:00:00",
  "who_labeled": "admin",
  "segment": "high_risk",
  "reason": "확정 이유"
}
```

## 성능 비교

### 전수 비교 vs Top-k 검색

| 방식 | 시간 복잡도 | 스케일 한계 |
|------|------------|------------|
| 전수 비교 | O(n) | ~1,000개 |
| 벡터DB Top-k | O(log n) | 수백만 개 |

### 백엔드 비교

| 백엔드 | 장점 | 단점 | 권장 사용 |
|--------|------|------|----------|
| ChromaDB | 메타데이터 관리, 영구 저장 | 메모리 사용량 높음 | 소규모~중규모 |
| FAISS | 고성능, 메모리 효율적 | 메타데이터 관리 복잡 | 대규모 |

## 문제 해결

### ChromaDB 연결 실패

```python
# 연결 상태 확인
vector_store = get_vector_store()
if not vector_store.is_connected:
    print("벡터 스토어 연결 실패")
```

### FAISS 설치 오류

```bash
# CPU 버전 설치
pip install faiss-cpu

# 또는 conda 사용
conda install -c pytorch faiss-cpu
```

### 임베딩 생성 실패

```bash
# OpenAI API 키 확인
export OPENAI_API_KEY=sk-your-key-here

# 또는 .env 파일에 추가
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

## 예제

### 전체 워크플로우

```python
from rag_pipeline.vector_store import get_vector_store
from rag_pipeline.embedding_service import get_embedding
from rag_pipeline.high_risk_store import update_feedback

# 1. 벡터 스토어 초기화
vector_store = get_vector_store(backend="chroma")

# 2. High-Risk 문장 저장
sentence = "이 서비스 떠날까 고민 중이에요"
embedding = get_embedding(sentence)
metadata = {
    "user_id": "user_001",
    "post_id": "post_123",
    "sentence": sentence,
    "risk_score": 0.91,
    "created_at": "2025-01-01T00:00:00",
}
vector_store.upsert_high_risk_chunk(
    embedding=embedding,
    metadata_dict=metadata,
    confirmed=True,
    who_labeled="admin"
)

# 3. 유사 문장 검색
query = "탈퇴할까 생각중입니다"
query_embedding = get_embedding(query)
similar = vector_store.search_similar_chunks(
    embedding=query_embedding,
    top_k=3,
    similarity_threshold=0.7,
    confirmed_only=True
)

# 4. 결과 출력
for chunk in similar:
    print(f"유사도: {chunk['similarity_score']:.3f}")
    print(f"문장: {chunk['sentence']}")
```

## 참고 자료

- [ChromaDB 문서](https://docs.trychroma.com/)
- [FAISS 문서](https://github.com/facebookresearch/faiss)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

