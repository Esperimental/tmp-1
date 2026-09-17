from __future__ import annotations

import json
from pathlib import Path

from evolver.evaluator import EVALUATOR_INSTRUCTIONS, build_smoke_packet


def test_smoke_packet_contains_complete_observable_trajectory(tmp_path: Path) -> None:
    state = tmp_path / ".evolver"
    state.mkdir()
    (tmp_path / "objective.md").write_text("Print hello\n", encoding="utf-8")
    (state / "plan.json").write_text(
        json.dumps({"objective": "Print hello", "steps": [{"id": "hello"}]}),
        encoding="utf-8",
    )
    (state / "proposal.json").write_text(
        json.dumps({"step_id": "hello", "argv": ["printf", "hello"]}), encoding="utf-8"
    )
    (state / "runs.jsonl").write_text(
        json.dumps(
            {
                "step_id": "hello",
                "argv": ["printf", "hello"],
                "stdout": "hello",
                "stderr": "",
                "exit_code": 0,
                "verified": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    packet = build_smoke_packet(tmp_path)

    assert packet["objective_gate"] == "pass"
    assert packet["trajectory"][0]["event_id"] == "run-1"
    assert packet["trajectory"][0]["stdout"] == "hello"
    assert packet["mechanical_metrics"]["repeated_actions"] == 0


def test_evaluator_prompt_explicitly_detects_inefficiency_and_loops() -> None:
    assert "repeated actions" in EVALUATOR_INSTRUCTIONS
    assert "no-progress" in EVALUATOR_INSTRUCTIONS
    assert "work performed after success" in EVALUATOR_INSTRUCTIONS
