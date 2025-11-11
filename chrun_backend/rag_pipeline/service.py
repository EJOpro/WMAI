from datetime import datetime, timezone
from typing import Dict, Any

from .rag_checker import check_new_post
from .models import AnalysisRequest
from .report_repository import save_analysis_result


def analyze_and_store(request: AnalysisRequest) -> Dict[str, Any]:
    context = check_new_post(
        text=request.text,
        user_id=request.user_id,
        post_id=request.post_id,
        created_at=request.created_at,
    )
    decision = context.get("decision", {})
    risk_score = float(decision.get("risk_score", 0.0))
    priority = decision.get("priority", "LOW")

    created_at_value = request.created_at
    if isinstance(created_at_value, str):
        try:
            created_at_value = datetime.fromisoformat(
                created_at_value.replace("Z", "+00:00")
            )
        except ValueError:
            created_at_value = datetime.now(timezone.utc)
    elif created_at_value is None:
        created_at_value = datetime.now(timezone.utc)

    db_payload = {
        "user_id": request.user_id,
        "post_id": request.post_id,
        "post_type": request.post_type,
        "risk_score": risk_score,
        "priority": priority,
        "decision": decision,
        "evidence": context.get("evidence", []),
        "created_at": created_at_value,
    }
    record_id = save_analysis_result(db_payload)

    return {
        "id": record_id,
        "context": context,
    }

