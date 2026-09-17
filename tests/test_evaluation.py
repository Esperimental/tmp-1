from __future__ import annotations

from evolver.evaluation import (
    DIMENSIONS,
    EvaluationPolicy,
    EvaluationSuiteReport,
    TaskEvaluation,
)


def evaluation(task_id: str, score: float = 7, gate: str = "pass", findings=None):
    return TaskEvaluation.from_dict(
        {
            "task_id": task_id,
            "gate_result": gate,
            "scores": {name: score for name in DIMENSIONS},
            "findings": findings or [],
            "strengths": ["Used tests to confirm the repair"],
            "improvement_priorities": [],
            "metrics": {"tool_calls": 8, "repeated_actions": 0},
        }
    )


def test_policy_requires_objective_gate_even_with_high_scores() -> None:
    result = evaluation("inventory", score=10, gate="fail")
    assert not EvaluationPolicy().passes(result)


def test_policy_rejects_low_dimension_hidden_by_average() -> None:
    value = evaluation("inventory", score=8)
    scores = dict(value.scores)
    scores["efficiency"] = 3
    result = TaskEvaluation(
        task_id=value.task_id,
        gate_result=value.gate_result,
        scores=scores,
    )
    assert result.overall_score > 6
    assert not EvaluationPolicy().passes(result)


def test_policy_rejects_critical_finding() -> None:
    result = evaluation(
        "inventory",
        findings=[
            {
                "severity": "critical",
                "area": "testing",
                "evidence": ["test-run-3"],
                "description": "The agent deleted a failing test.",
                "recommendation": "Protect benchmark tests from mutation.",
                "confidence": 1.0,
            }
        ],
    )
    assert not EvaluationPolicy().passes(result)


def test_suite_report_lists_tasks_and_strength_profile() -> None:
    first = evaluation("inventory-repair", score=7)
    second = evaluation("feature-addition", score=6)
    report = EvaluationSuiteReport((first, second), EvaluationPolicy()).to_markdown()
    assert "inventory-repair" in report
    assert "feature-addition" in report
    assert "Tasks passing policy: **2/2**" in report
    assert "Strongest areas:" in report
    assert "Weakest areas:" in report


def test_empty_suite_does_not_pass() -> None:
    assert not EvaluationSuiteReport((), EvaluationPolicy()).passes
