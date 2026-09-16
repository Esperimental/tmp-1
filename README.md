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

Preview the next action without executing it:

```bash
evolver run
```

After reviewing the proposed argv, explicitly permit one command:

```bash
evolver run --execute
```

Inspect reconciled state at any time, including after an interrupted run:

```bash
evolver status
```

Persistent state is stored under `.evolver/`. Do not put credentials in the
objective or generated state.
