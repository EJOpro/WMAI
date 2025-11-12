from datetime import datetime
from typing import Optional, Dict, Any


class AnalysisRequest:
    def __init__(
        self,
        user_id: str,
        post_id: str,
        post_type: str,
        text: str,
        created_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.post_id = post_id
        self.post_type = post_type
        self.text = text
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.metadata = metadata or {}


class AnalysisResult:
    def __init__(
        self,
        request: AnalysisRequest,
        risk_score: float,
        priority: str,
        reasons: Optional[list] = None,
        actions: Optional[list] = None,
        evidence: Optional[list] = None,
        decision: Optional[Dict[str, Any]] = None,
    ):
        self.request = request
        self.risk_score = risk_score
        self.priority = priority
        self.reasons = reasons or []
        self.actions = actions or []
        self.evidence = evidence or []
        self.decision = decision or {}


