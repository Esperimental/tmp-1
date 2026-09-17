from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from .evaluation import DIMENSIONS, EvaluationPolicy, EvaluationSuiteReport, TaskEvaluation
from .model import _json_object


EVALUATOR_INSTRUCTIONS = """You are an independent evaluator of an autonomous coding agent.
Use only observable evidence in the supplied packet. Assess the agent trajectory, not hidden
chain-of-thought. Return JSON only with this schema:
{
  "task_id": string,
  "gate_result": string,
  "scores": {
    "planning": number, "investigation": number, "implementation": number,
    "testing": number, "recovery": number, "efficiency": number, "completion": number
  },
  "findings": [{
    "severity": "critical"|"major"|"minor"|"observation",
    "area": string, "evidence": [string], "description": string,
    "recommendation": string, "confidence": number
  }],
  "strengths": [string],
  "improvement_priorities": [string],
  "metrics": object
}
Score each dimension from 0 to 10: 0 means absent/harmful, 2 severe failure, 4 substantial
problems, 6 acceptable baseline, 8 strong and efficient, and 10 exceptionally good. Cite
specific evidence IDs for every finding. Detect repeated actions, unchanged test reruns,
no-progress work, excessive investigation, broad changes, weak testing, premature completion,
and work performed after success. Do not invent problems unsupported by the packet. A simple
task can legitimately need little investigation or recovery; score proportionality rather than
rewarding unnecessary activity."""


def build_smoke_packet(root: Path) -> dict[str, Any]:
    state = root / ".evolver"
    runs = [
        {"event_id": f"run-{index}", **json.loads(line)}
        for index, line in enumerate(
            (state / "runs.jsonl").read_text(encoding="utf-8").splitlines(), start=1
        )
        if line.strip()
    ]
    verified = bool(runs) and all(run.get("verified") is True for run in runs)
    commands = [run.get("argv") for run in runs]
    repeated_actions = sum(
        1 for previous, current in zip(commands, commands[1:]) if previous == current
    )
    return {
        "task_id": "hello-world-smoke",
        "objective": (root / "objective.md").read_text(encoding="utf-8").strip(),
        "objective_gate": "pass" if verified else "fail",
        "plan": json.loads((state / "plan.json").read_text(encoding="utf-8")),
        "proposal": json.loads((state / "proposal.json").read_text(encoding="utf-8")),
        "trajectory": runs,
        "final_diff": "No repository change was required for this stdout-only smoke task.",
        "test_results": {"command_verification_passed": verified},
        "mechanical_metrics": {
            "model_calls": 2,
            "tool_calls": len(runs),
            "commands": len(commands),
            "repeated_actions": repeated_actions,
            "no_progress_actions": 0 if verified else len(runs),
        },
    }


class OpenAIEvaluator:
    def __init__(self, model: str | None = None) -> None:
        self.client = OpenAI()
        self.model = model or os.environ.get("EVOLVER_EVAL_MODEL", "gpt-5.6-luna")

    def evaluate(self, packet: dict[str, Any]) -> TaskEvaluation:
        response = self.client.responses.create(
            model=self.model,
            instructions=EVALUATOR_INSTRUCTIONS,
            input="Evaluate this complete recorded task packet:\n" + json.dumps(packet, indent=2),
        )
        value = _json_object(response.output_text)
        value["task_id"] = packet["task_id"]
        value["gate_result"] = packet["objective_gate"]
        value["metrics"] = packet["mechanical_metrics"]
        return TaskEvaluation.from_dict(value)


def evaluate_smoke(root: Path) -> tuple[TaskEvaluation, str, list[str]]:
    packet = build_smoke_packet(root)
    evaluation = OpenAIEvaluator().evaluate(packet)
    policy = EvaluationPolicy()
    report = EvaluationSuiteReport((evaluation,), policy).to_markdown()
    output = root / ".evolver" / "evaluations"
    output.mkdir(parents=True, exist_ok=True)
    (output / "hello-world-smoke.json").write_text(
        json.dumps(evaluation.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    return evaluation, report, policy.failures(evaluation)
