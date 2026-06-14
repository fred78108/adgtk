# Batch Jobs

A **batch job** is a YAML file that defines a set of experiments to run in sequence. Batch jobs are stored in the `batches/` directory and run with `adgtk-batch run`.

---

## Repeat runs without a batch file

To run the **same** experiment multiple times you do not need a batch file. Use `--n` on `adgtk run`:

```bash
adgtk run my-experiment --n 20    # run my-experiment 20 times in sequence
adgtk run --n 10                  # interactive selection, then 10 runs
```

Each run is numbered independently and its results are written to `results/{run_id}/` exactly as they would be for a single run.

---

## When to use batch jobs

Use batch jobs when you want to:

- Run **different** experiments back-to-back unattended (e.g. overnight)
- Define a standard nightly evaluation suite that spans multiple experiment definitions
- Sweep over a set of pre-built experiment definitions

Each item in a batch is a reference to an existing experiment definition in `blueprints/`.

---

## Batch YAML format

```yaml
name: nightly-suite
description: "Nightly evaluation of all prompt variants"
jobs:
  - experiment: baseline
  - experiment: exp.cot
  - experiment: exp.zero-shot
  - experiment: exp.few-shot
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Batch name — used in logging and display |
| `description` | Free-text description |
| `jobs` | List of job entries |
| `jobs[].experiment` | Name of the experiment definition in `blueprints/` |

---

## Running a batch

```bash
adgtk-batch list              # See available batch definitions
adgtk-batch run nightly-suite # Run a batch
```

Each experiment in the batch runs in sequence. Results are written independently to `results/{run_id}/` just as they would be for a single `adgtk run`. The batch run itself is not represented as a single result entry.

---

## Batch log

Every batch run writes a dedicated log to `logs/runs/{batch_name}/batch.log`. It records:

- Batch start time and total job count
- Per-experiment: start time, outcome (`complete` or `error`), and duration
- A one-line summary at completion: total elapsed time, pass count, and fail count

This gives you a single file to review after an unattended run without inspecting individual experiment logs.

The log appears on the **Logs** page of the web interface under **runs/{batch_name}**.

---

## Tips

- **Build experiment definitions first** with `adgtk build` before referencing them in a batch.
- **Use meaningful experiment names** — the batch log references them by name.
- **Check results after** with `adgtk-results list` to see all the runs that were produced.
