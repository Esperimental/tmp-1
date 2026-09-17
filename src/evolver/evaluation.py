from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DIMENSIONS = (
    "planning",
    "investigation",
    "implementation",
    "testing",
    "recovery",
    "efficiency",
    "completion",
)
GATE_RESULTS = {"pass", "fail", "error", "budget_exhausted", "benchmark_invalid"}
SEVERITIES = {"critical", "major", "minor", "observation"}


@dataclass(frozen=True)
class Finding:
    severity: str
    area: str
    evidence: tuple[str, ...]
    description: str
    recommendation: str
    confidence: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Finding":
        severity = str(value["severity"])
        if severity not in SEVERITIES:
            raise ValueError(f"Unsupported finding severity: {severity}")
        confidence = float(value["confidence"])
        if not 0 <= confidence <= 1:
            raise ValueError("Finding confidence must be between 0 and 1")
        evidence = tuple(str(item) for item in value.get("evidence", []))
        if not evidence:
            raise ValueError("Every finding must cite observable evidence")
        return cls(
            severity=severity,
            area=str(value["area"]),
            evidence=evidence,
            description=str(value["description"]),
            recommendation=str(value["recommendation"]),
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "area": self.area,
            "evidence": list(self.evidence),
            "description": self.description,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class TaskEvaluation:
    task_id: str
    gate_result: str
    scores: dict[str, float]
    findings: tuple[Finding, ...] = ()
    strengths: tuple[str, ...] = ()
    improvement_priorities: tuple[str, ...] = ()
    metrics: dict[str, float | int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaskEvaluation":
        gate_result = str(value["gate_result"])
        if gate_result not in GATE_RESULTS:
            raise ValueError(f"Unsupported gate result: {gate_result}")
        raw_scores = value.get("scores", {})
        missing = set(DIMENSIONS) - set(raw_scores)
        extra = set(raw_scores) - set(DIMENSIONS)
        if missing or extra:
            raise ValueError(f"Scores must match dimensions; missing={missing}, extra={extra}")
        scores = {name: float(raw_scores[name]) for name in DIMENSIONS}
        if any(not 0 <= score <= 10 for score in scores.values()):
            raise ValueError("Scores must be between 0 and 10")
        return cls(
            task_id=str(value["task_id"]),
            gate_result=gate_result,
            scores=scores,
            findings=tuple(Finding.from_dict(item) for item in value.get("findings", [])),
            strengths=tuple(str(item) for item in value.get("strengths", [])),
            improvement_priorities=tuple(
                str(item) for item in value.get("improvement_priorities", [])
            ),
            metrics=dict(value.get("metrics", {})),
        )

    @property
    def overall_score(self) -> float:
        return round(sum(self.scores.values()) / len(DIMENSIONS), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "gate_result": self.gate_result,
            "scores": self.scores,
            "overall_score": self.overall_score,
            "findings": [finding.to_dict() for finding in self.findings],
            "strengths": list(self.strengths),
            "improvement_priorities": list(self.improvement_priorities),
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class EvaluationPolicy:
    overall_threshold: float = 6.0
    dimension_floor: float = 4.0

    def failures(self, evaluation: TaskEvaluation) -> list[str]:
        failures: list[str] = []
        if evaluation.gate_result != "pass":
            failures.append(f"objective gate was {evaluation.gate_result}")
        if any(finding.severity == "critical" for finding in evaluation.findings):
            failures.append("critical diagnostic finding")
        if evaluation.overall_score < self.overall_threshold:
            failures.append(
                f"overall score {evaluation.overall_score:.2f} below {self.overall_threshold:.2f}"
            )
        below_floor = [
            f"{name}={score:.1f}"
            for name, score in evaluation.scores.items()
            if score < self.dimension_floor
        ]
        if below_floor:
            failures.append("dimensions below floor: " + ", ".join(below_floor))
        return failures

    def passes(self, evaluation: TaskEvaluation) -> bool:
        return not self.failures(evaluation)


@dataclass(frozen=True)
class EvaluationSuiteReport:
    tasks: tuple[TaskEvaluation, ...]
    policy: EvaluationPolicy

    @property
    def dimension_averages(self) -> dict[str, float]:
        if not self.tasks:
            return {name: 0.0 for name in DIMENSIONS}
        return {
            name: round(sum(task.scores[name] for task in self.tasks) / len(self.tasks), 2)
            for name in DIMENSIONS
        }

    @property
    def passed_tasks(self) -> int:
        return sum(self.policy.passes(task) for task in self.tasks)

    @property
    def passes(self) -> bool:
        return bool(self.tasks) and self.passed_tasks == len(self.tasks)

    def to_markdown(self) -> str:
        lines = [
            "# Evolver evaluation report",
            "",
            f"Suite result: **{'PASS' if self.passes else 'FAIL'}**",
            f"Tasks passing policy: **{self.passed_tasks}/{len(self.tasks)}**",
            "",
            "## Task scores",
            "",
            "| Task | Gate | Overall | Policy | " + " | ".join(DIMENSIONS) + " |",
            "| --- | --- | ---: | --- | " + " | ".join("---:" for _ in DIMENSIONS) + " |",
        ]
        for task in self.tasks:
            lines.append(
                f"| {task.task_id} | {task.gate_result} | {task.overall_score:.2f} | "
                f"{'pass' if self.policy.passes(task) else 'fail'} | "
                + " | ".join(f"{task.scores[name]:.1f}" for name in DIMENSIONS)
                + " |"
            )
        averages = self.dimension_averages
        ordered = sorted(averages.items(), key=lambda item: item[1], reverse=True)
        lines.extend(
            [
                "",
                "## Cross-task profile",
                "",
                "Strongest areas: " + ", ".join(f"{n} ({s:.2f})" for n, s in ordered[:3]),
                "",
                "Weakest areas: " + ", ".join(f"{n} ({s:.2f})" for n, s in ordered[-3:]),
                "",
                "## Issues and improvement priorities",
                "",
            ]
        )
        for task in self.tasks:
            lines.append(f"### {task.task_id}")
            failures = self.policy.failures(task)
            if failures:
                lines.append("Policy failures: " + "; ".join(failures))
            for finding in task.findings:
                lines.append(
                    f"- **{finding.severity} / {finding.area}:** {finding.description} "
                    f"Evidence: {', '.join(finding.evidence)}. "
                    f"Recommendation: {finding.recommendation}"
                )
            for priority in task.improvement_priorities:
                lines.append(f"- Priority: {priority}")
            if not findings_or_priorities(task):
                lines.append("- No issues reported.")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def findings_or_priorities(task: TaskEvaluation) -> bool:
    return bool(task.findings or task.improvement_priorities)
