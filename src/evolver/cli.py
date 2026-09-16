from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import OpenAIModel
from .runner import Runner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evolver")
    subcommands = parser.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run", help="Propose or execute one incomplete step")
    run.add_argument("--execute", action="store_true", help="Execute the proposed argv")
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
    argv, verified = runner.run_next(execute=args.execute)
    print("Proposed argv: " + json.dumps(argv))
    if verified is None:
        print("Not executed. Review it, then rerun with --execute.")
    else:
        print("Verification: " + ("passed" if verified else "failed"))


if __name__ == "__main__":
    main()
