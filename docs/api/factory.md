# Factory API

The factory is a runtime registry that maps `factory_id` strings to component classes and instantiation logic.

## Import

```python
from adgtk.factory import (
    SupportsFactory,
    register_to_factory,
    FactoryEntry,
    FactoryOrder,
    BlueprintQuestion,
)
```

---

## `SupportsFactory`

Abstract base class for factory-registered components.

```python
class SupportsFactory(ABC):
    factory_id: str        # unique identifier
    group: str             # logical group, e.g. "scenario", "evaluator"
    summary: str           # one-line description
    tags: list[str]        # labels for filtering
```

Inherit from this class and declare all four class attributes. Implement any `__init__` arguments you want to be configurable in experiment YAML.

---

## `register_to_factory`

Register a class into the factory. Can be used as a decorator or called directly.

```python
# Decorator
@register_to_factory
class MyScenario(SupportsFactory):
    ...

# Direct call
register_to_factory(MyScenario)

# Manual registration with explicit metadata
register(
    item=MyScenario,
    group="scenario",
    tags=["custom"],
    factory_id="my-scenario",
    summary="Does something useful",
    interview_blueprint=[]
)
```

---

## Factory operations

```python
from adgtk.factory import list_entries, create, get_entry

# List registered components
entries = list_entries()                    # all
entries = list_entries(group="scenario")   # by group
entries = list_entries(tags=["builtin"])   # by tag

# Instantiate a component
instance = create(factory_id="my-scenario", init_args={"model": "gpt-4o"})

# Retrieve an entry without instantiating
entry = get_entry(factory_id="my-scenario")
```

---

## `FactoryEntry`

Registry entry for a component.

| Attribute | Type | Description |
|-----------|------|-------------|
| `factory_id` | `str` | Unique identifier |
| `group` | `str` | Logical group |
| `tags` | `list[str]` | Filter labels |
| `summary` | `str` | One-line description |
| `creator` | `type` | The registered class |
| `interview_blueprint` | `list[BlueprintQuestion]` | Questions for the interactive builder |

---

## `FactoryOrder`

A request to instantiate a component, as deserialized from experiment YAML.

| Attribute | Type | Description |
|-----------|------|-------------|
| `factory_id` | `str` | ID to look up |
| `init_args` | `dict` | Arguments to pass to `__init__` |

---

## `BlueprintQuestion`

Defines a question in the interactive experiment builder. Used when you want custom prompting behavior during `adgtk build`.

| Attribute | Type | Description |
|-----------|------|-------------|
| `attribute` | `str` | Constructor argument name |
| `question` | `str` | Text shown to the user |
| `default` | `Any` | Default value |
| `required` | `bool` | Whether an answer is required |
