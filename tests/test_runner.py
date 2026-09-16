from __future__ import annotations

from pathlib import Path

from evolver.domain import Plan, Step, Verification
from evolver.runner import Runner


class FakeModel:
    def create_plan(self, objective: str, repository_summary: str) -> Plan:
        return Plan(
            objective=objective,
            steps=(
                Step(
                    id="print-hello",
                    instruction="Print Hello, world!",
                    verification=Verification(kind="stdout_equals", expected="Hello, world!"),
                ),
            ),
        )

    def propose_command(self, step: Step, repository_summary: str) -> list[str]:
        return ["printf", "Hello, world!\n"]


def make_runner(tmp_path: Path) -> Runner:
    (tmp_path / "objective.md").write_text(
        "Run a command that prints exactly: Hello, world!\n", encoding="utf-8"
    )
    return Runner(tmp_path, FakeModel())


def test_preview_persists_plan_but_does_not_execute(tmp_path: Path) -> None:
    runner = make_runner(tmp_path)
    argv, verified = runner.run_next(execute=False)

    assert argv == ["printf", "Hello, world!\n"]
    assert verified is None
    assert runner.plan_path.exists()
    assert runner.proposal_path.exists()
    assert not runner.runs_path.exists()


def test_execute_reuses_the_persisted_proposal(tmp_path: Path) -> None:
    runner = make_runner(tmp_path)
    preview_argv, _ = runner.run_next(execute=False)
    execute_argv, verified = runner.run_next(execute=True)

    assert execute_argv == preview_argv
    assert verified is True


def test_execute_records_evidence_and_reconciles_after_restart(tmp_path: Path) -> None:
    runner = make_runner(tmp_path)
    _, verified = runner.run_next(execute=True)

    assert verified is True
    restarted = Runner(tmp_path, FakeModel())
    plan = restarted.load_or_create_plan()
    statuses = restarted.reconcile(plan)
    assert statuses[0].complete is True
    assert restarted.next_step(plan) is None


def test_changed_objective_requires_review(tmp_path: Path) -> None:
    runner = make_runner(tmp_path)
    runner.load_or_create_plan()
    (tmp_path / "objective.md").write_text("A different objective\n", encoding="utf-8")

    try:
        runner.load_or_create_plan()
    except RuntimeError as error:
        assert "objective.md changed" in str(error)
    else:
        raise AssertionError("Expected changed objective to require review")
