from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .domain import Plan, Step
from .model import AgentModel


@dataclass(frozen=True)
class StepStatus:
    step: Step
    complete: bool
    evidence: str


class Runner:
    def __init__(self, root: Path, model: AgentModel) -> None:
        self.root = root.resolve()
        self.model = model
        self.state_dir = self.root / ".evolver"
        self.plan_path = self.state_dir / "plan.json"
        self.runs_path = self.state_dir / "runs.jsonl"

    def repository_summary(self) -> str:
        paths = sorted(
            str(path.relative_to(self.root))
            for path in self.root.rglob("*")
            if path.is_file() and ".git" not in path.parts and ".venv" not in path.parts
        )
        return "Files:\n" + "\n".join(paths[:200])

    def load_or_create_plan(self) -> Plan:
        objective = (self.root / "objective.md").read_text(encoding="utf-8").strip()
        if self.plan_path.exists():
            plan = Plan.from_dict(json.loads(self.plan_path.read_text(encoding="utf-8")))
            if plan.objective != objective:
                raise RuntimeError("objective.md changed; remove .evolver/plan.json after review")
            return plan
        plan = self.model.create_plan(objective, self.repository_summary())
        self.state_dir.mkdir(exist_ok=True)
        self.plan_path.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")
        return plan

    def _successful_run(self, step_id: str) -> bool:
        if not self.runs_path.exists():
            return False
        for line in self.runs_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("step_id") == step_id and record.get("verified") is True:
                return True
        return False

    def status(self, step: Step) -> StepStatus:
        verification = step.verification
        if verification.kind == "file_content_equals":
            candidate = (self.root / str(verification.path)).resolve()
            if self.root not in candidate.parents:
                return StepStatus(step, False, "verification path escapes repository")
            if candidate.exists() and candidate.read_text(encoding="utf-8") == verification.expected:
                return StepStatus(step, True, f"{verification.path} has expected content")
            return StepStatus(step, False, f"{verification.path} is absent or differs")
        complete = self._successful_run(step.id)
        return StepStatus(step, complete, "verified run recorded" if complete else "no verified run")

    def reconcile(self, plan: Plan) -> list[StepStatus]:
        return [self.status(step) for step in plan.steps]

    def next_step(self, plan: Plan) -> Step | None:
        return next((status.step for status in self.reconcile(plan) if not status.complete), None)

    def run_next(self, execute: bool, timeout_seconds: int = 30) -> tuple[list[str], bool | None]:
        plan = self.load_or_create_plan()
        step = self.next_step(plan)
        if step is None:
            raise RuntimeError("All plan steps are already complete")
        argv = self.model.propose_command(step, self.repository_summary())
        if not execute:
            return argv, None
        started = datetime.now(timezone.utc).isoformat()
        try:
            result = subprocess.run(
                argv,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout or ""
            stderr = error.stderr or ""
            exit_code = None
        if step.verification.kind == "stdout_equals":
            verified = exit_code == 0 and stdout.rstrip("\n") == step.verification.expected.rstrip("\n")
        else:
            verified = exit_code == 0 and self.status(step).complete
        record = {
            "started_at": started,
            "step_id": step.id,
            "argv": argv,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "verified": verified,
        }
        self.state_dir.mkdir(exist_ok=True)
        with self.runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return argv, verified
