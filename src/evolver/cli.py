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
    return parser


def main() -> None:
    args = _parser().parse_args()
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
