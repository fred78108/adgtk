# AgentWriter

`AgentWriter` is ADGTK's runtime metric writer for agentic test runs. It plays the same role as TensorBoard's `SummaryWriter` — a single object you hold across a run, call at each step, and flush to disk at the end.

Where `MeasurementEngine` evaluates a *dataset* after the fact, `AgentWriter` records *what happened while the agent ran*: latency per step, token consumption, tool calls, and final outcome. The output is a set of CSVs in the run's `metrics/` folder, compatible with the same analysis tools you use for any other ADGTK experiment.

---

## Lifecycle

```
AgentWriter(folders)
    ↓
log_step()          ← called once per agent step
log_tool_call()     ← called once per tool invocation (optional)
    ↓
log_outcome()       ← called at task completion
    ↓
save()              ← writes CSVs to folders.metrics
```

---

## Import

```python
from adgtk.measurements import AgentWriter, track_step
```

---

## Initialisation

```python
writer = AgentWriter(folders)                  # name defaults to "agent"
writer = AgentWriter(folders, name="planner")  # use a distinct name when running
                                               # multiple writers in one experiment
```

`folders` is the `ExperimentRunFolders` passed to `run_scenario`. CSV files are named `{name}.{label}.csv` inside `folders.metrics/`.

---

## `log_step`

Call once per step. All parameters are optional — omitted values produce no entry for that step (series are sparse, not zero-padded).

```python
writer.log_step(
    latency=elapsed,        # float — wall-clock seconds
    tokens_in=450,          # int   — input tokens to the model
    tokens_out=120,         # int   — output tokens from the model
    error=False,            # bool  — True if step raised an exception
)
```

---

## `log_tool_call`

Call once per tool invocation. Creates a per-tool CSV (`agent.tool.search.csv`) tracking success rate alongside the aggregate `agent.tool_call_count.csv`.

```python
writer.log_tool_call("search", success=True)
writer.log_tool_call("lookup", success=False)
```

---

## `log_outcome`

Call once at the end of a task attempt. For retry scenarios, call it again after each attempt — `retry_count` increments automatically.

```python
writer.log_outcome(
    success=True,
    goal_completion=0.9,    # float 0–1, partial credit (default 1.0)
    optimal_steps=3,        # int, known oracle step count — enables path_efficiency
)
```

`first_attempt_success` is recorded from the *first* call only, regardless of how many times `log_outcome` is subsequently called.

---

## `save`

Persists all metrics to `folders.metrics/`. Call once at the end of `run_scenario`.

```python
writer.save()
```

---

## Built-in metrics

| CSV file | Logged by | Description |
|---|---|---|
| `{name}.latency.csv` | `log_step` | Wall-clock seconds per step |
| `{name}.tokens_in.csv` | `log_step` | Input tokens per step |
| `{name}.tokens_out.csv` | `log_step` | Output tokens per step |
| `{name}.error.csv` | `log_step` | 1.0 if step errored, 0.0 otherwise |
| `{name}.tool_call_count.csv` | `log_tool_call` | 1.0 per invocation (sum = total) |
| `{name}.tool.{name}.csv` | `log_tool_call` | Per-tool: 1.0 success, 0.0 failure |
| `{name}.success.csv` | `log_outcome` | 1.0 = pass, 0.0 = fail |
| `{name}.goal_completion.csv` | `log_outcome` | Partial-credit score 0–1 |
| `{name}.retry_count.csv` | `log_outcome` | Failed attempts before this call |
| `{name}.path_efficiency.csv` | `log_outcome` | min(optimal / actual steps, 1.0) |
| `{name}.first_attempt_success.csv` | `log_outcome` (first call only) | 1.0 if first attempt succeeded |

---

## Full example inside `run_scenario`

```python
import time
from adgtk.factory import SupportsFactory
from adgtk.experiment.result import RunResultBuilder
from adgtk.tracking.structure import ExperimentRunFolders
from adgtk.measurements import AgentWriter
from adgtk.tracking import ObservationWriter

class MyAgentScenario(SupportsFactory):
    factory_id = "my.agent.scenario"
    group = "scenario"
    summary = "Test my tool-using agent"
    interview_blueprint = []
    factory_can_init = True

    def run_scenario(self, result_folders: ExperimentRunFolders):
        result = RunResultBuilder()
        writer = AgentWriter(result_folders)
        obs = ObservationWriter("agent")

        task = "Summarise the Q3 earnings report."
        max_steps = 10
        step = 0

        while step < max_steps:
            step_start = time.monotonic()

            # --- call the agent ---
            response = self.agent.step(task)
            elapsed = time.monotonic() - step_start

            writer.log_step(
                latency=elapsed,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
            )

            obs.agent_turn(
                prompt=response.prompt,
                response=response.text,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                latency_ms=elapsed * 1000,
            )

            # --- record any tool calls the agent made ---
            for call in response.tool_calls:
                writer.log_tool_call(call.name, success=call.ok)

            if response.done:
                break
            step += 1

        success = response.task_completed
        writer.log_outcome(
            success=success,
            goal_completion=response.completion_score,
            optimal_steps=3,
        )
        writer.save()

        summary = writer.summary()
        result.set("avg_latency", summary.get("latency", 0))
        result.set("total_tokens_out", sum(writer._tracker.get_all_data("tokens_out")))
        result.set("tool_calls", summary.get("tool_call_count", 0))
        result.tag("model", self.agent.model)

        if success:
            result.mark_pass()
        else:
            result.mark_fail("task not completed")

        result.summarize(f"Completed in {step + 1} steps")
        return result.finalize()
```

---

## `track_step` decorator

Use `track_step` to automatically capture latency and errors on any step method, without adding timing boilerplate everywhere.

```python
from adgtk.measurements import AgentWriter, track_step

writer = AgentWriter(result_folders)

@track_step(writer)
def run_agent_step(prompt: str) -> str:
    return call_llm(prompt)

# Exceptions are logged as errors and re-raised:
@track_step(writer, log_errors=True)   # default
def risky_step(prompt: str) -> str:
    ...

# Measure latency only, don't flag exceptions as errors:
@track_step(writer, log_errors=False)
def best_effort_step(prompt: str) -> str:
    ...
```

`track_step` records latency and error flag via `log_step` in the `finally` block, so latency is always captured even when the wrapped function raises.

---

## Introspection

```python
writer.step_count()          # int — steps logged so far
writer.tool_distribution()   # dict[str, int] — per-tool call counts
writer.summary()             # dict — latest value for each metric + tool stats
```

---

## Retry scenario

```python
for attempt in range(max_attempts):
    try:
        # run agent steps ...
        writer.log_outcome(success=True, goal_completion=score)
        break
    except AgentFailure:
        writer.log_outcome(success=False, goal_completion=0.0)

writer.save()
# retry_count in the CSV will reflect the number of failed attempts
```

---

## Using multiple writers

Pass a distinct `name` when you have multiple agents or sub-tasks in one run:

```python
planner  = AgentWriter(result_folders, name="planner")
executor = AgentWriter(result_folders, name="executor")

# produces planner.latency.csv, executor.latency.csv, etc.
```
