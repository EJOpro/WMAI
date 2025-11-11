"""
게시글과 댓글을 임베딩하여 ChromaDB에 저장하는 스크립트

실행 방법:
    python embed_board_comments.py

요구사항:
    - MySQL DB에 게시글(board)과 댓글(comment) 테이블 필요
    - BGE-M3 모델 (최초 실행 시 자동 다운로드)
"""

import os
from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from app.database import execute_query
from agent_back.bge_m3_embeddings import BGEM3Embeddings
from agent_back.semantic_chunker import SemanticChunker
from agent_back.bm25_store import BM25Store

# ChromaDB 저장 경로
CHROMA_DB_PATH = Path("chroma_store")

def fetch_boards():
    """DB에서 exposed 상태의 게시글 가져오기"""
    try:
        query = """
        SELECT b.id, b.title, b.content, b.category, b.created_at, u.username
        FROM board b
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.status = 'exposed'
        ORDER BY b.created_at DESC
        """
        boards = execute_query(query, fetch_all=True)
        print(f"[OK] 게시글 {len(boards)}개 조회 완료")
        return boards
    except Exception as e:
        print(f"[ERROR] 게시글 조회 실패: {e}")
        return []


def fetch_comments():
    """DB에서 exposed 상태의 댓글 가져오기"""
    try:
        query = """
        SELECT c.id, c.content, c.board_id, c.created_at, u.username, b.title as board_title
        FROM comment c
        LEFT JOIN users u ON c.user_id = u.id
        LEFT JOIN board b ON c.board_id = b.id
        WHERE c.status = 'exposed'
        ORDER BY c.created_at DESC
        """
        comments = execute_query(query, fetch_all=True)
        print(f"[OK] 댓글 {len(comments)}개 조회 완료")
        return comments
    except Exception as e:
        print(f"[ERROR] 댓글 조회 실패: {e}")
        return []


def create_documents(boards, comments):
    """게시글과 댓글을 Document 객체로 변환 (SemanticChunker 적용)"""
    documents = []
    
    # SemanticChunker 초기화 (사용자 지정 설정값 적용)
    print("[1/3] SemanticChunker 초기화 중...")
    chunker = SemanticChunker(
        similarity_threshold=0.75,
        min_chunk_size=80,
        max_chunk_size=1200
    )
    
    print("[2/3] 게시글 청킹 및 Document 생성 중...")
    # 게시글 Document 생성 (청킹 적용)
    for board in boards:
        # 제목과 내용을 합쳐서 청킹
        full_content = f"제목: {board['title']}\n\n{board['content']}"
        
        # SemanticChunker로 청크 분할
        chunks = chunker.chunk_text(full_content)
        
        # 각 청크를 개별 Document로 생성
        for chunk_idx, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "id": board['id'],
                    "type": "board",
                    "title": board['title'],
                    "author": board['username'] or '익명',
                    "date": str(board['created_at']),
                    "category": board['category'],
                    "chunk_index": chunk_idx,
                    "chunk_count": len(chunks),
                    "chunk_size": len(chunk)
                }
            )
            documents.append(doc)
    
    print("[3/3] 댓글 Document 생성 중...")
    # 댓글 Document 생성 (댓글은 보통 짧으므로 청킹하지 않음)
    for comment in comments:
        # 댓글이 충분히 길면 청킹 적용
        if len(comment['content']) > 200:
            chunks = chunker.chunk_text(comment['content'])
            for chunk_idx, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "id": comment['id'],
                        "type": "comment",
                        "board_id": comment['board_id'],
                        "board_title": comment['board_title'] or '제목 없음',
                        "author": comment['username'] or '익명',
                        "date": str(comment['created_at']),
                        "chunk_index": chunk_idx,
                        "chunk_count": len(chunks),
                        "chunk_size": len(chunk)
                    }
                )
                documents.append(doc)
        else:
            # 짧은 댓글은 그대로 사용
            doc = Document(
                page_content=comment['content'],
                metadata={
                    "id": comment['id'],
                    "type": "comment",
                    "board_id": comment['board_id'],
                    "board_title": comment['board_title'] or '제목 없음',
                    "author": comment['username'] or '익명',
                    "date": str(comment['created_at']),
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "chunk_size": len(comment['content'])
                }
            )
            documents.append(doc)
    
    print(f"[OK] Document 객체 {len(documents)}개 생성 완료 (청킹 적용)")
    return documents


def embed_and_store(documents):
    """Document를 임베딩하여 ChromaDB에 저장하고 BM25 인덱스도 생성"""
    try:
        print("\n[1/4] BGE-M3 임베딩 모델 로딩 중...")
        embeddings = BGEM3Embeddings()
        
        print("\n[2/4] ChromaDB 초기화 중...")
        # 기존 컬렉션이 있다면 삭제하고 새로 생성
        if CHROMA_DB_PATH.exists():
            import shutil
            import time
            import os
            import stat
            print(f"  [WARN] 기존 ChromaDB 삭제 시도: {CHROMA_DB_PATH}")
            
            # Windows에서 파일 속성 변경 후 삭제 시도
            def remove_readonly(func, path, exc):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except:
                    pass  # 삭제 실패해도 계속 진행
            
            try:
                shutil.rmtree(CHROMA_DB_PATH, onerror=remove_readonly)
                print("  [OK] 기존 ChromaDB 삭제 완료")
            except PermissionError:
                print("  [WARN] 파일이 사용 중입니다. 덮어쓰기 방식으로 진행합니다...")
                # 삭제 실패해도 계속 진행 (ChromaDB가 자동으로 덮어씀)
        
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[3/4] 임베딩 생성 및 저장 중... (총 {len(documents)}개)")
        print("  이 작업은 문서 수에 따라 수 분이 소요될 수 있습니다.")
        
        # ChromaDB에 저장 (자동으로 임베딩 생성)
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=str(CHROMA_DB_PATH),
            collection_name="board_comments"
        )
        
        print(f"\n[OK] 벡터 임베딩 완료 및 저장 완료: {CHROMA_DB_PATH}")
        print(f"[OK] 총 {len(documents)}개 문서가 벡터 DB에 저장되었습니다.")
        
        print(f"\n[4/4] BM25 인덱스 생성 및 저장 중...")
        # BM25 인덱스 생성
        bm25_store = BM25Store()
        bm25_store.create_bm25_index(documents)
        
        # BM25 인덱스 저장
        bm25_path = CHROMA_DB_PATH / "bm25_index.pkl"
        bm25_store.save_index(str(bm25_path))
        
        print(f"[OK] BM25 인덱스 저장 완료: {bm25_path}")
        
        # 간단한 검색 테스트
        print("\n[테스트] '육아' 벡터 검색 결과:")
        vector_results = vectorstore.similarity_search("육아", k=3)
        for idx, doc in enumerate(vector_results, 1):
            doc_type = "게시글" if doc.metadata['type'] == 'board' else "댓글"
            title = doc.metadata.get('title', doc.metadata.get('board_title', '제목 없음'))
            chunk_info = f" (청크 {doc.metadata.get('chunk_index', 0)+1}/{doc.metadata.get('chunk_count', 1)})" if doc.metadata.get('chunk_count', 1) > 1 else ""
            print(f"  {idx}. [{doc_type}] {title}{chunk_info}")
            print(f"     내용: {doc.page_content[:50]}...")
        
        print("\n[테스트] '육아' BM25 검색 결과:")
        bm25_results = bm25_store.search("육아", k=3)
        for idx, (doc, score) in enumerate(bm25_results, 1):
            doc_type = "게시글" if doc.metadata['type'] == 'board' else "댓글"
            title = doc.metadata.get('title', doc.metadata.get('board_title', '제목 없음'))
            chunk_info = f" (청크 {doc.metadata.get('chunk_index', 0)+1}/{doc.metadata.get('chunk_count', 1)})" if doc.metadata.get('chunk_count', 1) > 1 else ""
            print(f"  {idx}. [{doc_type}] {title}{chunk_info} (점수: {score:.3f})")
            print(f"     내용: {doc.page_content[:50]}...")
        
        # Rerank 테스트 추가
        try:
            print("\n[테스트] BGE Reranker 성능 비교:")
            print("="*60)
            from agent_back.reranker import BGEReranker
            
            reranker = BGEReranker()
            test_query = "육아"
            
            # Vector 검색으로 후보 10개 가져오기
            candidates = vectorstore.similarity_search(test_query, k=10)
            
            print(f"\n[Before Rerank] Vector 검색 결과 (상위 5개):")
            for idx, doc in enumerate(candidates[:5], 1):
                doc_type = "게시글" if doc.metadata['type'] == 'board' else "댓글"
                title = doc.metadata.get('title', doc.metadata.get('board_title', '제목 없음'))
                chunk_info = f" (청크 {doc.metadata.get('chunk_index', 0)+1}/{doc.metadata.get('chunk_count', 1)})" if doc.metadata.get('chunk_count', 1) > 1 else ""
                print(f"  {idx}. [{doc_type}] {title}{chunk_info}")
                print(f"     내용: {doc.page_content[:80]}...")
            
            # Rerank 적용
            reranked = reranker.rerank(test_query, candidates, top_k=5)
            
            print(f"\n[After Rerank] Rerank 적용 결과 (상위 5개):")
            for idx, (doc, rerank_score) in enumerate(reranked, 1):
                doc_type = "게시글" if doc.metadata['type'] == 'board' else "댓글"
                title = doc.metadata.get('title', doc.metadata.get('board_title', '제목 없음'))
                chunk_info = f" (청크 {doc.metadata.get('chunk_index', 0)+1}/{doc.metadata.get('chunk_count', 1)})" if doc.metadata.get('chunk_count', 1) > 1 else ""
                print(f"  {idx}. [{doc_type}] {title}{chunk_info} (Rerank 점수: {rerank_score:.4f})")
                print(f"     내용: {doc.page_content[:80]}...")
            
            print("\n" + "="*60)
            print("[OK] Reranker 테스트 완료!")
            print("="*60)
            print("💡 Reranker는 쿼리와 문서의 직접적인 관련성을 평가하여")
            print("   검색 결과의 순서를 최적화합니다.")
            print("   실제 검색 시에는 자동으로 Rerank가 적용됩니다.")
            
        except Exception as rerank_error:
            print(f"\n[WARN] Reranker 테스트 중 오류 발생: {rerank_error}")
            print("Reranker는 선택적 기능이므로 기본 검색은 정상 작동합니다.")
        
        return vectorstore
        
    except Exception as e:
        print(f"\n[ERROR] 임베딩/인덱스 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """메인 실행 함수"""
    print("="*60)
    print("게시글/댓글 임베딩 생성 스크립트")
    print("="*60)
    
    # 1. DB에서 데이터 가져오기
    print("\n[Step 1] 데이터베이스에서 게시글과 댓글 조회 중...")
    boards = fetch_boards()
    comments = fetch_comments()
    
    if len(boards) == 0 and len(comments) == 0:
        print("\n[WARN] 임베딩할 데이터가 없습니다.")
        print("   게시글이나 댓글을 먼저 작성해주세요.")
        return
    
    # 2. Document 객체 생성
    print("\n[Step 2] Document 객체 생성 중...")
    documents = create_documents(boards, comments)
    
    # 3. 임베딩 생성 및 저장
    print("\n[Step 3] 임베딩 생성 및 ChromaDB 저장 중...")
    vectorstore = embed_and_store(documents)
    
    if vectorstore:
        print("\n" + "="*60)
        print("[SUCCESS] 임베딩 생성 완료!")
        print("="*60)
        print(f"저장 위치: {CHROMA_DB_PATH.absolute()}")
        print(f"게시글: {len(boards)}개")
        print(f"댓글: {len(comments)}개")
        print(f"총 문서: {len(documents)}개")
        print("\n이제 Agent Chatbot을 사용할 수 있습니다!")
        print("서버 실행: python run_server.py")
    else:
        print("\n[FAILED] 임베딩 생성 실패")


if __name__ == "__main__":
    main()

