# Evaluation contract

Evolver evaluates two different things:

1. **The candidate result** — whether the target software satisfies its
   requirements without regression.
2. **The agent trajectory** — whether Evolver reached that result reliably,
   economically and coherently.

These must remain separate. An efficient attempt that produces incorrect
software fails. An inefficient attempt that produces correct software may pass
the candidate gate while receiving diagnostic findings that guide improvement.

## Objective promotion gate

The promotion gate is determined by externally observed evidence, not an LLM's
opinion. For the repository-repair milestone it includes:

- target repository started from the expected commit;
- visible tests pass;
- hidden acceptance tests pass;
- benchmark and hidden tests were not modified;
- prohibited paths were not modified;
- commands completed within time and resource limits;
- final diff can be applied cleanly to the original target;
- no required behaviour was removed merely to make tests pass.

Possible gate results are:

- `pass`
- `fail`
- `error`
- `budget_exhausted`
- `benchmark_invalid`

Qualitative review may explain a gate result but cannot change an objective
failure into a pass.

## Fail-fast evaluation phases

Task runs are isolated, so a suite may execute independent tasks concurrently with a bounded
worker count. For example, `evolver eval all --jobs 5` runs at most five agent/evaluator pairs
at once. Results are still reported in task-definition order and every selected task is allowed
to finish, so a single infrastructure or model failure does not hide other useful evidence.

Use one worker while iterating on an individual task. Raise the limit only within the configured
model rate and cost budget; parallelism reduces elapsed time, not model-token consumption.

## Evaluator calibration

The objective gate proves correctness for the behaviours it covers. The model evaluator measures
trajectory quality and must not turn a passing gate into an unearned high score. We calibrate it
against recorded, labelled examples rather than treating any one score as truth:

| Trajectory | Expected interpretation |
| --- | --- |
| Correct, focused implementation and meaningful checks | Strong: normally 8–10. |
| One avoidable failed action, then a focused correction | Good recovery, but not exceptional efficiency. |
| Repeated unchanged commands or broad speculative rewrites | Material efficiency/implementation deduction. |
| Changed protected tests or missed hidden acceptance behaviour | Deterministic gate failure; evaluator explains the failure, never overrides it. |

The complex inventory run is in the second category: it passed hidden parent-directory creation
and preserved protected files, but its first protection check was invalidated by generated cache
files and required cleanup. An 8-ish efficiency/recovery assessment is defensible; a 9+ efficiency
score would not be. Its passing gate also does not prove untested documented edge cases, so those
belong in hidden acceptance checks rather than being assumed from an evaluator narrative.

The quality pipeline grows in ordered phases:

1. **Traditional tests** validate Evolver itself without paid model calls.
2. **Simple AI tasks** require exactly one command and test isolated capabilities.
3. **Mid-range AI tasks** will require several commands, inspection and basic recovery.
4. **Complex AI tasks** will exercise realistic multi-step workflows, mistakes and recovery.

A phase only runs after the previous phase passes. The first mid-range task is enabled; the
complex job remains a disabled placeholder so its contract can evolve from observed evidence.
All tasks inside an enabled phase receive individual objective gates and scorecards; the phase
passes only when every task satisfies policy.

Tasks are also independently addressable through `evolver eval task <path>`. A developer can
iterate on a single isolated regression without paying to run unrelated model evaluations,
then rely on the ordered CI pipeline to reveal whether the improvement transfers upward.

## Runtime guards

Some failures should be stopped during execution rather than discovered later:

- maximum model calls;
- maximum commands and file mutations;
- maximum elapsed time and estimated API cost;
- timeout for each command;
- captured-output size limit;
- repeated identical action limit;
- repeated test result with no intervening repository change;
- consecutive actions that produce no observable state change;
- attempts to modify protected paths;
- explicit model completion without acceptance evidence.

When a guard stops a run, Evolver records the triggering condition and preserves
the full usable trajectory for evaluation.

## Trajectory metrics

Metrics should be mechanically derived wherever possible:

- total model calls and tokens;
- estimated API cost;
- elapsed time;
- tool calls by type;
- successful and failed commands;
- files read and changed;
- diff size;
- test runs and unique test outcomes;
- repeated actions;
- no-progress actions;
- plan revisions;
- retries after tool errors;
- first step at which the final successful approach appeared;
- work performed after all acceptance checks were already satisfied.

These metrics identify patterns such as loops, premature completion, excessive
repository reading, repeatedly running unchanged tests, broad rewrites for small
bugs, and continuing to work after success.

## Diagnostic review

After deterministic evaluation, a reviewer receives:

- objective and specification;
- initial and final repository summaries;
- plan revisions;
- ordered tool trajectory;
- command outputs and test results;
- final diff;
- objective gate results;
- mechanically derived metrics.

The reviewer returns structured findings. Each finding contains:

- severity: `critical`, `major`, `minor` or `observation`;
- area: planning, inspection, implementation, testing, recovery, efficiency,
  architecture, security or evaluation;
- evidence: specific observable events from the trajectory;
- impact;
- a concrete improvement suggestion;
- confidence.

The review also lists:

- what worked well;
- where the agent became stuck or uncertain;
- unnecessary or repeated work;
- missing tests or assumptions;
- the earliest useful intervention, if one was needed;
- recommended changes to Evolver rather than to the benchmark solution.

Reviewers must not rely on hidden chain-of-thought. Evaluation uses recorded
actions, outputs, diffs and explicit agent messages.

## Initial report shape

Each run should eventually produce both JSON for comparison and Markdown for
people:

```json
{
  "run_id": "...",
  "benchmark": "inventory-repair-v1",
  "candidate_gate": {
    "result": "pass",
    "visible_tests": "9/9",
    "hidden_tests": "5/5"
  },
  "trajectory": {
    "model_calls": 0,
    "tool_calls": 0,
    "repeated_actions": 0,
    "no_progress_actions": 0,
    "elapsed_seconds": 0,
    "estimated_cost_usd": 0
  },
  "findings": [],
  "improvement_priorities": []
}
```

The exact schema may evolve after real trajectories show which information is
useful. Raw evidence should remain available so new evaluators can reassess old
runs.

The implemented scorecard uses seven dimensions: planning, investigation,
implementation, testing, recovery, efficiency and completion. The initial
policy requires an objective gate pass, no critical finding, an overall score of
at least `6.0`, and no individual dimension below `4.0`. Aggregate reports list
every task and expose the strongest and weakest cross-task averages.

## Comparing Evolver versions

One successful run is anecdotal. Versions should eventually be compared across
multiple clean trials and benchmarks using:

- task success rate;
- hidden-test pass rate;
- median cost and duration;
- median tool calls;
- loop and budget-exhaustion frequency;
- regression frequency;
- severity and recurrence of diagnostic findings.

Promotion decisions should consider the distribution of results, not only the
best run. A descendant that occasionally performs brilliantly but frequently
loops or damages unrelated files is not an improvement.
