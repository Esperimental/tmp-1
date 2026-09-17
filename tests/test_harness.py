from __future__ import annotations

import json
import sys
from pathlib import Path

from evolver.domain import Plan, Step, Verification
from evolver.evaluation import DIMENSIONS, TaskEvaluation
from evolver.harness import TaskDefinition, discover_tasks, run_task


class RepairModel:
    @property
    def model_name(self) -> str:
        return "fake-repair-model"

    def create_plan(self, objective: str, repository_summary: str) -> Plan:
        fixed = "def add(a, b):\n    return a + b\n"
        return Plan(
            objective,
            (
                Step("observe", "Run tests", Verification("exit_code_equals", "1")),
                Step(
                    "repair",
                    "Repair calc.py",
                    Verification("file_content_equals", fixed, "calc.py"),
                ),
                Step("verify", "Rerun tests", Verification("exit_code_equals", "0")),
            ),
        )

    def propose_command(self, step: Step, repository_summary: str) -> list[str]:
        if step.id in {"observe", "verify"}:
            return [sys.executable, "-m", "unittest", "-q"]
        return [
            sys.executable,
            "-c",
            "from pathlib import Path; Path('calc.py').write_text('def add(a, b):\\n    return a + b\\n')",
        ]


class EvidenceEvaluator:
    def evaluate(self, packet: dict) -> TaskEvaluation:
        return TaskEvaluation(
            task_id=packet["task_id"],
            gate_result=packet["objective_gate"],
            scores={name: 8.0 for name in DIMENSIONS},
            metrics=packet["mechanical_metrics"],
        )


def make_repair_task(tmp_path: Path) -> Path:
    task = tmp_path / "evals" / "mid-range" / "repair"
    task.mkdir(parents=True)
    (task / "task.json").write_text(
        json.dumps(
            {
                "id": "repair",
                "phase": "mid-range",
                "max_commands": 4,
                "acceptance": {"argv": [sys.executable, "-m", "unittest", "-q"]},
                "protected_paths": ["test_calc.py"],
            }
        ),
        encoding="utf-8",
    )
    (task / "objective.md").write_text("Repair the calculator\n", encoding="utf-8")
    (task / "calc.py").write_text("def add(a, b):\n    return b\n", encoding="utf-8")
    (task / "test_calc.py").write_text(
        "import unittest\nfrom calc import add\n\n"
        "class Tests(unittest.TestCase):\n"
        "    def test_add(self): self.assertEqual(add(2, 3), 5)\n",
        encoding="utf-8",
    )
    return task


def test_one_mid_range_task_can_run_in_isolation(tmp_path: Path) -> None:
    task = make_repair_task(tmp_path)
    output = tmp_path / "results"

    evaluation = run_task(
        TaskDefinition.load(task), output, model=RepairModel(), evaluator=EvidenceEvaluator()
    )

    assert evaluation.gate_result == "pass"
    assert evaluation.metrics["commands"] == 3
    assert (output / "repair.json").exists()
    evidence = json.loads((output / "repair.evidence.json").read_text(encoding="utf-8"))
    assert len(evidence["trajectory"]) == 3
    assert evidence["acceptance_evidence"]["protected_changes"] == []


def test_tasks_can_be_selected_by_phase(tmp_path: Path) -> None:
    task = make_repair_task(tmp_path)

    assert discover_tasks(tmp_path / "evals", "simple") == []
    assert discover_tasks(tmp_path / "evals", "mid-range") == [TaskDefinition.load(task)]
