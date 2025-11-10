"""
Agent 도구 정의
5개 조회 도구 + 2개 실행 도구
조회: semantic_search, churn_analysis, ethics_check, match_reports, trends_analysis
실행: execute_churn_analysis, execute_ethics_analysis
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma
# EnsembleRetriever는 직접 구현
from agent_back.bm25_store import BM25Store

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

# ChromaDB 경로 (프로젝트 루트의 chroma_store 사용)
CHROMA_DB_PATH = PROJECT_ROOT / "chroma_store"

# 임베딩 모델 전역 변수
_embeddings = None
_vectorstore = None
_bm25_store = None
_ensemble_retriever = None

# 최근 검색 결과 저장 (게시글 상세보기에서 사용)
_last_search_board_ids = []


def get_embeddings():
    """BGE-M3 임베딩 모델 반환 (싱글톤)"""
    global _embeddings
    if _embeddings is None:
        from agent_back.bge_m3_embeddings import BGEM3Embeddings
        _embeddings = BGEM3Embeddings()
    return _embeddings


def get_vectorstore():
    """ChromaDB vectorstore 반환 (싱글톤)"""
    global _vectorstore
    if _vectorstore is None:
        embeddings = get_embeddings()
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_DB_PATH),
            embedding_function=embeddings,
            collection_name="board_comments"
        )
    return _vectorstore


def get_bm25_store():
    """BM25Store 반환 (싱글톤)"""
    global _bm25_store
    if _bm25_store is None:
        bm25_path = CHROMA_DB_PATH / "bm25_index.pkl"
        if bm25_path.exists():
            _bm25_store = BM25Store.load_index(str(bm25_path))
        else:
            raise FileNotFoundError(
                f"BM25 인덱스 파일이 없습니다: {bm25_path}\n"
                "먼저 'python embed_board_comments.py'를 실행하여 인덱스를 생성하세요."
            )
    return _bm25_store


def get_ensemble_retriever():
    """EnsembleRetriever 반환 (BM25 + Vector 결합)"""
    global _ensemble_retriever
    if _ensemble_retriever is None:
        try:
            # Vector 검색기와 BM25 검색기를 함께 사용하는 커스텀 검색기
            _ensemble_retriever = CustomEnsembleRetriever()
            print("[OK] CustomEnsembleRetriever 초기화 완료 (BM25 + Vector)")
            
        except Exception as e:
            print(f"[WARN] EnsembleRetriever 초기화 실패: {e}")
            print("[INFO] Vector 검색만 사용합니다.")
            # 실패 시 Vector 검색만 사용
            vectorstore = get_vectorstore()
            _ensemble_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    
    return _ensemble_retriever


class CustomEnsembleRetriever:
    """
    BM25와 Vector 검색을 결합하는 커스텀 앙상블 검색기
    """
    
    def __init__(self, bm25_weight: float = 0.5, vector_weight: float = 0.5):
        """
        Args:
            bm25_weight: BM25 검색 결과 가중치
            vector_weight: Vector 검색 결과 가중치
        """
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
    
    def get_relevant_documents(self, query: str, k: int = 10):
        """
        앙상블 검색 수행
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            
        Returns:
            관련 Document 리스트
        """
        try:
            # BM25 검색
            bm25_store = get_bm25_store()
            bm25_results = bm25_store.search(query, k=k*2)  # 더 많이 가져와서 다양성 확보
            
            # Vector 검색
            vectorstore = get_vectorstore()
            vector_results = vectorstore.similarity_search_with_score(query, k=k*2)
            
            # 결과 통합 및 중복 제거
            combined_docs = {}
            
            # BM25 결과 추가
            for doc, score in bm25_results:
                doc_id = self._get_doc_id(doc)
                if doc_id not in combined_docs:
                    combined_docs[doc_id] = {
                        'doc': doc,
                        'bm25_score': score * self.bm25_weight,
                        'vector_score': 0.0
                    }
            
            # Vector 결과 추가 (점수 정규화)
            for doc, distance in vector_results:
                doc_id = self._get_doc_id(doc)
                # 거리를 유사도로 변환 (거리가 작을수록 유사도 높음)
                similarity = max(0, 1.0 - distance)
                
                if doc_id in combined_docs:
                    combined_docs[doc_id]['vector_score'] = similarity * self.vector_weight
                else:
                    combined_docs[doc_id] = {
                        'doc': doc,
                        'bm25_score': 0.0,
                        'vector_score': similarity * self.vector_weight
                    }
            
            # 최종 점수 계산 및 정렬
            final_results = []
            for doc_info in combined_docs.values():
                final_score = doc_info['bm25_score'] + doc_info['vector_score']
                final_results.append((doc_info['doc'], final_score))
            
            # 점수 내림차순 정렬
            final_results.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 k개 반환
            return [doc for doc, score in final_results[:k]]
            
        except Exception as e:
            print(f"[WARN] 앙상블 검색 실패: {e}")
            # 실패 시 Vector 검색만 사용
            vectorstore = get_vectorstore()
            return vectorstore.similarity_search(query, k=k)
    
    def _get_doc_id(self, doc):
        """문서의 고유 ID 생성"""
        # 메타데이터의 id, type, chunk_index를 조합하여 고유 ID 생성
        doc_id = doc.metadata.get('id', 0)
        doc_type = doc.metadata.get('type', 'unknown')
        chunk_idx = doc.metadata.get('chunk_index', 0)
        return f"{doc_type}_{doc_id}_{chunk_idx}"


@tool
def semantic_search_tool(query: str) -> str:
    """
    커뮤니티 게시글과 댓글을 의미 기반으로 검색합니다 (BM25 + Vector 앙상블).
    사용자가 특정 주제나 키워드에 대한 게시글을 찾을 때 사용하세요.
    
    Args:
        query: 검색할 내용 (예: "육아에 대한 게시글", "요리 레시피")
        
    Returns:
        검색 결과 문자열 (상위 10개 결과 포함) + 게시글 ID 목록
    """
    try:
        # EnsembleRetriever 사용 (BM25 + Vector)
        ensemble_retriever = get_ensemble_retriever()
        
        # 앙상블 검색 수행
        results = ensemble_retriever.get_relevant_documents(query)
        
        if not results:
            return f"'{query}'에 대한 검색 결과가 없습니다."
        
        # 게시글과 댓글 분리 및 ID 수집
        board_ids = []
        comment_ids = []
        board_results = []
        comment_results = []
        
        for doc in results:
            doc_type = doc.metadata.get('type', 'board')
            doc_id = doc.metadata.get('id')
            
            if doc_type == 'board' and doc_id:
                if doc_id not in board_ids:
                    board_ids.append(doc_id)
                    board_results.append(doc)
            elif doc_type == 'comment' and doc_id:
                if doc_id not in comment_ids:
                    comment_ids.append(doc_id)
                    comment_results.append(doc)
        
        # 검색 메타데이터 생성
        search_metadata = {
            'search_method': 'BM25+Vector 앙상블',
            'total_results': len(results),
            'board_count': len(board_results),
            'comment_count': len(comment_results),
            'board_ids': board_ids,
            'comment_ids': comment_ids
        }
        
        # 결과 포맷팅
        output = [f"'{query}'에 대한 앙상블 검색 결과 {len(results)}건 (게시글 {len(board_results)}개, 댓글 {len(comment_results)}개):\n"]
        
        # 전체 결과 표시 (게시글 + 댓글)
        for idx, doc in enumerate(results, 1):
            title = doc.metadata.get('title', '제목 없음')
            author = doc.metadata.get('author', '익명')
            date = doc.metadata.get('date', 'N/A')
            doc_type = doc.metadata.get('type', 'board')
            
            # 청크 정보 추가
            chunk_info = ""
            if doc.metadata.get('chunk_count', 1) > 1:
                chunk_idx = doc.metadata.get('chunk_index', 0)
                chunk_count = doc.metadata.get('chunk_count', 1)
                chunk_info = f" (청크 {chunk_idx+1}/{chunk_count})"
            
            type_text = "📄 게시글" if doc_type == "board" else "💬 댓글"
            
            # 댓글인 경우 게시글 제목 표시
            if doc_type == "comment":
                board_title = doc.metadata.get('board_title', '제목 없음')
                title = f"[댓글] {board_title}"
            
            # 유사도 점수 계산 (순서 기반)
            similarity_score = max(0, 100 - (idx * 5))
            
            output.append(f"\n[{idx}] {type_text} - {title}{chunk_info}")
            output.append(f"작성자: {author} | 날짜: {date} | 유사도: {similarity_score}% | 검색: BM25+Vector 앙상블")
            output.append(f"내용: {doc.page_content[:100]}...")
            output.append("-" * 50)
        
        # 게시글 ID 목록과 메타데이터를 결과에 포함 (JSON 형태로)
        if board_ids:
            # 전역 변수에 검색 결과 저장 (게시글 상세보기에서 사용)
            global _last_search_board_ids
            _last_search_board_ids = board_ids.copy()
            
            output.append(f"\n[BOARD_IDS]: {json.dumps(board_ids)}")
            output.append(f"[SEARCH_QUERY]: {query}")
            output.append(f"[SEARCH_METADATA]: {json.dumps(search_metadata)}")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"검색 중 오류 발생: {str(e)}\n\n" \
               f"BM25 인덱스가 없는 경우 'python embed_board_comments.py'를 실행하여 인덱스를 생성하세요."


@tool
def churn_analysis_tool(query: str) -> str:
    """
    사용자 이탈 분석을 실행합니다.
    이탈률, 이탈 사용자 수, 세그먼트별 분석 등을 확인할 때 사용하세요.
    
    Args:
        query: 분석 요청 내용 (예: "이탈률 알려줘", "어떤 사용자가 이탈하나요")
        
    Returns:
        실행 명령 JSON 문자열
    """
    # 현재 날짜 기준으로 기간 계산 (데이터가 있는 과거 날짜 사용)
    # 2025년 데이터가 없을 수 있으므로 2024년 데이터 사용
    now = datetime(2024, 12, 31)  # 데이터가 있을 가능성이 높은 날짜
    end_month = now.strftime("%Y-%m")
    
    # 3개월 전 계산
    start_date = now - timedelta(days=90)
    start_month = start_date.strftime("%Y-%m")
    
    # 실행 명령 JSON 생성 (API 스키마에 맞게 수정)
    execution_data = {
        "action": "execute_analysis",
        "tool_id": "churn_analysis_tool",
        "api_endpoint": "/api/churn/analysis/run",
        "params": {
            "start_month": start_month,
            "end_month": end_month,
            "segments": {
                "gender": True,
                "age_band": True,
                "channel": True,
                "combined": False,
                "weekday_pattern": False,
                "time_pattern": False,
                "action_type": False
            },
            "inactivity_days": [30, 60, 90],
            "threshold": 1
        },
        "message": f"이탈 분석을 실행합니다 (기간: {start_month} ~ {end_month})"
    }
    
    return json.dumps(execution_data, ensure_ascii=False)


@tool
def ethics_check_tool(query: str) -> str:
    """
    비윤리적 게시글 및 스팸 지수 분석 결과를 조회합니다.
    욕설, 비방, 스팸, 광고 등의 문제 게시글 통계를 확인할 때 사용하세요.
    
    Args:
        query: 조회 요청 내용 (예: "비윤리적인 게시글 있어?", "스팸 얼마나 있어?")
        
    Returns:
        비윤리/스팸 분석 결과 문자열 + 페이지 URL
    """
    try:
        # ethics_logs 테이블에서 실제 데이터 조회 (간단한 통계)
        from app.database import execute_query
        
        # 최근 비윤리 로그 통계
        high_risk = execute_query(
            "SELECT COUNT(*) as count FROM ethics_logs WHERE score >= 70",
            fetch_one=True
        )
        
        spam = execute_query(
            "SELECT COUNT(*) as count FROM ethics_logs WHERE spam >= 70",
            fetch_one=True
        )
        
        total = execute_query(
            "SELECT COUNT(*) as count FROM ethics_logs",
            fetch_one=True
        )
        
        high_risk_count = high_risk['count'] if high_risk else 0
        spam_count = spam['count'] if spam else 0
        total_count = total['count'] if total else 0
        
        if total_count == 0:
            return """⚠️ 비윤리/스팸 분석:
            
아직 분석된 데이터가 없습니다.
게시글과 댓글을 작성하면 자동으로 분석됩니다.

💡 자세한 내용은 대시보드에서 확인하세요.
[페이지 이동: /ethics_dashboard]"""
        
        return f"""⚠️ 비윤리/스팸 분석 결과:

📊 전체 통계:
• 분석된 콘텐츠: {total_count:,}건
• 고위험 콘텐츠: {high_risk_count}건 ({high_risk_count/total_count*100:.1f}%)
• 스팸 감지: {spam_count}건

💡 자세한 내용과 전체 목록은 비윤리/스팸 대시보드에서 확인하세요.
[페이지 이동: /ethics_dashboard]"""
        
    except Exception as e:
        return f"""⚠️ 비윤리/스팸 분석:
        
분석 데이터를 불러오는 중 오류가 발생했습니다.

💡 자세한 내용은 대시보드에서 확인하세요.
[페이지 이동: /ethics_dashboard]"""


@tool
def match_reports_tool(query: str) -> str:
    """
    신고 데이터를 조회하고 통계를 제공합니다.
    신고 유형별 건수, 처리 상태 등을 확인할 때 사용하세요.
    
    Args:
        query: 조회 요청 내용 (예: "신고 많은 게시글", "신고 통계 보여줘")
        
    Returns:
        신고 통계 문자열 + 페이지 URL
    """
    try:
        # report 테이블에서 실제 데이터 조회
        from app.database import execute_query
        
        # 전체 신고 건수
        total_result = execute_query(
            "SELECT COUNT(*) as count FROM report",
            fetch_one=True
        )
        total = total_result['count'] if total_result else 0
        
        if total == 0:
            return """🚨 신고 데이터 통계:

아직 신고 데이터가 없습니다.

💡 자세한 신고 내역과 분석은 신고 분류 페이지에서 확인하세요.
[페이지 이동: /reports]"""
        
        # 처리 상태별 통계
        status_stats = execute_query(
            "SELECT status, COUNT(*) as count FROM report GROUP BY status",
            fetch_all=True
        )
        
        # 신고 유형별 통계 (상위 5개)
        type_stats = execute_query(
            "SELECT report_type, COUNT(*) as count FROM report GROUP BY report_type ORDER BY count DESC LIMIT 5",
            fetch_all=True
        )
        
        output = [f"""🚨 신고 데이터 통계:

📊 전체 신고: {total}건

처리 상태:"""]
        
        status_names = {
            'pending': '대기 중',
            'reviewing': '검토 중',
            'completed': '처리 완료',
            'rejected': '거부됨'
        }
        
        for stat in status_stats:
            status_name = status_names.get(stat['status'], stat['status'])
            output.append(f"• {status_name}: {stat['count']}건")
        
        output.append("\n신고 유형별 TOP 5:")
        for idx, stat in enumerate(type_stats, 1):
            percentage = (stat['count'] / total * 100) if total > 0 else 0
            output.append(f"{idx}. {stat['report_type']}: {stat['count']}건 ({percentage:.1f}%)")
        
        output.append("\n💡 자세한 신고 내역과 분석은 신고 분류 페이지에서 확인하세요.")
        output.append("[페이지 이동: /reports]")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"""🚨 신고 통계:
        
데이터를 불러오는 중 오류가 발생했습니다.

💡 자세한 내용은 신고 페이지에서 확인하세요.
[페이지 이동: /reports]"""


@tool
def trends_analysis_tool(query: str) -> str:
    """
    트렌드 키워드와 인기 검색어를 분석합니다.
    인기 키워드, 급상승 키워드, 트렌드 변화 등을 확인할 때 사용하세요.
    
    Args:
        query: 분석 요청 내용 (예: "트렌드 키워드 알려줘", "인기 검색어는?")
        
    Returns:
        트렌드 분석 결과 문자열 + 페이지 URL
    """
    try:
        # board 테이블에서 최근 인기 게시글 분석
        from app.database import execute_query
        
        # 최근 조회수 높은 게시글의 카테고리 통계
        category_stats = execute_query(
            """SELECT category, COUNT(*) as count, SUM(view_count) as total_views 
               FROM board 
               WHERE status='exposed' 
               GROUP BY category 
               ORDER BY total_views DESC 
               LIMIT 5""",
            fetch_all=True
        )
        
        if not category_stats or len(category_stats) == 0:
            return """📈 트렌드 분석:

아직 충분한 데이터가 없습니다.

💡 자세한 내용은 트렌드 페이지에서 확인하세요.
[페이지 이동: /trends]"""
        
        output = ["""📈 트렌드 분석 결과:

🔥 인기 카테고리 TOP 5:"""]
        
        for idx, stat in enumerate(category_stats, 1):
            output.append(f"{idx}. {stat['category']}: 게시글 {stat['count']}개, 총 조회수 {stat['total_views']:,}회")
        
        output.append("\n💡 자세한 트렌드 분석과 시각화는 트렌드 페이지에서 확인하세요.")
        output.append("[페이지 이동: /trends]")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"""📈 트렌드 분석:
        
데이터를 불러오는 중 오류가 발생했습니다.

💡 자세한 내용은 트렌드 페이지에서 확인하세요.
[페이지 이동: /trends]"""


@tool
def execute_churn_analysis_tool(period_months: int = 3) -> str:
    """
    사용자 이탈 분석을 실행합니다. 
    사용자가 "이탈 분석 실행해줘", "분석 돌려줘" 같은 명령을 하면 이 도구를 사용하세요.
    
    Args:
        period_months: 분석할 기간 (개월 수, 기본값 3개월)
        
    Returns:
        실행 명령 JSON 문자열
    """
    # 현재 날짜 기준으로 기간 계산 (데이터가 있는 과거 날짜 사용)
    # 2025년 데이터가 없을 수 있으므로 2024년 데이터 사용
    now = datetime(2024, 12, 31)  # 데이터가 있을 가능성이 높은 날짜
    end_month = now.strftime("%Y-%m")
    
    # period_months 개월 전 계산
    start_date = now - timedelta(days=30 * period_months)
    start_month = start_date.strftime("%Y-%m")
    
    # 실행 명령 JSON 생성 (API 스키마에 맞게 수정)
    execution_data = {
        "action": "execute_analysis",
        "tool_id": "churn_analysis_tool",
        "api_endpoint": "/api/churn/analysis/run",
        "params": {
            "start_month": start_month,
            "end_month": end_month,
            "segments": {
                "gender": True,
                "age_band": True,
                "channel": True,
                "combined": False,
                "weekday_pattern": False,
                "time_pattern": False,
                "action_type": False
            },
            "inactivity_days": [30, 60, 90],
            "threshold": 1
        },
        "message": f"이탈 분석을 실행합니다 (기간: {start_month} ~ {end_month})"
    }
    
    return json.dumps(execution_data, ensure_ascii=False)


@tool
def execute_ethics_analysis_tool(text: str) -> str:
    """
    비윤리/스팸 분석을 실행합니다.
    사용자가 특정 텍스트에 대해 "비윤리 분석해줘", "스팸 체크해줘" 같은 명령을 하면 사용하세요.
    
    Args:
        text: 분석할 텍스트 내용
        
    Returns:
        실행 명령 JSON 문자열
    """
    execution_data = {
        "action": "execute_analysis",
        "tool_id": "ethics_check_tool",
        "api_endpoint": "/api/ethics/analyze",
        "params": {
            "text": text
        },
        "message": f"비윤리/스팸 분석을 실행합니다"
    }
    
    return json.dumps(execution_data, ensure_ascii=False)


@tool
def approve_report_tool(report_id: int, note: str = "") -> str:
    """
    신고를 승인합니다.
    사용자가 "id #18 승인해줘", "신고 18번 승인" 같은 명령을 하면 사용하세요.
    
    Args:
        report_id: 신고 ID
        note: 처리 사유 (선택)
        
    Returns:
        실행 명령 JSON 문자열
    """
    params = {"action": "approve"}
    if note:  # note가 있을 때만 포함
        params["note"] = note
    
    execution_data = {
        "action": "execute_action",
        "tool_id": "approve_report_tool",
        "api_endpoint": f"/api/admin/reports/{report_id}/process",
        "params": params,
        "message": f"신고 #{report_id}를 승인합니다"
    }
    
    return json.dumps(execution_data, ensure_ascii=False)


@tool
def reject_report_tool(report_id: int, note: str = "") -> str:
    """
    신고를 거부합니다.
    사용자가 "id #18 거부해줘", "신고 18번 거부" 같은 명령을 하면 사용하세요.
    
    Args:
        report_id: 신고 ID
        note: 처리 사유 (선택)
        
    Returns:
        실행 명령 JSON 문자열
    """
    params = {"action": "reject"}
    if note:  # note가 있을 때만 포함
        params["note"] = note
    
    execution_data = {
        "action": "execute_action",
        "tool_id": "reject_report_tool",
        "api_endpoint": f"/api/admin/reports/{report_id}/process",
        "params": params,
        "message": f"신고 #{report_id}를 거부합니다"
    }
    
    return json.dumps(execution_data, ensure_ascii=False)


@tool
def filter_reports_tool(status: str = "all") -> str:
    """
    신고 목록을 필터링합니다.
    사용자가 "대기중 신고 보여줘", "승인된 신고 확인", "거부된 신고", "전체 신고" 같은 명령을 하면 사용하세요.
    
    Args:
        status: 필터 상태 - "pending"(대기중), "approved"(승인), "rejected"(거부), "all"(전체)
        
    Returns:
        필터링 명령 JSON 문자열
    """
    # 한글 상태명을 영문으로 변환
    status_map = {
        "대기중": "pending",
        "대기": "pending",
        "승인": "approved",
        "승인된": "approved",
        "거부": "rejected",
        "거부된": "rejected",
        "전체": "all",
        "모든": "all",
        "모두": "all"
    }
    
    filter_status = status_map.get(status, status)
    
    # 상태 표시명
    status_display = {
        "pending": "대기중",
        "approved": "승인",
        "rejected": "거부",
        "all": "전체"
    }.get(filter_status, "전체")
    
    execution_data = {
        "action": "filter_reports",
        "tool_id": "match_reports_tool",
        "api_endpoint": "/api/admin/reports",
        "filter_params": {
            "status": filter_status if filter_status != "all" else "",
            "type": ""
        },
        "message": f"{status_display} 신고 목록을 표시합니다"
    }
    
    return json.dumps(execution_data, ensure_ascii=False)


@tool
def board_navigation_tool(
    action: str,
    search_query: str = None,
    category: str = None,
    sort_by: str = "latest",
    page: int = 1
) -> str:
    """
    게시판 필터링, 정렬, 페이지 이동을 제어합니다.
    
    Args:
        action: 수행할 액션 ("filter", "sort", "page")
        search_query: 검색어 (action이 "filter"일 때 사용)
        category: 카테고리 필터 ("", "free", "notice", "qna", "review", "tips")
        sort_by: 정렬 방식 ("latest", "popular", "similarity")
        page: 페이지 번호 (action이 "page"일 때 사용)
        
    Returns:
        실행 명령 JSON 문자열
    """
    try:
        # 액션별 처리
        if action == "filter":
            if search_query:
                # 검색어가 있으면 의미 기반 검색 수행
                return semantic_search_tool(search_query)
            else:
                # 카테고리 필터링만
                execution_data = {
                    "action_type": "execute",
                    "tool_id": "board_navigation_tool",
                    "action": "filter_category",
                    "params": {
                        "category": category or ""
                    },
                    "message": f"{'전체' if not category else category} 카테고리로 필터링합니다"
                }
        
        elif action == "sort":
            sort_labels = {
                "latest": "최신순",
                "popular": "인기순", 
                "similarity": "유사도순"
            }
            execution_data = {
                "action_type": "execute",
                "tool_id": "board_navigation_tool",
                "action": "change_sort",
                "params": {
                    "sort_by": sort_by
                },
                "message": f"{sort_labels.get(sort_by, sort_by)}으로 정렬합니다"
            }
        
        elif action == "page":
            execution_data = {
                "action_type": "execute",
                "tool_id": "board_navigation_tool", 
                "action": "navigate_page",
                "params": {
                    "page": page
                },
                "message": f"{page}페이지로 이동합니다"
            }
        
        else:
            return f"알 수 없는 액션입니다: {action}"
        
        return json.dumps(execution_data, ensure_ascii=False)
        
    except Exception as e:
        return f"게시판 조작 중 오류 발생: {str(e)}"


@tool
def board_detail_tool(
    post_id: int = None,
    relative_position: str = None,
    search_context: str = None
) -> str:
    """
    특정 게시글의 상세 정보를 조회합니다.
    
    Args:
        post_id: 게시글 ID (직접 지정)
        relative_position: 상대적 위치 ("첫번째", "두번째", "세번째", "네번째", "다섯번째" 등)
        search_context: 검색 컨텍스트 (최근 검색 결과에서 선택할 때 사용)
        
    Returns:
        실행 명령 JSON 문자열
    """
    try:
        # 상대적 위치를 숫자로 변환
        position_map = {
            "첫번째": 1, "첫째": 1, "1번째": 1, "first": 1,
            "두번째": 2, "둘째": 2, "2번째": 2, "second": 2,
            "세번째": 3, "셋째": 3, "3번째": 3, "third": 3,
            "네번째": 4, "넷째": 4, "4번째": 4, "fourth": 4,
            "다섯번째": 5, "다섯째": 5, "5번째": 5, "fifth": 5,
            "여섯번째": 6, "여섯째": 6, "6번째": 6, "sixth": 6,
            "일곱번째": 7, "일곱째": 7, "7번째": 7, "seventh": 7,
            "여덟번째": 8, "여덟째": 8, "8번째": 8, "eighth": 8,
            "아홉번째": 9, "아홉째": 9, "9번째": 9, "ninth": 9,
            "열번째": 10, "열째": 10, "10번째": 10, "tenth": 10
        }
        
        position_number = None
        if relative_position:
            position_number = position_map.get(relative_position.lower())
        
        # 직접 ID가 지정되지 않고 상대적 위치가 있는 경우, 최근 검색 결과에서 찾기
        if not post_id and position_number:
            # 전역 변수로 최근 검색 결과 저장 (간단한 구현)
            global _last_search_board_ids
            if '_last_search_board_ids' in globals() and _last_search_board_ids:
                if position_number <= len(_last_search_board_ids):
                    post_id = _last_search_board_ids[position_number - 1]
                else:
                    return f"검색 결과에 {relative_position} 게시글이 없습니다. (총 {len(_last_search_board_ids)}개 결과)"
            else:
                # 검색 결과가 없으면 기본 게시글 ID 사용 (데모용)
                # 실제로는 최신 게시글을 조회해야 하지만, 여기서는 간단히 position_number를 ID로 사용
                post_id = position_number
                print(f"[DEBUG] 검색 결과 없음, 기본 ID 사용: {post_id}")
        
        if not post_id and not relative_position:
            return "게시글 ID 또는 상대적 위치를 지정해주세요."
        
        if not post_id:
            return f"'{relative_position}' 위치의 게시글을 찾을 수 없습니다."
        
        execution_data = {
            "action_type": "execute",
            "action": "show_post_detail",
            "tool_id": "board_detail_tool",
            "execution_data": {
                "action": "show_post_detail",
                "tool_id": "board_detail_tool",
                "params": {
                    "post_id": post_id,
                    "relative_position": relative_position
                },
                "message": f"{'게시글 ' + str(post_id) + '번' if post_id else relative_position + ' 게시글'}의 상세 정보를 표시합니다"
            }
        }
        
        return json.dumps(execution_data, ensure_ascii=False)
        
    except Exception as e:
        return f"게시글 상세 조회 중 오류 발생: {str(e)}"


@tool
def board_filter_tool(
    category: str = "",
    sort_by: str = "latest"
) -> str:
    """
    게시판을 카테고리별로 필터링하고 정렬합니다.
    
    Args:
        category: 카테고리 ("", "free", "notice", "qna", "review", "tips")
        sort_by: 정렬 방식 ("latest", "popular", "similarity")
        
    Returns:
        실행 명령 JSON 문자열
    """
    try:
        category_labels = {
            "": "전체",
            "free": "자유게시판",
            "notice": "공지사항", 
            "qna": "질문답변",
            "review": "후기",
            "tips": "팁/노하우"
        }
        
        sort_labels = {
            "latest": "최신순",
            "popular": "인기순",
            "similarity": "유사도순"
        }
        
        execution_data = {
            "action_type": "execute",
            "tool_id": "board_filter_tool",
            "action": "filter_and_sort",
            "params": {
                "category": category,
                "sort_by": sort_by
            },
            "message": f"{category_labels.get(category, '전체')} 카테고리를 {sort_labels.get(sort_by, sort_by)}으로 표시합니다"
        }
        
        return json.dumps(execution_data, ensure_ascii=False)
        
    except Exception as e:
        return f"게시판 필터링 중 오류 발생: {str(e)}"


@tool  
def board_page_tool(page: int) -> str:
    """
    게시판의 특정 페이지로 이동합니다.
    
    Args:
        page: 이동할 페이지 번호
        
    Returns:
        실행 명령 JSON 문자열
    """
    try:
        if page < 1:
            return "페이지 번호는 1 이상이어야 합니다."
        
        execution_data = {
            "action_type": "execute",
            "tool_id": "board_page_tool",
            "action": "navigate_page",
            "params": {
                "page": page
            },
            "message": f"{page}페이지로 이동합니다"
        }
        
        return json.dumps(execution_data, ensure_ascii=False)
        
    except Exception as e:
        return f"페이지 이동 중 오류 발생: {str(e)}"


@tool
def board_list_tool(request_type: str = "back_to_list") -> str:
    """
    게시판 목록으로 돌아가거나 검색 결과를 다시 표시합니다.
    사용자가 "목록으로 돌아가 달라", "뒤로", "검색 결과 보여줘" 등의 명령을 하면 사용하세요.
    
    Args:
        request_type: 요청 타입 ("back_to_list", "show_search_results", "show_board_list")
        
    Returns:
        실행 명령 JSON 문자열
    """
    try:
        # 요청 타입별 메시지 설정
        message_map = {
            "back_to_list": "이전 목록으로 돌아갑니다",
            "show_search_results": "검색 결과를 다시 표시합니다", 
            "show_board_list": "게시판 목록을 표시합니다"
        }
        
        message = message_map.get(request_type, "목록을 표시합니다")
        
        execution_data = {
            "action": "back_to_list",
            "tool_id": "board_list_tool",
            "params": {
                "request_type": request_type
            },
            "message": message
        }
        
        return json.dumps(execution_data, ensure_ascii=False)
        
    except Exception as e:
        return f"목록 표시 중 오류 발생: {str(e)}"


@tool
def daily_report_tool(query: str) -> str:
    """
    오늘의 일일 보고서를 생성합니다.
    "오늘의 할일", "일일 보고서", "오늘의 업무", "데일리 리포트" 등의 명령에 사용하세요.
    
    Args:
        query: 보고서 요청 (예: "오늘의 할일 보여줘")
        
    Returns:
        일일 보고서 텍스트 (신고 현황, 비윤리/스팸 통계, 이탈률, 트렌드)
    """
    try:
        from datetime import datetime
        from app.database import execute_query
        
        # 숫자 포맷팅 함수
        def format_number(num):
            """숫자를 K, M 단위로 포맷팅"""
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            else:
                return f"{num:,}"
        
        # 현재 날짜
        today = datetime.now().strftime("%Y-%m-%d")
        weekday_names = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        weekday = weekday_names[datetime.now().weekday()]
        today_display = datetime.now().strftime(f"%Y년 %m월 %d일 ({weekday})")
        
        report_lines = []
        report_lines.append("╔═══════════════════════════════════════════════════╗")
        report_lines.append("║                                                   ║")
        report_lines.append("║          📋 커뮤니티 일일 운영 보고서              ║")
        report_lines.append("║                                                   ║")
        report_lines.append(f"║          {today_display:^30}           ║")
        report_lines.append("║                                                   ║")
        report_lines.append("╚═══════════════════════════════════════════════════╝")
        report_lines.append("")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1. 신고 및 처리 현황
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  📢 신고 및 처리 현황                           │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            
            # 전체 신고 건수
            total_result = execute_query(
                "SELECT COUNT(*) as count FROM report",
                fetch_one=True
            )
            total_reports = total_result['count'] if total_result else 0
            
            # 처리 상태별 통계
            status_stats = execute_query(
                "SELECT status, COUNT(*) as count FROM report GROUP BY status",
                fetch_all=True
            )
            
            status_counts = {
                'pending': 0,
                'reviewing': 0,
                'completed': 0,
                'rejected': 0
            }
            
            if status_stats:
                for stat in status_stats:
                    status_counts[stat['status']] = stat['count']
            
            # 오늘 접수된 신고
            today_reported = execute_query(
                f"SELECT COUNT(*) as count FROM report WHERE DATE(created_at) = '{today}'",
                fetch_one=True
            )
            today_reports = today_reported['count'] if today_reported else 0
            
            # 오늘 처리된 신고
            today_processed = execute_query(
                f"SELECT COUNT(*) as count FROM report WHERE DATE(processed_date) = '{today}'",
                fetch_one=True
            )
            today_processed_count = today_processed['count'] if today_processed else 0
            
            # 전체 통계
            report_lines.append("  [전체 신고 현황]")
            report_lines.append(f"  • 총 신고 건수: {total_reports:,}건")
            report_lines.append("")
            report_lines.append("  [상태별 분류]")
            report_lines.append(f"    ⏳ 대기중:    {status_counts['pending']:>4}건")
            report_lines.append(f"    ✅ 처리완료:  {status_counts['completed']:>4}건")
            report_lines.append(f"    ❌ 거부됨:    {status_counts['rejected']:>4}건")
            report_lines.append("")
            report_lines.append("  [오늘의 활동]")
            report_lines.append(f"    📥 신규 접수: {today_reports:>4}건")
            report_lines.append(f"    ✔️  처리 완료: {today_processed_count:>4}건")
            report_lines.append("")
            
            if status_counts['pending'] > 10:
                report_lines.append("  ⚠️  주의: 대기중인 신고가 10건 이상입니다!")
                report_lines.append("")
            
        except Exception as e:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  📢 신고 및 처리 현황                           │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            report_lines.append(f"  ⚠️ 데이터 조회 실패: {str(e)}")
            report_lines.append("")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2. 비윤리/스팸 분석통계
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  ⚠️  비윤리/스팸 분석 통계                      │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            
            # 전체 분석된 콘텐츠
            total_ethics = execute_query(
                "SELECT COUNT(*) as count FROM ethics_logs",
                fetch_one=True
            )
            total_ethics_count = total_ethics['count'] if total_ethics else 0
            
            # 고위험 콘텐츠
            high_risk = execute_query(
                "SELECT COUNT(*) as count FROM ethics_logs WHERE score >= 70",
                fetch_one=True
            )
            high_risk_count = high_risk['count'] if high_risk else 0
            
            # 스팸 감지
            spam = execute_query(
                "SELECT COUNT(*) as count FROM ethics_logs WHERE spam >= 70",
                fetch_one=True
            )
            spam_count = spam['count'] if spam else 0
            
            # 오늘 분석된 콘텐츠
            today_ethics = execute_query(
                f"SELECT COUNT(*) as count FROM ethics_logs WHERE DATE(created_at) = '{today}'",
                fetch_one=True
            )
            today_ethics_count = today_ethics['count'] if today_ethics else 0
            
            high_risk_pct = (high_risk_count / total_ethics_count * 100) if total_ethics_count > 0 else 0
            spam_pct = (spam_count / total_ethics_count * 100) if total_ethics_count > 0 else 0
            
            # 위험도 판단
            risk_emoji = "🟢" if high_risk_pct < 3 else "🟡" if high_risk_pct < 5 else "🔴"
            
            report_lines.append("  [전체 분석 현황]")
            report_lines.append(f"  • 분석된 콘텐츠: {format_number(total_ethics_count)}건")
            report_lines.append("")
            report_lines.append("  [위험 콘텐츠 감지]")
            report_lines.append(f"    {risk_emoji} 고위험 콘텐츠: {high_risk_count:>4}건 ({high_risk_pct:>5.1f}%)")
            report_lines.append(f"    🚫 스팸 감지:     {spam_count:>4}건 ({spam_pct:>5.1f}%)")
            report_lines.append("")
            report_lines.append("  [오늘의 분석]")
            report_lines.append(f"    🔍 분석 건수:     {today_ethics_count:>4}건")
            report_lines.append("")
            
            if high_risk_pct >= 5:
                report_lines.append("  🔴 경고: 고위험 콘텐츠 비율이 높습니다!")
                report_lines.append("  💡 /ethics_dashboard 에서 상세 확인 필요")
                report_lines.append("")
            
        except Exception as e:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  ⚠️  비윤리/스팸 분석 통계                      │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            report_lines.append(f"  ⚠️ 데이터 조회 실패: {str(e)}")
            report_lines.append("")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3. 이탈률 체크
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  📉 사용자 이탈률 분석                          │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            
            # 이탈 분석 실행 (간략 버전)
            try:
                from chrun_backend.chrun_analytics import ChurnAnalyzer
                from chrun_backend.chrun_database import get_db
                
                db = next(get_db())
                analyzer = ChurnAnalyzer(db)
                
                # 최근 2개월 데이터로 분석
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                
                start_month = start_date.strftime("%Y-%m")
                end_month = end_date.strftime("%Y-%m")
                
                result = analyzer.run_full_analysis(
                    start_month=start_month,
                    end_month=end_month,
                    segments={
                        "gender": False,
                        "age_band": False,
                        "channel": False,
                        "combined": False,
                        "weekday_pattern": False,
                        "time_pattern": False,
                        "action_type": False
                    },
                    inactivity_days=[30, 60, 90],
                    threshold=1
                )
                
                metrics = result.get("metrics", {})
                insights = result.get("insights", [])
                
                churn_rate = metrics.get("churn_rate", 0)
                churned_users = metrics.get("churned_users", 0)
                active_users = metrics.get("active_users", 0)
                
                # 이탈률 상태 판단
                churn_emoji = "🟢" if churn_rate < 10 else "🟡" if churn_rate < 20 else "🔴"
                churn_status = "양호" if churn_rate < 10 else "주의" if churn_rate < 20 else "위험"
                
                report_lines.append("  [이탈률 현황]")
                report_lines.append(f"  {churn_emoji} 현재 이탈률: {churn_rate:>6.1f}% ({churn_status})")
                report_lines.append("")
                report_lines.append("  [사용자 통계]")
                report_lines.append(f"    👥 활성 사용자: {format_number(active_users):>6}명")
                report_lines.append(f"    👤 이탈 사용자: {format_number(churned_users):>6}명")
                report_lines.append("")
                
                if insights and len(insights) > 0:
                    report_lines.append("  [주요 인사이트]")
                    # 첫 번째 인사이트만 표시 (최대 70자)
                    insight_text = insights[0][:70]
                    if len(insights[0]) > 70:
                        insight_text += "..."
                    report_lines.append(f"    💡 {insight_text}")
                    report_lines.append("")
                
                if churn_rate >= 20:
                    report_lines.append("  🔴 경고: 이탈률이 높습니다!")
                    report_lines.append("  💡 /churn 에서 상세 분석 및 대응 방안 확인")
                    report_lines.append("")
                else:
                    report_lines.append("  💡 자세한 내용: /churn")
                    report_lines.append("")
                
            except Exception as churn_error:
                # 이탈 분석 실패 시
                report_lines.append("  [이탈률 현황]")
                report_lines.append("  ⏳ 데이터 수집 중...")
                report_lines.append("")
                report_lines.append("  💡 자세한 내용: /churn")
                report_lines.append("")
                
        except Exception as e:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  📉 사용자 이탈률 분석                          │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            report_lines.append(f"  ⚠️ 데이터 조회 실패")
            report_lines.append("")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4. 최근 트렌드 분석
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        try:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  📈 커뮤니티 트렌드 분석                        │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            
            # 최근 조회수 높은 게시글의 카테고리 통계
            category_stats = execute_query(
                """SELECT category, COUNT(*) as count, SUM(view_count) as total_views 
                   FROM board 
                   WHERE status='exposed' 
                   GROUP BY category 
                   ORDER BY total_views DESC 
                   LIMIT 3""",
                fetch_all=True
            )
            
            if category_stats and len(category_stats) > 0:
                report_lines.append("  [인기 카테고리 TOP 3]")
                rank_emojis = ["🥇", "🥈", "🥉"]
                for idx, stat in enumerate(category_stats):
                    category = stat['category']
                    count = stat['count']
                    views = stat['total_views']
                    emoji = rank_emojis[idx] if idx < 3 else f"{idx+1}."
                    report_lines.append(f"    {emoji} {category:8} │ {count:>3}개 게시글 │ {format_number(views):>6} 조회")
                report_lines.append("")
                report_lines.append("  💡 자세한 내용: /trends")
                report_lines.append("")
            else:
                report_lines.append("  ⏳ 아직 충분한 데이터가 수집되지 않았습니다.")
                report_lines.append("")
                report_lines.append("  💡 자세한 내용: /trends")
                report_lines.append("")
            
        except Exception as e:
            report_lines.append("┌─────────────────────────────────────────────────┐")
            report_lines.append("│  📈 커뮤니티 트렌드 분석                        │")
            report_lines.append("└─────────────────────────────────────────────────┘")
            report_lines.append("")
            report_lines.append(f"  ⚠️ 데이터 조회 실패: {str(e)}")
            report_lines.append("")
        
        # 마무리
        report_lines.append("╔═══════════════════════════════════════════════════╗")
        report_lines.append("║                                                   ║")
        report_lines.append("║              ✨ 오늘도 좋은 하루 되세요! ✨        ║")
        report_lines.append("║                                                   ║")
        report_lines.append("║  각 섹션의 상세 정보는 해당 페이지에서 확인:      ║")
        report_lines.append("║  • 신고 관리: /admin/reports                      ║")
        report_lines.append("║  • 비윤리/스팸: /ethics_dashboard                 ║")
        report_lines.append("║  • 이탈 분석: /churn                              ║")
        report_lines.append("║  • 트렌드: /trends                                ║")
        report_lines.append("║                                                   ║")
        report_lines.append("╚═══════════════════════════════════════════════════╝")
        
        return "\n".join(report_lines)
        
    except Exception as e:
        return f"""📋 오늘의 일일 보고서

⚠️ 보고서 생성 중 오류가 발생했습니다: {str(e)}

각 섹션의 상세 정보는 다음 페이지에서 확인하세요:
• 신고 현황: /admin/reports
• 비윤리/스팸: /ethics_dashboard
• 이탈 분석: /churn
• 트렌드: /trends"""


# 모든 도구 리스트
AGENT_TOOLS = [
    semantic_search_tool,
    churn_analysis_tool,
    ethics_check_tool,
    match_reports_tool,
    trends_analysis_tool,
    execute_churn_analysis_tool,
    execute_ethics_analysis_tool,
    approve_report_tool,
    reject_report_tool,
    filter_reports_tool,
    board_navigation_tool,
    board_detail_tool,
    board_filter_tool,
    board_page_tool,
    board_list_tool,
    daily_report_tool  # 일일 보고서 생성
]

