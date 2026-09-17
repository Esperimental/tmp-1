from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluation import DIMENSIONS, EvaluationPolicy, EvaluationSuiteReport, Finding, TaskEvaluation
from .evaluator import OpenAIEvaluator, build_task_packet
from .model import AgentModel, OpenAIModel
from .runner import Runner


@dataclass(frozen=True)
class TaskSource:
    clone_url: str
    revision: str


@dataclass(frozen=True)
class TaskDefinition:
    directory: Path
    task_id: str
    phase: str
    max_commands: int
    acceptance_argv: tuple[str, ...] = ()
    acceptance_script: str | None = None
    protected_paths: tuple[str, ...] = ()
    source: TaskSource | None = None

    @classmethod
    def load(cls, directory: Path) -> "TaskDefinition":
        directory = directory.resolve()
        value = json.loads((directory / "task.json").read_text(encoding="utf-8"))
        acceptance = value.get("acceptance", {})
        task_id = str(value["id"])
        phase = str(value["phase"])
        max_commands = int(value["max_commands"])
        protected_paths = tuple(str(item) for item in value.get("protected_paths", []))
        acceptance_argv = tuple(str(item) for item in acceptance.get("argv", []))
        acceptance_script = acceptance.get("script")
        if acceptance_script is not None:
            if not isinstance(acceptance_script, str):
                raise ValueError("Acceptance script must be a path string")
            script_path = Path(acceptance_script)
            if script_path.is_absolute() or ".." in script_path.parts:
                raise ValueError("Acceptance script must stay inside the task directory")
            if not (directory / script_path).is_file():
                raise ValueError("Acceptance script does not exist")
        if acceptance_argv and acceptance_script:
            raise ValueError("Use either an acceptance command or script, not both")
        source_value = value.get("source")
        source = None
        if source_value is not None:
            if not isinstance(source_value, dict):
                raise ValueError("Source must be an object")
            clone_url = str(source_value.get("clone_url", ""))
            revision = str(source_value.get("revision", ""))
            if not clone_url or not re.fullmatch(r"[0-9a-f]{7,64}", revision):
                raise ValueError("Source requires a clone URL and pinned hexadecimal revision")
            source = TaskSource(clone_url, revision)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", task_id):
            raise ValueError("Task id must be a lowercase hyphenated identifier")
        if not re.fullmatch(r"[a-z][a-z-]*", phase):
            raise ValueError("Phase must be a lowercase hyphenated identifier")
        if max_commands < 1:
            raise ValueError("max_commands must be at least one")
        if any(Path(path).is_absolute() or ".." in Path(path).parts for path in protected_paths):
            raise ValueError("Protected paths must stay inside the task workspace")
        return cls(
            directory=directory,
            task_id=task_id,
            phase=phase,
            max_commands=max_commands,
            acceptance_argv=acceptance_argv,
            acceptance_script=acceptance_script,
            protected_paths=protected_paths,
            source=source,
        )


def discover_tasks(evals_root: Path, phase: str | None = None) -> list[TaskDefinition]:
    definitions = [TaskDefinition.load(path.parent) for path in evals_root.rglob("task.json")]
    return sorted(
        (item for item in definitions if phase is None or item.phase == phase),
        key=lambda item: (item.phase, item.task_id),
    )


def _snapshot(workspace: Path, paths: tuple[str, ...]) -> dict[str, bytes | None]:
    snapshot: dict[str, bytes | None] = {}
    for path in paths:
        candidate = workspace / path
        if candidate.is_dir():
            snapshot.update(
                {
                    str(child.relative_to(workspace)): child.read_bytes()
                    for child in candidate.rglob("*")
                    if child.is_file()
                    and "__pycache__" not in child.parts
                    and child.suffix != ".pyc"
                }
            )
        else:
            snapshot[path] = candidate.read_bytes() if candidate.is_file() else None
    return snapshot


def _acceptance(
    definition: TaskDefinition, workspace: Path, runner: Runner, before: dict[str, bytes | None]
) -> tuple[str, dict[str, Any]]:
    runs = (
        runner.runs_path.read_text(encoding="utf-8").splitlines()
        if runner.runs_path.exists()
        else []
    )
    after = _snapshot(workspace, definition.protected_paths)
    protected_changes = [
        path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)
    ]
    if definition.acceptance_argv or definition.acceptance_script:
        argv = (
            list(definition.acceptance_argv)
            if definition.acceptance_argv
            else [sys.executable, str(definition.directory / str(definition.acceptance_script)), str(workspace)]
        )
        try:
            result = subprocess.run(
                argv,
                cwd=workspace,
                env=runner.command_environment(),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            accepted = result.returncode == 0
            evidence: dict[str, Any] = {
                "argv": argv,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "protected_changes": protected_changes,
            }
        except subprocess.TimeoutExpired as error:
            accepted = False
            evidence = {
                "argv": argv,
                "exit_code": None,
                "stdout": error.stdout or "",
                "stderr": error.stderr or "",
                "timeout": True,
                "protected_changes": protected_changes,
            }
    else:
        records = [json.loads(line) for line in runs if line.strip()]
        plan = runner.load_or_create_plan()
        completed = runner.next_step(plan) is None
        accepted = (
            bool(records)
            and len(records) <= definition.max_commands
            and all(record.get("verified") is True for record in records)
            and completed
        )
        evidence = {"recorded_verifications_passed": accepted, "protected_changes": protected_changes}
    if protected_changes:
        accepted = False
    return ("pass" if accepted else "fail"), evidence


def run_task(
    definition: TaskDefinition,
    output_dir: Path,
    model: AgentModel | None = None,
    evaluator: OpenAIEvaluator | None = None,
) -> TaskEvaluation:
    with tempfile.TemporaryDirectory(prefix=f"evolver-{definition.task_id}-") as temporary:
        workspace = Path(temporary)
        source_evidence: dict[str, str] = {}
        if definition.source:
            subprocess.run(
                ["git", "clone", "--quiet", definition.source.clone_url, str(workspace)],
                check=True,
            )
            subprocess.run(
                ["git", "checkout", "--quiet", "--detach", definition.source.revision],
                cwd=workspace,
                check=True,
            )
            actual_revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=workspace, text=True
            ).strip()
            if actual_revision != definition.source.revision:
                raise RuntimeError("Checked-out source does not match the pinned revision")
            source_evidence = {
                "clone_url": definition.source.clone_url,
                "expected_revision": definition.source.revision,
                "actual_revision": actual_revision,
            }
            shutil.copy2(definition.directory / "objective.md", workspace / "objective.md")
        else:
            shutil.copytree(
                definition.directory,
                workspace,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("task.json", "README.md"),
            )
        runner = Runner(workspace, model or OpenAIModel())
        before = _snapshot(workspace, definition.protected_paths)
        for _ in range(definition.max_commands):
            plan = runner.load_or_create_plan()
            if runner.next_step(plan) is None:
                break
            runner.run_next(execute=True)
        gate, gate_evidence = _acceptance(definition, workspace, runner, before)
        if source_evidence:
            gate_evidence["source"] = source_evidence
        packet = build_task_packet(workspace, definition.task_id, gate, gate_evidence)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{definition.task_id}.evidence.json").write_text(
            json.dumps(packet, indent=2) + "\n", encoding="utf-8"
        )
        evaluation = (evaluator or OpenAIEvaluator()).evaluate(packet)
        (output_dir / f"{definition.task_id}.json").write_text(
            json.dumps(evaluation.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        return evaluation


def _task_error(definition: TaskDefinition, output_dir: Path, error: Exception) -> TaskEvaluation:
    evaluation = TaskEvaluation(
        task_id=definition.task_id,
        gate_result="error",
        scores={name: 0.0 for name in DIMENSIONS},
        findings=(
            Finding(
                severity="critical",
                area="execution",
                evidence=(type(error).__name__,),
                description=str(error),
                recommendation="Inspect the recorded task error and correct the harness or model protocol.",
                confidence=1.0,
            ),
        ),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{definition.task_id}.json").write_text(
        json.dumps(evaluation.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return evaluation


def run_tasks(
    definitions: list[TaskDefinition], output_dir: Path, *, jobs: int = 1
) -> EvaluationSuiteReport:
    if jobs < 1:
        raise ValueError("jobs must be at least one")

    output_dir.mkdir(parents=True, exist_ok=True)
    evaluations: dict[str, TaskEvaluation] = {}
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(run_task, definition, output_dir): definition for definition in definitions
        }
        for future in as_completed(futures):
            definition = futures[future]
            try:
                evaluations[definition.task_id] = future.result()
            except Exception as error:
                evaluations[definition.task_id] = _task_error(definition, output_dir, error)
    ordered_evaluations = tuple(evaluations[definition.task_id] for definition in definitions)
    suite = EvaluationSuiteReport(ordered_evaluations, EvaluationPolicy())
    (output_dir / "report.md").write_text(suite.to_markdown(), encoding="utf-8")
    return suite
