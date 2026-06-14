# ADR-007: Protocol-Based Interface Typing

**Status:** Accepted
**Date:** 2026-06-07

---

## Context

The factory system needs to instantiate user-defined scenarios and measurements without knowing their concrete types in advance. The framework must define what a valid scenario or measurement *looks like* (its interface) without forcing user classes to inherit from a specific base class.

Python provides two approaches to this: **abstract base classes (ABC)** which require explicit inheritance, and **`typing.Protocol`** which uses structural subtyping (duck typing with static enforcement).

---

## Decision

Use **`typing.Protocol`** for all public interface contracts in ADGTK. User-defined scenarios, measurements, and comparisons implement these protocols by having the right methods, without inheriting from any framework base class.

```python
# Framework defines the contract:
class ScenarioProtocol(Protocol):
    def run_scenario(self, result_folders: ExperimentRunFolders) -> RunResult:
        ...

# User implements it without inheriting:
class MyScenario:
    def run_scenario(self, result_folders: ExperimentRunFolders) -> RunResult:
        ...
        return RunResult(...)
```

**Key protocols in the codebase:**

| Protocol | Interface |
|----------|-----------|
| `ScenarioProtocol` | `run_scenario(folders) -> RunResult` |
| `ClassBasedMeasurement` | `measure(value) -> float` |
| `ClassBasedComparison` | `compare(a, b) -> float` |
| `direct_measurement` | `(value) -> float` (function protocol) |
| `distribution_measurement` | `(dataset) -> dict` (function protocol) |

`SupportsFactory` uses ABC because it requires `ClassVar` declarations that must be enforced — structural typing cannot check `ClassVar` presence reliably across all static analysis tools.

---

## Rationale

- **No framework coupling.** User scenario classes have no import from `adgtk` in their class definition. They are plain Python classes. This reduces the risk that a framework change breaks user code.
- **Flexible composition.** A class can satisfy multiple protocols simultaneously without a complex MRO. A class can be both a scenario and provide measurement capabilities.
- **Mypy-compatible.** `typing.Protocol` is fully supported by mypy, providing static type checking without requiring explicit inheritance declarations.
- **Cleaner user experience.** Users read the protocol definition to understand what methods they need; they don't need to understand ABC's abstract method mechanics.

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Abstract base classes for all interfaces | Forces framework imports into user scenario files; breaks if base class changes |
| Duck typing with no static enforcement | No IDE autocompletion or type checking; errors only surface at runtime |
| Dataclass-based interfaces | Cannot express method signatures; not suitable for behavioral contracts |
| `register()` on ABC | More explicit but requires framework coupling and `super()` calls |

---

## Consequences

- **Positive:** User scenario classes have zero required imports from `adgtk`. They are maximally portable.
- **Positive:** Any class with the right method signature satisfies the protocol — existing code can become a valid scenario without modification.
- **Negative:** Protocol satisfaction is structural, not declared. A class that *accidentally* has a `run_scenario` method will type-check as a `ScenarioProtocol`. This is intentional and consistent with Python's duck-typing philosophy.
- **Negative:** `SupportsFactory` (which needs `ClassVar` enforcement) uses ABC, creating a minor inconsistency. This is documented as a deliberate exception.

---

## Related Decisions

- [ADR-001](ADR-001-non-persistent-factory.md) — Factory uses `SupportsFactory` (ABC) for registration metadata
- [ADR-008](ADR-008-bootstrap-pattern.md) — Protocols define what gets registered via bootstrap
