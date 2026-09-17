from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import OpenAIModel
from .runner import Runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evolver")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run", help="Execute one incomplete step")
    run.add_argument("--preview", action="store_true", help="Persist and show argv without executing")
    subcommands.add_parser("status", help="Reconcile the saved plan with current state")
    evaluation = subcommands.add_parser("eval", help="Run one task, one phase, or all tasks")
    evaluation_commands = evaluation.add_subparsers(dest="eval_command", required=True)
    task = evaluation_commands.add_parser("task", help="Run one isolated task")
    task.add_argument("path", type=Path)
    phase = evaluation_commands.add_parser("phase", help="Run one evaluation phase")
    phase.add_argument("name")
    phase.add_argument("--evals-root", type=Path, default=Path("evals"))
    all_tasks = evaluation_commands.add_parser("all", help="Run every implemented task")
    all_tasks.add_argument("--evals-root", type=Path, default=Path("evals"))
    for command in (task, phase, all_tasks):
        command.add_argument(
            "--output-dir", type=Path, default=Path(".evolver/evaluations")
        )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "eval":
        from .harness import TaskDefinition, discover_tasks, run_tasks

        if args.eval_command == "task":
            definitions = [TaskDefinition.load(args.path)]
        elif args.eval_command == "phase":
            definitions = discover_tasks(args.evals_root, args.name)
        else:
            definitions = discover_tasks(args.evals_root)
        if not definitions:
            raise SystemExit("No matching evaluation tasks found")
        suite = run_tasks(definitions, args.output_dir.resolve())
        print(suite.to_markdown())
        if not suite.passes:
            raise SystemExit(1)
        return
    runner = Runner(Path.cwd(), OpenAIModel())
    if args.command == "status":
        plan = runner.load_or_create_plan()
        for status in runner.reconcile(plan):
            marker = "complete" if status.complete else "incomplete"
            print(f"{status.step.id}: {marker} - {status.evidence}")
        return
    print("Model: " + runner.model.model_name)
    argv, verified = runner.run_next(execute=not args.preview)
    print("Proposed argv: " + json.dumps(argv))
    if verified is None:
        print("Not executed. The exact proposal is persisted for the next run.")
    else:
        print("Verification: " + ("passed" if verified else "failed"))


if __name__ == "__main__":
    main()
