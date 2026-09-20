from reconciliation_platform.ai.reviewer import NoOpAIReviewer, escalate_reviews
from reconciliation_platform.evaluation.metrics import evaluate
from reconciliation_platform.reconciliation.engine import ReconciliationDecision

def test_ai_escalation_is_safe_by_default():
    d=ReconciliationDecision("B1","I1","REVIEW","DETERMINISTIC_EXCEPTION",0.5,"amount mismatch",("exact_reference",))
    result=escalate_reviews([d],NoOpAIReviewer())["B1"]
    assert result.recommendation=="HUMAN_REVIEW"
    assert result.model=="none"

def test_evaluation_metrics():
    ds=[
      ReconciliationDecision("B1","I1","MATCHED","DETERMINISTIC",1.0,"ok",()),
      ReconciliationDecision("B2","I2","REVIEW","FUZZY",0.7,"review",()),
      ReconciliationDecision("B3",None,"UNMATCHED","NONE",0.0,"none",()),
    ]
    m=evaluate(ds)
    assert (m.total,m.matched,m.review,m.unmatched)==(3,1,1,1)
    assert m.auto_match_rate==1/3
