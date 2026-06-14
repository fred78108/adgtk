# Studies

A **study** is a named collection of experiments whose results you want to compare side-by-side. It answers questions like:

- Which model performed better on this task?
- Did changing the prompt strategy improve accuracy?
- How does the baseline compare to the refined approach?

Where `adgtk report` aggregates runs *within* a single experiment (same blueprint, multiple runs), a study aggregates results *across* different experiments — each with its own blueprint, configuration, and history of runs.

---

## How it works

1. You define a study blueprint in `studies/` — a short YAML file listing which experiments to include.
2. `adgtk-study run` reads every run manifest for each experiment, recalculates statistics, and writes a markdown report and combined CSV to `study-results/`.
3. The output is ready for human review (the markdown) or further analysis in a notebook (the CSV).

The study does not re-run any experiments. It operates entirely on stored results.

---

## Directory layout

```
blueprints/            ← experiment YAML definitions
studies/               ← study YAML definitions
  model-comparison.yaml

results/
  exp-gpt4o/           ← runs for experiment "exp-gpt4o"
    0.exp-gpt4o/
    1.exp-gpt4o/
  exp-claude/          ← runs for experiment "exp-claude"
    0.exp-claude/

study-results/
  model-comparison/
    study_report.md    ← cross-experiment markdown report
    study_results.csv  ← combined CSV, one row per run
```

---

## Step-by-step walkthrough

### 1. Run your experiments

Before creating a study you need at least one completed run for each experiment you want to include. Run them normally:

```bash
adgtk run exp-gpt4o --n 5
adgtk run exp-claude --n 5
```

### 2. Build a study blueprint

```bash
adgtk-study build
```

The wizard asks for a name, an optional description, optional tags, and then lists every experiment with results on disk:

```
============================================================
  Build a Study Blueprint
============================================================
Study name: model-comparison
Description (optional): GPT-4o vs Claude on the extraction task
Tags (comma-separated, optional): extraction

Available experiments (from results/):
    0 : exp-claude
    1 : exp-gpt4o

Enter indices (comma-separated), experiment names, or 'all':
> 0,1

  Study    : model-comparison
  Desc     : GPT-4o vs Claude on the extraction task
  Tags     : extraction
  Experiments:
    - exp-claude
    - exp-gpt4o

Save? [Y/n] Y
  Saved: studies/model-comparison.yaml
```

You can also write the YAML by hand:

```yaml
name: model-comparison
description: GPT-4o vs Claude on the extraction task
tags:
  - extraction
experiments:
  - exp-gpt4o
  - exp-claude
```

Reorder experiments to control the order they appear in the report. Add or remove experiments at any time and re-run to refresh the output.

### 3. Generate the study report

```bash
adgtk-study run model-comparison
```

Output:

```
Generating study report for: model-comparison
  Report : study-results/model-comparison/study_report.md
  CSV    : study-results/model-comparison/study_results.csv
```

---

## Reading the study report

`study_report.md` has three main sections.

### Cross-experiment overview table

The first section gives you the at-a-glance comparison — one row per experiment:

```
| Experiment | Runs | Pass | Fail | Avg Duration | metric_accuracy mean |
| --- | --- | --- | --- | --- | --- |
| exp-gpt4o | 5 | 4 | 1 | 4m 12s | 0.9120 |
| exp-claude | 5 | 5 | 0 | 3m 58s | 0.9340 |
```

Columns include every result metric and measurement mean that appeared in any experiment's runs.

### Per-experiment sections

Each experiment gets its own section with:

- **Configuration (first run)** — the `run.exp.config.yaml` from run 0, shown as a YAML block. This is the canonical "what is this experiment?" record.
- **Verdicts** — pass/fail/inconclusive/unknown counts and percentages
- **Timing** — total, average, std dev, min, and max run duration
- **Result metrics** — cross-run means, plus a per-run table
- **Measurement statistics** — mean-of-means and std across runs for every `MetricTracker` label
- **Config deviations** — if any run used a different blueprint than the majority, it is flagged here

### Missing experiments

If a blueprint lists an experiment that has no results folder on disk, it is noted at the top of the report so you know the comparison is incomplete.

---

## Using the combined CSV

`study_results.csv` contains one row per run across all experiments. The column schema matches the per-experiment `results.csv` but adds `experiment_name` as the leading column.

```python
import pandas as pd

df = pd.read_csv("study-results/model-comparison/study_results.csv")

# Mean accuracy per experiment
df.groupby("experiment_name")["metric_accuracy"].mean()

# Pass rate per experiment
df.groupby("experiment_name")["verdict"].apply(
    lambda s: (s == "pass").mean()
)

# Distribution of run durations
df.boxplot(column="duration_seconds", by="experiment_name")
```

Because every `tag_<key>` from every run is included as a column, you can also slice within experiments by any tag you set during runs:

```python
# Compare accuracy by model tag across all experiments
df.groupby(["experiment_name", "tag_model"])["metric_accuracy"].mean()
```

---

## Tips

**Mixing experiments with different metrics.** The CSV and report include all metric/measurement columns seen across all experiments. An experiment that doesn't record a particular metric will have blank cells for those columns — this is expected and handled correctly by pandas.

**Refreshing after new runs.** Re-running `adgtk-study run` regenerates both output files from scratch. All runs present on disk at that moment are included, so you can accumulate more runs and re-run the study to get updated statistics.

**Editing a blueprint.** Change the YAML in `studies/` directly — add experiments, remove them, or reorder them — then re-run to regenerate. The blueprint is the only persistent state; the output files are always regenerated.

**Using tags for richer comparisons.** If your scenarios use `result.tag("model", "gpt-4o")` and `result.tag("temperature", "0.7")`, those tags become `tag_model` and `tag_temperature` columns in the study CSV, letting you slice results by any combination of configuration dimensions.
