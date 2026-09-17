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
and work performed after success. A plan records intent but does not prescribe an exact command;
never penalize an equivalent successful approach merely for using a different command or tool.
Do not invent problems unsupported by the packet. A simple
task can legitimately need little investigation or recovery; score proportionality rather than
rewarding unnecessary activity."""


def build_task_packet(
    root: Path,
    task_id: str,
    objective_gate: str | None = None,
    gate_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = root / ".evolver"
    plan = json.loads((state / "plan.json").read_text(encoding="utf-8"))
    runs = [
        {"event_id": f"run-{index}", **json.loads(line)}
        for index, line in enumerate(
            (state / "runs.jsonl").read_text(encoding="utf-8").splitlines(), start=1
        )
        if line.strip()
    ]
    planned_steps = {str(step.get("id")) for step in plan.get("steps", [])}
    verified_steps = {
        str(run.get("step_id")) for run in runs if run.get("verified") is True
    }
    verified = bool(runs) and all(run.get("verified") is True for run in runs)
    verified = verified and planned_steps == verified_steps
    commands = [run.get("argv") for run in runs]
    repeated_actions = sum(
        1 for previous, current in zip(commands, commands[1:]) if previous == current
    )
    return {
        "task_id": task_id,
        "objective": (root / "objective.md").read_text(encoding="utf-8").strip(),
        "objective_gate": objective_gate or ("pass" if verified else "fail"),
        "plan": plan,
        "proposal": json.loads((state / "proposal.json").read_text(encoding="utf-8")),
        "trajectory": runs,
        "workspace_files": {
            str(path.relative_to(root)): path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*"))
            if path.is_file()
            and ".evolver" not in path.parts
            and path.name != "objective.md"
            and path.suffix in {".py", ".json", ".txt", ".md", ".toml", ".yaml", ".yml"}
        },
        "test_results": {"command_verification_passed": verified},
        "acceptance_evidence": gate_evidence or {},
        "mechanical_metrics": {
            "model_calls": 1 + len(runs),
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


def evaluate_task(root: Path, task_id: str, output_path: Path) -> TaskEvaluation:
    packet = build_task_packet(root, task_id)
    evaluation = OpenAIEvaluator().evaluate(packet)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evaluation.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return evaluation


def report_suite(input_dir: Path, output_path: Path) -> EvaluationSuiteReport:
    tasks = tuple(
        TaskEvaluation.from_dict(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(input_dir.glob("*.json"))
    )
    suite = EvaluationSuiteReport(tasks, EvaluationPolicy())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(suite.to_markdown(), encoding="utf-8")
    return suite


# Retained for API compatibility with the original single-task experiment.
def build_smoke_packet(root: Path) -> dict[str, Any]:
    return build_task_packet(root, "hello-world-smoke")
