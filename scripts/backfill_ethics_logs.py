from __future__ import annotations

"""Backfill high-confidence ethics logs into the vector database.

This script reads entries from the `ethics_logs` table, filters high-confidence
cases, and stores them in the `ethics_spam_cases` vector collection so that the
RAG pipeline can leverage historical data.

Usage
-----
python scripts/backfill_ethics_logs.py [--batch-size 200] [--limit 0]

Options
-------
- ``--batch-size``: number of log rows to fetch per iteration (default: 200)
- ``--limit``: maximum number of log rows to process (default: 0 ⇒ unlimited)
- ``--min-confidence``: minimum confidence (or spam confidence) required to
  backfill a log entry (default: 70.0)

Environment
-----------
Requires database credentials (.env / match_config.env) and
``OPENAI_API_KEY`` for generating embeddings. When the API key is missing the
embedding helper returns a zero vector, allowing safe dry runs.
"""

from dataclasses import dataclass
from datetime import datetime
import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Ensure project root is in sys.path when running as a standalone script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import execute_query
from ethics.ethics_embedding import get_embedding
from ethics.ethics_text_splitter import split_to_sentences
from ethics.ethics_vector_db import get_client, upsert_confirmed_case


@dataclass
class EthicsLog:
    """Representation of a row from the ``ethics_logs`` table."""

    id: int
    text: str
    score: float
    spam: float
    confidence: float
    spam_confidence: float
    created_at: Optional[datetime]

    @classmethod
    def from_dict(cls, row: dict) -> "EthicsLog":
        return cls(
            id=row["id"],
            text=row["text"],
            score=float(row.get("score", 0.0) or 0.0),
            spam=float(row.get("spam", 0.0) or 0.0),
            confidence=float(row.get("confidence", 0.0) or 0.0),
            spam_confidence=float(row.get("spam_confidence", 0.0) or 0.0),
            created_at=row.get("created_at"),
        )

    @property
    def max_confidence(self) -> float:
        return max(self.confidence, self.spam_confidence)


def fetch_logs(batch_size: int, offset: int) -> List[EthicsLog]:
    rows = execute_query(
        """
        SELECT id, text, score, spam, confidence, spam_confidence, created_at
        FROM ethics_logs
        ORDER BY id
        LIMIT %s OFFSET %s
        """,
        (batch_size, offset),
        fetch_all=True,
    )
    return [EthicsLog.from_dict(row) for row in (rows or [])]


def should_backfill(log: EthicsLog, min_confidence: float) -> bool:
    return log.text and log.max_confidence >= min_confidence


def upsert_log_sentences(log: EthicsLog, client, min_sentence_length: int = 10) -> int:
    sentences = split_to_sentences(log.text, min_length=min_sentence_length)
    if not sentences:
        return 0

    inserted = 0
    for sentence in sentences:
        embedding = get_embedding(sentence)
        metadata = {
            "sentence": sentence,
            "immoral_score": log.score,
            "spam_score": log.spam,
            "confidence": log.max_confidence,
            "confirmed": False,
            "post_id": f"log_{log.id}",
            "user_id": "",
            "created_at": log.created_at.isoformat() if isinstance(log.created_at, datetime) else datetime.now().isoformat(),
            "feedback_type": "log_backfill",
        }
        upsert_confirmed_case(client=client, embedding=embedding, metadata=metadata)
        inserted += 1
    return inserted


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill ethics_logs into the vector store.")
    parser.add_argument("--batch-size", type=int, default=200, help="Number of logs to fetch per iteration.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of logs to process (0 = unlimited).")
    parser.add_argument("--min-confidence", type=float, default=70.0, help="Minimum confidence required for backfill.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    client = get_client()

    processed_logs = 0
    inserted_sentences = 0
    offset = 0

    try:
        while True:
            if args.limit and processed_logs >= args.limit:
                break

            logs = fetch_logs(batch_size=args.batch_size, offset=offset)
            if not logs:
                break

            for log in logs:
                if args.limit and processed_logs >= args.limit:
                    break

                processed_logs += 1

                if not should_backfill(log, min_confidence=args.min_confidence):
                    continue

                inserted = upsert_log_sentences(log, client=client)
                inserted_sentences += inserted

            offset += args.batch_size

        print(
            f"Backfill completed: processed {processed_logs} logs, "
            f"inserted {inserted_sentences} sentences into the vector store."
        )
        return 0
    except KeyboardInterrupt:
        print("\nBackfill interrupted by user.")
        print(
            f"Progress: processed {processed_logs} logs, "
            f"inserted {inserted_sentences} sentences so far."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
