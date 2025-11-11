"""
이미지 분석 기능 디버깅 스크립트
"""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def check_database():
    """데이터베이스 상태 확인"""
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'wmai_db'),
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        print("=" * 60)
        print("데이터베이스 연결 성공!")
        print("=" * 60)
        
        # 1. 테이블 존재 확인
        print("\n[1] 테이블 존재 확인")
        cursor.execute("SHOW TABLES LIKE 'image_analysis_logs'")
        result = cursor.fetchone()
        
        if result:
            print("✅ image_analysis_logs 테이블이 존재합니다.")
            
            # 2. 테이블 구조 확인
            print("\n[2] 테이블 구조")
            cursor.execute("DESCRIBE image_analysis_logs")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")
            
            # 3. 데이터 개수 확인
            print("\n[3] 데이터 확인")
            cursor.execute("SELECT COUNT(*) FROM image_analysis_logs")
            count = cursor.fetchone()[0]
            print(f"  총 로그 개수: {count}")
            
            if count > 0:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_blocked = TRUE THEN 1 ELSE 0 END) as blocked,
                        SUM(CASE WHEN is_nsfw = TRUE THEN 1 ELSE 0 END) as nsfw
                    FROM image_analysis_logs
                """)
                stats = cursor.fetchone()
                print(f"  - 전체: {stats[0]}")
                print(f"  - 차단: {stats[1]}")
                print(f"  - NSFW: {stats[2]}")
                
                # 최근 로그 5개
                print("\n[4] 최근 로그 5개")
                cursor.execute("""
                    SELECT id, filename, is_blocked, created_at
                    FROM image_analysis_logs
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                logs = cursor.fetchall()
                for log in logs:
                    print(f"  ID: {log[0]}, 파일: {log[1]}, 차단: {log[2]}, 시각: {log[3]}")
            else:
                print("  ⚠️ 데이터가 없습니다. 이미지를 업로드하여 테스트해보세요.")
        else:
            print("❌ image_analysis_logs 테이블이 존재하지 않습니다!")
            print("\n해결 방법:")
            print("  mysql -u root -p wmai_db < db/migration_add_image_logs.sql")
        
        # 4. 뷰 확인
        print("\n[5] 뷰 존재 확인")
        cursor.execute("SHOW TABLES LIKE 'v_blocked_images'")
        result = cursor.fetchone()
        if result:
            print("✅ v_blocked_images 뷰가 존재합니다.")
        else:
            print("❌ v_blocked_images 뷰가 존재하지 않습니다!")
        
        # 5. 관리자 권한 확인
        print("\n[6] 관리자 사용자 확인")
        cursor.execute("SELECT id, username, role FROM users WHERE role = 'admin'")
        admins = cursor.fetchall()
        if admins:
            print(f"  관리자 {len(admins)}명 발견:")
            for admin in admins:
                print(f"  - ID: {admin[0]}, 이름: {admin[1]}, 역할: {admin[2]}")
        else:
            print("  ⚠️ 관리자가 없습니다!")
            print("\n해결 방법:")
            print("  UPDATE users SET role = 'admin' WHERE username = '본인아이디';")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("진단 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        print("\n.env 파일의 DB 설정을 확인하세요:")
        print("  DB_HOST=localhost")
        print("  DB_USER=root")
        print("  DB_PASSWORD=비밀번호")
        print("  DB_NAME=wmai_db")

if __name__ == '__main__':
    check_database()

