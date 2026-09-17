# Evolver experiment

[![Tests](https://github.com/Esperimental/tmp-1/actions/workflows/tests.yml/badge.svg)](https://github.com/Esperimental/tmp-1/actions/workflows/tests.yml)

The project vision, stable principles, current scope and evolutionary roadmap
are maintained in [`docs/PROJECT.md`](docs/PROJECT.md).
The evaluation and diagnostic contract is in
[`docs/EVALUATION.md`](docs/EVALUATION.md).

This is the smallest useful experiment for a restartable coding agent. It reads
an objective, asks a model for a structured plan, compares that plan with prior
verified runs, proposes one command, and optionally executes and verifies it.

The repository state and recorded command results outrank the model's claims.
The agent does not commit, push, mutate itself, or run continuously.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export OPENAI_API_KEY='set-this-in-your-shell-not-in-the-repository'
```

Optionally select a model with `EVOLVER_MODEL`.

## First run

Run the next action, including a real model call and command execution:

```bash
evolver run
```

To persist and inspect the proposed argv without executing it:

```bash
evolver run --preview
```

The next normal run executes that exact persisted proposal rather than asking
the model to generate it again.

Inspect reconciled state at any time, including after an interrupted run:

```bash
evolver status
```

Persistent state is stored under `.evolver/`. Do not put credentials in the
objective or generated state.

## Live GitHub evaluation

Every push runs traditional tests first. If they pass, the simple AI phase uses
`gpt-5.6-luna` for four isolated one-command tasks: exact output, argument handling,
file creation and file inspection. An independent Luna evaluator scores every task,
then the harness publishes a combined capability report and evidence artifact.

The first mid-range task is a local broken inventory module. It exercises a bounded
multi-command repair loop, deterministic acceptance tests and protected test files.
The complex phase remains a disabled placeholder. The workflow requires an Actions
repository secret named `OPENAI_API_KEY`.

Any task or phase can be run independently while diagnosing a weakness:

```bash
evolver eval task evals/mid-range/local-inventory-repair
evolver eval phase simple
evolver eval phase mid-range
evolver eval all
```
