"""
이탈률 분석 직접 실행 스크립트
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from chrun_backend.chrun_database import get_db, init_db
from chrun_backend.chrun_analytics import ChurnAnalyzer
from sqlalchemy.orm import Session

def run_churn_analysis():
    """이탈률 분석 실행"""
    print("=" * 60)
    print("이탈률 분석 실행")
    print("=" * 60)
    
    # 데이터베이스 초기화
    print("\n[1/3] 데이터베이스 초기화 중...")
    init_db()
    
    # 데이터베이스 연결
    print("[2/3] 데이터베이스 연결 중...")
    db = next(get_db())
    
    try:
        # 분석기 생성
        analyzer = ChurnAnalyzer(db)
        
        # 분석 실행 (2024년 10월 ~ 11월 데이터)
        print("[3/3] 이탈률 분석 실행 중...")
        print("   기간: 2024-10 ~ 2024-11")
        print("   데이터: 3,309개 이벤트 (10월: 1,880개, 11월: 962개, 12월: 467개)")
        
        result = analyzer.run_full_analysis(
            start_month="2024-10",
            end_month="2024-11",
            segments={
                "gender": False,
                "age_band": False,
                "channel": True,
                "combined": False,
                "weekday_pattern": False,
                "time_pattern": False,
                "action_type": False
            },
            inactivity_days=[30, 60, 90],
            threshold=1
        )
        
        # 결과 출력
        print("\n" + "=" * 60)
        print("분석 결과")
        print("=" * 60)
        
        metrics = result.get('metrics', {})
        print(f"\n[전체 이탈률] {metrics.get('churn_rate', 0):.2f}%")
        print(f"   활성 사용자: {metrics.get('active_users', 0):,}명")
        print(f"   이탈 사용자: {metrics.get('churned_users', 0):,}명")
        print(f"   유지 사용자: {metrics.get('retained_users', 0):,}명")
        
        # 채널별 이탈률
        segments = result.get('segments', {})
        if 'channel' in segments:
            print(f"\n[채널별 이탈률]")
            channel_data = segments['channel']
            if isinstance(channel_data, dict):
                for channel, data in channel_data.items():
                    churn_rate = data.get('churn_rate', 0) if isinstance(data, dict) else 0
                    print(f"   {channel}: {churn_rate:.2f}%")
            elif isinstance(channel_data, list):
                for item in channel_data:
                    if isinstance(item, dict):
                        channel = item.get('segment', 'Unknown')
                        churn_rate = item.get('churn_rate', 0)
                        print(f"   {channel}: {churn_rate:.2f}%")
        
        # 트렌드
        trends = result.get('trends', {})
        if trends:
            print(f"\n[월별 트렌드]")
            for month, data in trends.items():
                churn_rate = data.get('churn_rate', 0)
                print(f"   {month}: {churn_rate:.2f}%")
        
        print("\n[완료] 분석 완료!")
        print(f"\n전체 결과는 result 변수에 저장되어 있습니다.")
        print(f"API 서버를 실행하려면: uvicorn chrun_backend.chrun_main:app --reload")
        
        return result
        
    except Exception as e:
        import traceback
        print(f"\n[오류] 오류 발생: {e}")
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    result = run_churn_analysis()

