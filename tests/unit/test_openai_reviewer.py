import json
from types import SimpleNamespace

from reconciliation_platform.ai.openai_reviewer import OpenAIReviewer
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


class FakeResponses:
    def create(self, **kwargs):
        assert kwargs["model"] == "test-model"
        assert kwargs["text"]["format"]["type"] == "json_schema"
        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "recommendation": "HUMAN_REVIEW",
                    "confidence": 0.83,
                    "rationale": "The evidence remains ambiguous.",
                }
            )
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_reviewer_parses_structured_response():
    reviewer = OpenAIReviewer.__new__(OpenAIReviewer)
    reviewer.client = FakeClient()
    reviewer.model = "test-model"

    decision = ReconciliationDecision(
        "B1", "I1", "REVIEW", "FUZZY", 0.7, "ambiguous", ("near_amount",)
    )
    result = reviewer.review(decision)

    assert result.recommendation == "HUMAN_REVIEW"
    assert result.confidence == 0.83
    assert result.model == "test-model"
