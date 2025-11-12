import uuid
from datetime import datetime
from pathlib import Path
import sys

# Ensure project root on sys.path when running via pytest
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from chrun_backend.rag_pipeline.text_splitter import TextSplitter
from chrun_backend.rag_pipeline.risk_scorer import RiskScorer
from chrun_backend.rag_pipeline.seed_confirmed import seed_confirmed_sentences
from chrun_backend.rag_pipeline import vector_db
from chrun_backend.rag_pipeline.high_risk_store import init_db, get_recent_high_risk
from app.main import app


@pytest.fixture(scope="module")
def api_client():
    with TestClient(app) as client:
        yield client


def test_text_splitter_deterministic():
    splitter = TextSplitter()
    ts = datetime(2025, 1, 1, 12, 0, 0)
    text = "안녕! 반가워요. 오늘은 좋은 날인가요?"
    first = splitter.split_text(text, user_id="u1", post_id="p1", created_at=ts)
    second = splitter.split_text(text, user_id="u1", post_id="p1", created_at=ts)

    assert first == second
    assert len(first) == 3


def test_risk_scorer_provides_reasons():
    scorer = RiskScorer()
    result = scorer.score_sentence("이 서비스는 진짜 최악이야 다시는 쓰고 싶지 않아.")
    assert result["risk_score"] >= 0
    assert result["reasons"], "위험 근거가 비어있습니다."


def test_vector_db_roundtrip(tmp_path):
    client = vector_db.get_client(persist_dir=str(tmp_path / "chroma"))
    collection_name = f"test_collection_{uuid.uuid4().hex}"

    embedding = [0.0] * 1536
    chunk_id = vector_db.build_chunk_id("테스트 문장", "post-1")
    meta = {
        "chunk_id": chunk_id,
        "sentence": "테스트 문장",
        "user_id": "user-x",
        "post_id": "post-1",
        "risk_score": 0.9,
        "created_at": datetime.utcnow().isoformat(),
        "confirmed": True,
    }

    vector_db.upsert_confirmed_chunk(client, embedding, meta, collection_name=collection_name)

    results = vector_db.search_similar(
        client,
        embedding,
        top_k=1,
        min_score=0.0,
        collection_name=collection_name,
    )
    assert results
    assert results[0]["id"] == chunk_id


def test_seed_confirmed_sentences_idempotent():
    seed_confirmed_sentences()
    seed_confirmed_sentences()
    client = vector_db.get_client()
    stats = vector_db.get_collection_stats(client)
    assert stats["total_documents"] > 0


def test_check_new_post_api_success(api_client):
    payload = {
        "text": "요즘 서비스가 너무 별로라서 탈퇴를 고민 중이에요.",
        "user_id": "test_user",
        "post_id": "test_post",
        "created_at": datetime.utcnow().isoformat(),
    }
    response = api_client.post("/api/risk/check_new_post", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert {"post", "decision", "evidence"} <= data.keys()


def test_check_new_post_api_validation_error(api_client):
    bad_payload = {"text": "내용만 있습니다."}
    response = api_client.post("/api/risk/check_new_post", json=bad_payload)
    assert response.status_code == 422


def test_collection_stats_endpoint(api_client):
    resp = api_client.get("/api/risk/collection_stats")
    assert resp.status_code == 200
    body = resp.json()
    assert {"name", "count", "status"} <= body.keys()


def test_feedback_loop_roundtrip(api_client):
    init_db()
    recent = get_recent_high_risk(limit=1)
    assert recent, "샘플 고위험 문장을 찾을 수 없습니다."
    chunk = recent[0]

    payload = {
        "chunk_id": chunk["chunk_id"],
        "confirmed": True,
        "sentence": chunk["sentence"],
        "pred_score": 0.82,
        "final_label": "MATCH",
    }
    response = api_client.post("/api/risk/feedback", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"

    # invalid label should trigger validation error
    invalid_payload = payload.copy()
    invalid_payload["final_label"] = "INVALID"
    invalid_resp = api_client.post("/api/risk/feedback", json=invalid_payload)
    assert invalid_resp.status_code == 422

    list_resp = api_client.get("/api/risk/feedback?limit=5")
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["count"] >= 1


def test_auto_analyze_pipeline(api_client):
    payload = {
        "user_id": "auto_user",
        "post_id": "post_auto_1",
        "post_type": "post",
        "text": "요즘 너무 화가 나서 탈퇴를 고민 중입니다.",
    }
    response = api_client.post("/api/risk/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert "decision" in body

    list_resp = api_client.get("/api/risk/analysis_results?limit=5")
    assert list_resp.status_code == 200
    items = list_resp.json().get("items", [])
    assert any(item["post_id"] == "post_auto_1" for item in items)

