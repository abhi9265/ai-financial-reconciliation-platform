"""OpenAI-backed reviewer for ambiguous reconciliation cases.

This adapter only recommends a disposition for cases already escalated by the
deterministic engine. It never changes the authoritative reconciliation decision.
"""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from reconciliation_platform.ai.reviewer import AIReviewResult, validate_ai_result
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


class OpenAIReviewer:
    """Use the OpenAI Responses API to produce a structured review recommendation."""

    def __init__(self, *, api_key: str, model: str | None = None, timeout: float = 20.0) -> None:
        self.client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model or os.getenv("OPENAI_REVIEW_MODEL", "gpt-5.6-luna")

    def review(self, decision: ReconciliationDecision) -> AIReviewResult:
        payload = {
            "bank_record_id": decision.bank_record_id,
            "candidate_record_id": decision.counterparty_record_id,
            "current_status": decision.status,
            "current_tier": decision.tier,
            "deterministic_confidence": decision.confidence,
            "explanation": decision.explanation,
            "signals": list(decision.signals),
        }
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial reconciliation review assistant. "
                        "Review only the supplied evidence. Never invent missing facts. "
                        "The deterministic engine is authoritative. Your output is a "
                        "recommendation for a human reviewer, not an automatic match."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, sort_keys=True),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "reconciliation_review",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "recommendation": {
                                "type": "string",
                                "enum": ["MATCH", "HUMAN_REVIEW", "UNMATCHED"],
                            },
                            "confidence": {"type": "number"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["recommendation", "confidence", "rationale"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        try:
            result: dict[str, Any] = json.loads(response.output_text)
            recommendation = str(result["recommendation"])
            confidence = float(result["confidence"])
            rationale = str(result["rationale"])
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("OpenAI reviewer returned an invalid structured response") from exc

        confidence = max(0.0, min(1.0, confidence))
        return validate_ai_result(
            AIReviewResult(
                recommendation=recommendation,
                confidence=confidence,
                rationale=rationale,
                model=self.model,
            ),
            decision,
        )
