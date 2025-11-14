# Windows에서 Redis 설치 가이드

## 방법 1: Memurai 사용 (권장)

Memurai는 Windows용 Redis 호환 서버입니다.

1. **다운로드**: https://www.memurai.com/get-memurai
2. **설치 후 실행**:
   ```powershell
   # 서비스 시작
   net start Memurai
   
   # 서비스 상태 확인
   sc query Memurai
   ```

## 방법 2: Docker 사용

Docker Desktop이 설치되어 있다면:

```powershell
# Redis 컨테이너 실행
docker run -d --name redis -p 6379:6379 redis:alpine

# 컨테이너 상태 확인
docker ps

# 연결 테스트
docker exec -it redis redis-cli ping
```

## 방법 3: WSL2 + Redis

WSL2가 설치되어 있다면:

```bash
# WSL2에서 실행
sudo apt update
sudo apt install redis-server -y

# Redis 시작
sudo service redis-server start

# 연결 테스트
redis-cli ping
```

## 설치 후 서버 재시작

Redis 설치 후 애플리케이션을 재시작하면 캐싱이 자동으로 활성화됩니다.

```powershell
# 애플리케이션 재시작
# 기존 프로세스 종료 후 다시 시작
```

## 캐싱 효과

- ✅ API 응답 속도 **2-10배 향상**
- ✅ 데이터베이스 부하 **70-90% 감소**
- ✅ 동시 접속자 처리 능력 향상

## 확인 방법

로그에서 다음 메시지가 사라집니다:
```
[트렌드] WARNING | Redis connection failed! Cache will be disabled.
```

대신 정상 시작 메시지가 표시됩니다:
```
[트렌드] INFO | Redis cache enabled
```

