# Evolver experiment

[![Tests](https://github.com/Esperimental/tmp-1/actions/workflows/tests.yml/badge.svg)](https://github.com/Esperimental/tmp-1/actions/workflows/tests.yml)

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

## Live GitHub experiment

The `Live agent` workflow makes real API calls using `gpt-5.6-luna`, executes
the generated command, verifies it, checks restart reconciliation, and uploads
the `.evolver` evidence. It requires an Actions repository secret named
`OPENAI_API_KEY` and is started manually from the Actions tab.
