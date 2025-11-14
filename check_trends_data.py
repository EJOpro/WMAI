"""트렌드 데이터 확인 스크립트"""
from app.database import get_db_connection

print("=" * 60)
print("트렌드 데이터베이스 확인")
print("=" * 60)

try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 테이블 존재 확인
        print("\n1. 테이블 존재 확인:")
        cursor.execute("SHOW TABLES LIKE 'trend%'")
        tables = cursor.fetchall()
        
        if tables:
            for table in tables:
                table_name = list(table.values())[0]
                print(f"   [OK] {table_name}")
        else:
            print("   [ERROR] trend 관련 테이블이 없습니다!")
            print("\n해결 방법:")
            print("   mysql -u root -p wmai_db < db/migration_add_trend_keywords.sql")
            exit(1)
        
        # 2. trend_keywords 데이터 확인
        print("\n2. trend_keywords 데이터 확인:")
        cursor.execute("SELECT COUNT(*) as cnt FROM trend_keywords")
        result = cursor.fetchone()
        count = result['cnt']
        print(f"   총 {count}개 키워드")
        
        if count == 0:
            print("   [ERROR] 데이터가 없습니다!")
            print("\n해결 방법:")
            print("   mysql -u root -p wmai_db < db/trend_dummy_data.sql")
            exit(1)
        
        # 3. 샘플 데이터 조회
        print("\n3. 샘플 데이터 (최근 3개):")
        cursor.execute("""
            SELECT keyword, search_count, search_date, category 
            FROM trend_keywords 
            ORDER BY search_date DESC, search_count DESC 
            LIMIT 3
        """)
        samples = cursor.fetchall()
        
        for sample in samples:
            print(f"   - {sample['keyword']}: {sample['search_count']}회 (날짜: {sample['search_date']}, 카테고리: {sample['category']})")
        
        # 4. 통계 캐시 확인
        print("\n4. trend_stats_cache 데이터:")
        cursor.execute("SELECT * FROM trend_stats_cache ORDER BY stat_date DESC LIMIT 1")
        stats = cursor.fetchone()
        
        if stats:
            print(f"   날짜: {stats['stat_date']}")
            print(f"   게시글: {stats['total_posts']}개")
            print(f"   댓글: {stats['total_comments']}개")
        else:
            print("   [WARNING] 통계 캐시 데이터 없음 (선택사항)")
        
        cursor.close()
    
    print("\n" + "=" * 60)
    print("[OK] 모든 확인 완료! 데이터가 정상입니다.")
    print("=" * 60)
    print("\n이제 서버를 실행하세요:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("\n그리고 브라우저에서 확인하세요:")
    print("   http://localhost:8000/trends")
    print("   http://localhost:8000/api/trends")
    
except Exception as e:
    print(f"\n[ERROR] 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n해결 방법:")
    print("1. MySQL 서버가 실행 중인지 확인")
    print("2. 데이터베이스 wmai_db가 생성되어 있는지 확인")
    print("3. .env 또는 match_config.env 파일의 DB 설정 확인")

