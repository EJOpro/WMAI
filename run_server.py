"""
FastAPI 서버 실행 스크립트
시니어의 팁: 이 파일을 실행하면 메인 서버와 트렌드 서버가 동시에 시작됩니다!
"""

import sys
import os
import subprocess
import signal
import time
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

def start_servers():
    """메인 서버(8000)와 트렌드 서버(8001)를 동시에 실행"""
    
    print("="*60)
    print("  Community Admin + TrendStream API Servers")
    print("="*60)
    print("")
    print("  메인 서버:   http://localhost:8000")
    print("  트렌드 서버: http://localhost:8001")
    print("")
    print("  API 문서:")
    print("    - 메인: http://localhost:8000/docs")
    print("    - 트렌드: http://localhost:8001/v1/docs")
    print("")
    print("  헬스체크:")
    print("    - 메인: http://localhost:8000/health")
    print("    - 트렌드: http://localhost:8001/health")
    print("")
    print("  서버를 종료하려면 Ctrl+C를 누르세요")
    print("="*60)
    print("")
    
    # 프로세스 저장용
    processes = []
    
    try:
        # 1. 메인 서버 시작 (8000번 포트)
        print("[INFO] 메인 서버 시작 중... (포트 8000)")
        main_server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", 
             "--host", "0.0.0.0", "--port", "8000", "--reload"],
            cwd=os.path.dirname(__file__),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        processes.append(main_server)
        time.sleep(2)  # 서버 시작 대기
        
        # 2. 트렌드 서버 시작 (8001번 포트)
        print("[INFO] 트렌드 서버 시작 중... (포트 8001)")
        trend_dir = Path(__file__).parent / "trend"
        trend_server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", 
             "--host", "0.0.0.0", "--port", "8001", "--reload"],
            cwd=str(trend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        processes.append(trend_server)
        time.sleep(2)  # 서버 시작 대기
        
        print("\n[SUCCESS] 두 서버가 모두 시작되었습니다!")
        print("   메인 서버: http://localhost:8000")
        print("   트렌드 서버: http://localhost:8001")
        print("\n[INFO] 트렌드 대시보드를 사용하려면:")
        print("   http://localhost:8000/trends 접속\n")
        
        # 서버 로그 출력 (비동기)
        while True:
            # 메인 서버 로그
            if main_server.poll() is None:
                line = main_server.stdout.readline()
                if line:
                    print(f"[메인] {line.strip()}")
            
            # 트렌드 서버 로그
            if trend_server.poll() is None:
                line = trend_server.stdout.readline()
                if line:
                    print(f"[트렌드] {line.strip()}")
            
            # 두 서버가 모두 종료되었는지 확인
            if main_server.poll() is not None and trend_server.poll() is not None:
                break
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n👋 서버를 종료합니다...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("[SUCCESS] 모든 서버가 종료되었습니다. 안녕히 가세요!")
    
    except Exception as e:
        print(f"\n\n[ERROR] 서버 실행 중 오류 발생: {e}")
        print("\n[DEBUG] 문제 해결 방법:")
        print("  1. requirements.txt 설치 확인:")
        print("     pip install -r requirements.txt")
        print("     pip install -r trend/requirements.txt")
        print("  2. 포트 8000, 8001이 사용 중인지 확인")
        print("  3. Python 버전 확인: python --version (3.11+ 권장)")
        
        # 프로세스 정리
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()

if __name__ == "__main__":
    start_servers()

