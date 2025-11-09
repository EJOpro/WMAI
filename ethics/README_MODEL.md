# Ethics 모델 자동 다운로드

## 개요

`binary_classifier.pth` 모델 파일이 없을 경우 서버 실행 시 Google Drive에서 자동으로 다운로드됩니다.

## 자동 다운로드 프로세스

1. 서버 시작 시 `ethics/models/binary_classifier.pth` 파일 존재 여부 확인
2. 파일이 없으면 자동으로 Google Drive에서 다운로드 시작
3. 다운로드 완료 후 모델 로드

## 모델 파일 정보

- **파일명**: `binary_classifier.pth`
- **저장 위치**: `ethics/models/`
- **Google Drive URL**: [다운로드 링크](https://drive.google.com/file/d/1paWpYv5umu0zmmjsC4gyM7HL248tShEh/view?usp=sharing)
- **파일 ID**: `1paWpYv5umu0zmmjsC4gyM7HL248tShEh`

## 수동 다운로드 (옵션)

자동 다운로드가 실패하는 경우 수동으로 다운로드할 수 있습니다:

1. [Google Drive 링크](https://drive.google.com/file/d/1paWpYv5umu0zmmjsC4gyM7HL248tShEh/view?usp=sharing) 접속
2. 파일 다운로드
3. `ethics/models/binary_classifier.pth` 경로에 저장

## 테스트

모델 다운로드를 테스트하려면:

```bash
# 모델 파일 삭제 (테스트용)
rm ethics/models/binary_classifier.pth

# 모델 다운로더 실행
python -m ethics.model_downloader

# 또는 서버 시작 (자동으로 다운로드됨)
python run_server.py
```

## 문제 해결

### 다운로드 실패 시

1. 인터넷 연결 확인
2. Google Drive 접근 가능 여부 확인
3. 수동 다운로드 후 올바른 경로에 저장

### 파일 크기 확인

정상적인 모델 파일은 약 **415 MB**입니다. 
- 파일이 3KB 정도면 Google Drive 보안 페이지가 다운로드된 것입니다.
- 이 경우 `gdown` 라이브러리를 사용하여 해결됩니다.

### gdown 라이브러리가 없는 경우

```bash
pip install gdown
```

gdown이 없으면 자동 다운로드가 실패하고 수동 다운로드 안내가 표시됩니다.

## 의존성

- `gdown>=4.7.1` (Google Drive 대용량 파일 다운로드용)
- `requests>=2.31.0`

### gdown 설치

```bash
pip install gdown
```

또는

```bash
pip install -r requirements.txt
```

## 로그 메시지

- `[INFO] 모델 파일이 이미 존재합니다` - 다운로드 불필요
- `[WARN] 모델 파일을 찾을 수 없습니다` - 다운로드 시작
- `[INFO] Google Drive에서 모델 다운로드 중...` - 다운로드 진행 중
- `[SUCCESS] 모델 다운로드가 완료되었습니다!` - 다운로드 성공
- `[ERROR] 모델 다운로드에 실패했습니다.` - 수동 다운로드 필요

