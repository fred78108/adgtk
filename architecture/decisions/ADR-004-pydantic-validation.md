# ADR-004: Pydantic for All External Data Validation

**Status:** Accepted
**Date:** 2026-06-07

---

## Context

ADGTK reads external data from multiple sources: YAML blueprint files, JSON manifest files, study definition files, and the `.tracking/` registry. This data must be validated before use. Errors in this data — a missing required field, a wrong type, an invalid value — should produce a clear error message pointing to the source, not an obscure Python exception deep in the framework.

Separately, internal data structures (e.g., paths passed between functions) need to be lightweight and fast, without the overhead of validation.

---

## Decision

Use **Pydantic `BaseModel`** for all data that crosses a system boundary (read from disk, received from a user, returned from an API). Use **Python `dataclass`** or plain objects for internal data structures where validation is not needed.

| Data | Type | Reason |
|------|------|--------|
| `ExperimentDefinition` | Pydantic | Parsed from user YAML |
| `AttributeEntry` | Pydantic | Nested within ExperimentDefinition |
| `RunManifest` | Pydantic | Written to and read from JSON |
| `RunEntryModel` | Pydantic | Read/written to `.tracking/runs.json` |
| `RunResult` | Pydantic | Returned by scenarios (public interface) |
| `AnyObservation` | Pydantic (discriminated union) | Stored in manifests |
| `ExperimentRunFolders` | `dataclass` | Internal path structure; no external source |
| `FactoryEntry` | Internal class | Created by `register()` directly |

---

## Rationale

- **Clear error messages at system boundaries.** When a user's YAML is malformed, Pydantic reports the field path and expected type. This is far more useful than a `KeyError` buried in framework code.
- **Free serialization.** Pydantic models serialize to and from JSON/dict without custom converters, which simplifies writing and reading manifests.
- **Type safety with runtime enforcement.** `mypy` enforces types statically; Pydantic enforces them at runtime when reading external data. Both are needed.
- **Discriminated unions for observations.** Pydantic's discriminated union support makes `AnyObservation` type-safe and self-documenting without a complex `isinstance` tree.
- **Lightweight internals.** Internal data (e.g., `ExperimentRunFolders`) uses `dataclass` to avoid validation overhead on data the framework creates and controls.

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| `TypedDict` + manual validation | Too verbose; no automatic serialization; no runtime enforcement |
| `attrs` | Less ecosystem integration; Pydantic's JSON support is better for manifest I/O |
| `marshmallow` | More verbose schema definitions; less integrated with Python type hints |
| `dataclass` for everything | No runtime validation at system boundaries; errors surface later and are harder to diagnose |

---

## Consequences

- **Positive:** All external data is validated at the point of ingestion, with field-level error messages.
- **Positive:** `RunManifest.model_dump_json()` / `RunManifest.model_validate_json()` replace all custom serialization code.
- **Positive:** Schema changes to `RunManifest` are automatically reflected in JSON output.
- **Negative:** Pydantic adds a startup and validation cost. For the data volumes in ADGTK (single manifests, small registries), this cost is negligible.
- **Negative:** Pydantic version differences (v1 vs v2) can cause breakage. The project targets Pydantic v2.

---

## Related Decisions

- [ADR-003](ADR-003-filesystem-tracking.md) — `RunManifest` is the primary Pydantic-serialized artifact
- [ADR-005](ADR-005-module-level-observation-state.md) — Observations are Pydantic models stored in the module-level list
