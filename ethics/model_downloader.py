"""
Ethics 모델 자동 다운로드 유틸리티
Google Drive에서 binary_classifier.pth 모델 파일을 자동으로 다운로드합니다.
"""
import os
from pathlib import Path

try:
    import gdown
    GDOWN_AVAILABLE = True
except ImportError:
    GDOWN_AVAILABLE = False
    print("[WARN] gdown 라이브러리가 설치되지 않았습니다.")
    print("[INFO] 설치 방법: pip install gdown")


def download_file_from_google_drive(file_id: str, destination: str) -> bool:
    """
    Google Drive에서 파일을 다운로드합니다.
    gdown 라이브러리를 사용하여 대용량 파일도 안정적으로 다운로드합니다.
    
    Args:
        file_id: Google Drive 파일 ID
        destination: 저장할 파일 경로
        
    Returns:
        bool: 다운로드 성공 여부
    """
    if not GDOWN_AVAILABLE:
        print(f"[ERROR] gdown 라이브러리가 필요합니다.")
        print(f"[INFO] 설치 명령어: pip install gdown")
        return False
    
    try:
        print(f"[INFO] Google Drive에서 모델 다운로드 중...")
        print(f"[INFO] 파일 ID: {file_id}")
        print(f"[INFO] 저장 경로: {destination}")
        print(f"[INFO] 대용량 파일(~415MB) 다운로드 중... 시간이 소요될 수 있습니다.")
        
        # gdown을 사용한 다운로드
        url = f"https://drive.google.com/uc?id={file_id}"
        output = gdown.download(url, destination, quiet=False, fuzzy=True)
        
        # 다운로드 검증
        if output and os.path.exists(destination):
            file_size = os.path.getsize(destination)
            file_size_mb = file_size / (1024 * 1024)
            
            # 최소 100MB 이상이어야 정상 (원본 415MB)
            if file_size > 100 * 1024 * 1024:
                print(f"[SUCCESS] 모델 다운로드 완료!")
                print(f"[INFO] 파일 크기: {file_size:,} bytes ({file_size_mb:.2f} MB)")
                return True
            else:
                print(f"[ERROR] 다운로드된 파일이 너무 작습니다: {file_size:,} bytes ({file_size_mb:.2f} MB)")
                print(f"[ERROR] 예상 크기: ~415 MB")
                print(f"[INFO] Google Drive 보안 페이지가 다운로드되었을 수 있습니다.")
                os.remove(destination)
                return False
        else:
            print(f"[ERROR] 파일 다운로드 실패")
            return False
            
    except Exception as e:
        print(f"[ERROR] 모델 다운로드 중 오류 발생: {e}")
        if os.path.exists(destination):
            os.remove(destination)
        return False


def ensure_model_exists(
    model_path: str = 'ethics/models/binary_classifier.pth',
    file_id: str = '1paWpYv5umu0zmmjsC4gyM7HL248tShEh'
) -> bool:
    """
    모델 파일이 존재하는지 확인하고, 없으면 다운로드합니다.
    
    Args:
        model_path: 모델 파일 경로
        file_id: Google Drive 파일 ID
        
    Returns:
        bool: 모델 파일 준비 완료 여부
    """
    # 모델 파일이 이미 존재하는지 확인
    if os.path.exists(model_path):
        file_size = os.path.getsize(model_path)
        print(f"[INFO] 모델 파일이 이미 존재합니다: {model_path} ({file_size:,} bytes)")
        return True
    
    print(f"[WARN] 모델 파일이 존재하지 않습니다: {model_path}")
    
    # 디렉토리 생성
    model_dir = os.path.dirname(model_path)
    if model_dir:
        os.makedirs(model_dir, exist_ok=True)
        print(f"[INFO] 모델 디렉토리 생성: {model_dir}")
    
    # Google Drive에서 다운로드
    print(f"[INFO] Google Drive에서 모델 다운로드를 시작합니다...")
    success = download_file_from_google_drive(file_id, model_path)
    
    if success:
        print(f"[SUCCESS] 모델 다운로드가 완료되었습니다!")
        return True
    else:
        print(f"[ERROR] 모델 다운로드에 실패했습니다.")
        print(f"[INFO] 수동으로 다운로드하세요:")
        print(f"[INFO] URL: https://drive.google.com/file/d/{file_id}/view")
        print(f"[INFO] 저장 경로: {model_path}")
        return False


if __name__ == "__main__":
    # 테스트용
    ensure_model_exists()

