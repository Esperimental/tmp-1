# Evolver: project direction

## Purpose

Evolver is an experiment in building an increasingly capable autonomous software
engineering system from a small set of rules. It is inspired by systems such as
Conway's Game of Life: simple local rules should be able to produce useful,
complex behaviour without us designing the final organisation in advance.

The long-term objective is a system capable of building complete applications,
improving how it plans and performs work, creating specialist roles when they
demonstrably help, and proposing tested descendants of its own implementation.

This is not an attempt to make a language model rewrite itself continuously and
hope for improvement. Changes must be evaluated against observable evidence.

## Core evolutionary rule

Every proposed improvement creates a descendant. A descendant earns promotion
only by showing that it is better than its parent without losing required
behaviour.

Initially, people review and promote changes. Automated promotion may be
considered only after the evaluation process itself has proved reliable.

## Stable principles

These principles should change rarely and deliberately:

1. Reality outranks claims. Repository state, command results, tests and evals
   outrank an agent's description of what it believes happened.
2. Work must be restartable. After interruption, compare the objective, saved
   instructions and current environment before deciding what remains.
3. Prefer bounded changes. Break large objectives into steps with observable
   completion conditions.
4. Separate creation from judgement. Planning, implementation, review and
   evaluation are distinct responsibilities, even when one model performs them.
5. Preserve evidence. Record objectives, plans, actions, outputs, evaluations,
   costs and lineage so outcomes can be examined later.
6. Promotion requires comparison. Passing tests means a candidate is not known
   to be broken; it does not by itself mean the candidate is better.
7. Complexity must justify itself. New agents, personas, tools and stages should
   solve observed problems or measurably improve results.
8. Failed experiments are information. Preserve useful failure evidence without
   promoting the failed descendant.
9. Budgets and stopping conditions are part of correctness. A looping or
   uneconomical agent is not successful.
10. Evolution occurs in isolated descendants. The active parent is not modified
    in place and remains recoverable.

## Intended work cycle

The starting organisational seed is intentionally modest:

1. **Reconcile** — inspect the objective, prior instructions, evidence and actual
   repository state.
2. **Plan and architect** — divide the objective into bounded steps and define
   how their completion can be observed.
3. **Work** — make one controlled change using available tools.
4. **Review** — independently examine the change for mistakes, shortcuts,
   regressions and architectural damage.
5. **Evaluate** — run deterministic tests and task-specific qualitative evals.
6. **Compare** — decide whether the descendant is better than its parent.
7. **Record** — preserve the decision and evidence, then stop or begin another
   explicitly authorised generation.

Planning and team structure may evolve, but the system should not add ceremony
merely to resemble a human organisation.

## Current experiment

Version 0.1 proves only the smallest vertical slice:

```text
objective -> generated plan -> reconciliation -> generated command
          -> execution -> verification -> persistent evidence
```

Current behaviour:

- Reads the human objective from `objective.md`.
- Uses `gpt-5.6-luna` to generate a structured plan.
- Selects the first incomplete step.
- Uses Luna to propose one direct process invocation as an argv array.
- Persists the proposal before execution so preview and execution cannot drift.
- Executes one command without shell interpolation and with a timeout.
- Gives generated commands a bounded repository manifest rather than silently
  supplying all source contents; the agent must inspect relevant files when it
  needs their contents.
- Gives generated commands a minimal allowlisted environment that excludes API
  keys, GitHub tokens and other parent-process credentials.
- Verifies exact stdout or exact file content.
- Records the command, output, exit code and verification result under
  `.evolver/`.
- Reconciles that evidence after restart.
- Runs deterministic unit tests and a real model-driven experiment on every
  push to `main`.

This is evidence that the basic loop works, not evidence that Evolver can yet
build software autonomously.

## Current state files

| Path | Meaning |
| --- | --- |
| `objective.md` | Current human-provided objective |
| `.evolver/plan.json` | Generated instructions and verification criteria |
| `.evolver/proposal.json` | Exact command proposed for the current step |
| `.evolver/runs.jsonl` | Append-only execution and verification evidence |

Generated state is intentionally readable and versionable. Secrets must never
be stored in these files.

## Capability evidence

This table is the working capability map, not a claim that the system is ready
for general software engineering. A capability moves to **proven** only when a
model-driven task has passed its objective gate and evaluation policy. Passing
one narrow benchmark proves only that bounded case; it does not establish a
general ability.

| Capability | Status | Evidence or next proof |
| --- | --- | --- |
| One-command execution and exact verification | Proven, narrow | Four isolated simple tasks passed: output, arguments, file creation and file inspection. |
| Restartable state and persisted proposals | Proven, narrow | Deterministic tests cover preview, execution and reconciliation after restart. |
| Small local code repair | Proven, narrow | One broken-inventory repair task passed with protected tests and local acceptance checks. |
| Targeted repository inspection | Evaluating | The agent now receives a file manifest instead of source contents. The targeted-inventory-repair benchmark requires it to inspect relevant evidence. |
| Narrow changes that preserve unrelated code | Evaluating | Targeted-inventory-repair protects its tests and unrelated formatting module. |
| Diagnose failures and choose proportionate tests | Planned | Add a small realistic task where test output alone is insufficient and the agent must inspect code before selecting focused verification. |
| Recover from an incorrect first attempt | Planned | Add a bounded task with a plausible but wrong first diagnosis; evaluate evidence-driven revision rather than a prescribed recovery command. |
| Small multi-file feature work | Planned | Add a compact feature spanning a boundary such as CLI/API, domain logic and tests. |
| Git-aware application work | Planned | Work in an isolated repository copy: inspect status/diff, preserve unrelated changes, make a focused commit after acceptance passes. |
| Build and repair moderate applications | Planned | Complex, held-out tasks: unfamiliar but bounded applications with realistic requirements, regressions and acceptance tests. |
| Independent change review | Planned | Seed flawed diffs and demonstrate that a reviewer identifies defects the implementer missed. |
| Compare candidate descendants | Planned | Run parent and candidate on held-out tasks; compare success, regressions, cost and reliability. |
| Propose changes to Evolver itself | Deferred | Only after the preceding capabilities are evidenced; use isolated descendants and human promotion. |

When a mid-range or complex task reveals a specific weakness, add the smallest
useful simple task that isolates it. Iterate on that AI-unit test cheaply, then
rerun the matching higher-level task to check whether the improvement transfers.

## Near-term progression

Each stage should be implemented and evaluated before moving to the next:

1. Improve structured model responses and validation without adding a large
   agent framework.
2. Reconcile file and repository state rather than relying primarily on prior
   run records.
3. Support small multi-step objectives with dependency and stopping rules.
4. Add a distinct review pass and demonstrate that it catches seeded defects.
5. Add parent-versus-candidate evaluation in isolated Git worktrees.
6. Record token usage, monetary cost, duration and failure categories.
7. Try competing descendants and preserve more than one promising lineage.
8. Allow controlled evolution of prompts, tools and organisational roles.
9. Allow proposed changes to non-critical parts of Evolver itself, with human
    promotion after tests and evals.

The order can change when experiments provide evidence for a better sequence.

## Evaluation direction

Evaluation will eventually have multiple layers:

- build, lint and deterministic tests;
- objective-specific acceptance checks;
- regression and security checks;
- cost and performance budgets;
- qualitative review by one or more models;
- hidden or independently generated evals;
- direct parent-versus-descendant trials;
- human review while promotion remains experimental.

The objective gate, trajectory diagnostics, loop detection and report contract
are defined in [`EVALUATION.md`](EVALUATION.md).

Evaluation criteria must not be freely rewritten by the same candidate being
evaluated. The evolutionary system can propose improved evals, but those changes
must themselves be reviewed and tested.

## Explicit non-goals for the current stage

- Unattended continuous mutation.
- Automatic merging or promotion.
- A large fixed panel of personas.
- Building a web UI before the underlying loop needs one.
- Treating more files, agents or model calls as evidence of progress.
- Claiming that modifying orchestration code makes the underlying model itself
  more intelligent.

## Success at this stage

The current stage succeeds when an observer can see that:

1. a real model interpreted the objective;
2. it produced a bounded plan and command;
3. the exact persisted command ran;
4. an external verifier checked the result;
5. the result remained understood after restart; and
6. tests and evidence make failures visible rather than concealing them.

The next stage should be chosen from an observed limitation of this loop, not
from a desire to make the architecture look sophisticated.
