"""
보고서 출력 스키마 정의 및 검증 모듈
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime


# 공통 출력 스키마 버전
PROMPT_VERSION = "v1.0"
DEFAULT_MODEL = "gpt-4o-mini"


def create_report_schema(
    summary: str,
    risk_level: str,
    evidence: List[Dict[str, Any]],
    actions: List[str],
    model: str = DEFAULT_MODEL,
    prompt_v: str = PROMPT_VERSION,
    warnings: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    공통 출력 스키마로 보고서 생성
    
    Args:
        summary (str): 요약 설명
        risk_level (str): 위험 수준 ("low", "medium", "high")
        evidence (List[Dict]): 증거 리스트 [{"id": str, "snippet": str, "similarity": float}]
        actions (List[str]): 조치사항 리스트 (최소 3개)
        model (str): 사용한 LLM 모델명
        prompt_v (str): 프롬프트 버전
        warnings (List[str], optional): 경고 메시지 리스트
        
    Returns:
        Dict[str, Any]: 공통 스키마 형식의 보고서
    """
    # risk_level 정규화
    risk_level = risk_level.lower()
    if risk_level not in ["low", "medium", "high"]:
        risk_level = "medium"
    
    # evidence 검증 및 경고
    evidence_warnings = []
    if len(evidence) < 2:
        evidence_warnings.append(f"evidence가 {len(evidence)}건으로 부족합니다 (최소 2건 권장)")
    
    # actions 최소 3개 보장
    if len(actions) < 3:
        actions = actions + ["추가 조치사항 검토 필요"] * (3 - len(actions))
    
    # warnings 통합
    all_warnings = (warnings or []) + evidence_warnings
    
    report = {
        "summary": summary,
        "risk_level": risk_level,
        "evidence": evidence,
        "actions": actions[:10],  # 최대 10개
        "model": model,
        "prompt_v": prompt_v
    }
    
    if all_warnings:
        report["warnings"] = all_warnings
    
    return report


def validate_report_schema(report: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    보고서 스키마 검증
    
    Args:
        report (Dict[str, Any]): 검증할 보고서
        
    Returns:
        tuple[bool, Optional[str]]: (유효성, 오류 메시지)
    """
    # 필수 필드 확인
    required_fields = ["summary", "risk_level", "evidence", "actions", "model", "prompt_v"]
    for field in required_fields:
        if field not in report:
            return False, f"필수 필드 누락: {field}"
    
    # risk_level 검증
    if report["risk_level"] not in ["low", "medium", "high"]:
        return False, f"잘못된 risk_level: {report['risk_level']}"
    
    # evidence 검증
    if not isinstance(report["evidence"], list):
        return False, "evidence는 리스트여야 합니다"
    
    for i, ev in enumerate(report["evidence"]):
        if not isinstance(ev, dict):
            return False, f"evidence[{i}]는 딕셔너리여야 합니다"
        if "id" not in ev or "snippet" not in ev or "similarity" not in ev:
            return False, f"evidence[{i}]에 필수 필드(id, snippet, similarity)가 없습니다"
    
    # actions 검증
    if not isinstance(report["actions"], list):
        return False, "actions는 리스트여야 합니다"
    
    if len(report["actions"]) < 3:
        return False, "actions는 최소 3개 이상이어야 합니다"
    
    return True, None


def format_evidence_from_similar_patterns(similar_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    similar_patterns를 evidence 형식으로 변환
    
    Args:
        similar_patterns (List[Dict]): 유사 패턴 리스트
        
    Returns:
        List[Dict]: evidence 형식 리스트
    """
    evidence_list = []
    
    for pattern in similar_patterns:
        chunk_id = pattern.get('chunk_id', '')
        sentence = pattern.get('sentence', '')
        similarity = pattern.get('similarity_score', 0.0)
        
        evidence_list.append({
            "id": chunk_id[:16] if chunk_id else f"ev_{len(evidence_list)}",
            "snippet": sentence[:200],  # 최대 200자
            "similarity": round(float(similarity), 3)
        })
    
    return evidence_list



