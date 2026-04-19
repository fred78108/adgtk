# flake8: noqa: E402
"""Central registry and factory for measurement callables.

This module provides a lightweight registration and lookup system for
measurement implementations, including:

- class-based callables (single-input or pairwise comparison),
- direct functions (single-input or pairwise comparison), and
- distribution-oriented functions.

Key behaviors:
1. Supports registration of both classes and functions.
2. For class-based items, supports registering either the class or an
   already-created callable instance.
3. Class constructors are expected to be callable without required
   positional arguments unless provided at creation time.
4. Centralizes built-in and user-defined measurements in one inventory.
"""

import os
import sys
# ----------------------------------------------------------------------
# Start of path verification
# ----------------------------------------------------------------------
path = os.getcwd()
bootstrap_file = os.path.join(path, "bootstrap.py")
if not os.path.exists(bootstrap_file):
    print("ERROR: Unable to locate the bootstrap.py. Please check your path.")
    sys.exit(1)
# ----------------------------------------------------------------------
# End of path verification
# ----------------------------------------------------------------------
import inspect
from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
    Optional,
    Protocol,
    Sequence,
    TypedDict,
    Union,
    get_args,
    runtime_checkable
)
import uuid
import numpy as np
from adgtk.utils import create_logger
# ----------------------------------------------------------------------
# Protocols, Interfaces, & Structures
# ----------------------------------------------------------------------


# ------------- measurements -------------
@runtime_checkable
class ClassBasedMeasurement(Protocol):
    """Protocol for class-based single-input measurements.

    Implementations must be callable with one input and return a numeric score.
    """

    def __call__(self, a:Any) -> Union[int, float]: ...


@runtime_checkable
class ClassBasedComparison(Protocol):
    """Protocol for class-based pairwise comparison measurements.

    Implementations must be callable with 2 inputs and return a numeric score.
    """

    def __call__(self, a:Any, b:Any) -> Union[int, float]: ...


direct_measurement = Callable[[Any], Union[int, float]]
direct_comparison = Callable[[Any, Any], Union[int, float]]
distribution_measurement = Callable[[Any], Union[list, np.ndarray]]
distribution_comparison = Callable[[Iterable, Iterable], float]

supports_factory = Union[
        ClassBasedComparison,
        ClassBasedMeasurement,
        direct_measurement,
        direct_comparison,
        distribution_measurement,
        distribution_comparison
        ]

measurement_type = Literal[
        "class_based_measure",
        "class_based_compare",
        "class_other",
        "direct_measure",
        "direct_comparison",
        "direct_other",
        "distribution_measure",
        "distribution_comparison"]

# ------------- entry -------------


class MeasFactoryEntry(TypedDict):
    factory_id: str
    meas_type: measurement_type
    tags: list[str]
    item: supports_factory
    description: str


# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------

_inventory: dict[str, MeasFactoryEntry] = {}


# Set up module-specific logger
_logger = create_logger(
    "adgtk.measurement.factory.log",
    logger_name=__name__,
    subdir="framework"
)


# ----------------------------------------------------------------------
# Helpers, can be public but designed for internal
# ----------------------------------------------------------------------
def classify_measurement(item: Callable) -> measurement_type:
    """Classify a callable into a supported measurement type.

    Args:
        item: A function, class, or callable candidate to classify.

    Returns:
        A ``measurement_type`` literal describing how the item is treated
        by the factory.

    Raises:
        ValueError: If ``item`` is not recognized as a callable supported by
            this classifier.
    """
    if inspect.isclass(item):
        if issubclass(item, ClassBasedMeasurement):
            return "class_based_measure"
        elif issubclass(item, ClassBasedComparison):
            return "class_based_compare"
        else:
            return "class_other"
    elif inspect.isfunction(item):
        if get_args(item) == get_args(direct_measurement):
            return "direct_measure"
        if get_args(item) == get_args(direct_comparison):
            return "direct_comparison"
        if get_args(item) == get_args(distribution_measurement):
            return "distribution_measure"
        if get_args(item) == get_args(distribution_comparison):
            return "distribution_comparison"
        return "direct_other"
    raise ValueError("Not callable")


# ----------------------------------------------------------------------
# Public, designed for use outside module
# ----------------------------------------------------------------------
def get_measurement_factory_entry(factory_id: str) -> MeasFactoryEntry:
    """Return a registered factory entry by ID.

    Args:
        factory_id: The factory identifier to look up.

    Raises:
        IndexError: If no entry exists for ``factory_id``.

    Returns:
        The matching measurement factory entry.
    """
    if factory_id not in _inventory.keys():
        _logger.error("unable to locate factory_id %s", factory_id)
        raise IndexError("unable to locate factory_id %s", factory_id)
    return _inventory[factory_id]


def register_to_measurement_factory(
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    factory_id: Optional[str] = None
):
    """Decorator to register a measurement class/function in the factory.

    Args:
        description: Optional override for the registered description.
            If omitted, the decorated object's docstring is used.
        tags: Optional list of user-defined tags for filtering.
        factory_id: Optional explicit ID to register under.

    Raises:
        ValueError: If neither ``description`` nor a docstring is available.
    """
    def decorator(cls):
        nonlocal description
        if description is None:
            description = inspect.getdoc(cls)
        if description is None:
            _logger.error(
                "Attempted to register via decorator without a "
                "description or docstring")
            raise ValueError(
                "register_to_factory requires a docstring or description set")
        _ = manual_measurement_factory_register(
            item=cls,
            description=description,
            tags=tags,
            factory_id=factory_id
        )
        return cls

    return decorator


def manual_measurement_factory_register(
    item: supports_factory,
    description: str,
    tags: Optional[list[str]] = None,
    factory_id: Optional[str] = None,
) -> str:
    """Register a measurement object directly in the factory.

    Args:
        item: The class/function/callable to register.
        description: Human-readable description for discovery/use.
        tags: Optional list of user tags for later filtering.
        factory_id: Optional explicit registration ID. If omitted, a name
            or generated UUID is used.

    Raises:
        KeyError: If the requested ``factory_id`` is already registered.

    Returns:
        The factory ID used for this registration.
    """
    global _inventory
    if factory_id is None:
        if inspect.isfunction(item) or inspect.isclass(item):
            factory_id = item.__name__
        else:
            factory_id = str(uuid.uuid4())
    if factory_id in _inventory.keys():
        _logger.error(
            "Factory Id %s already exists. unable to register", factory_id)
        raise KeyError("Factory Id %s already exists", factory_id)
    if tags is None:
        tags = []

    entry = MeasFactoryEntry(
        item=item,
        tags=tags,
        description=description,
        meas_type=classify_measurement(item),
        factory_id=factory_id
    )
    _inventory[factory_id] = entry
    _logger.info("Registered %s to factory", factory_id)
    return factory_id


def get_measurements_by_type(
    filter_by_type: Optional[measurement_type] = None
) -> list[MeasFactoryEntry]:
    """List registered measurements, optionally filtered by type.

    Args:
        filter_by_type: Optional measurement type to filter by. If ``None``,
            all entries are returned.

    Returns:
        A list of entries matching the requested type filter.
    """
    if filter_by_type is None:
        return list(_inventory.values())
    entries = []
    for _, item in _inventory.items():
        if item["meas_type"] == filter_by_type:
            entries.append(item)
    return entries


def get_measurements_by_tag(
    tags: Optional[Union[str, list[measurement_type]]]
) -> list[MeasFactoryEntry]:
    """List registered measurements that match one or more tags.

    Matching is based on overlap between provided tags and each entry's
    ``tags`` list.

    Args:
        tags: A single tag string, a sequence of tags, or ``None``.
            If ``None``, all entries are returned.

    Returns:
        A list of entries with at least one matching tag.
    """

    if tags is None:
        return list(_inventory.values())
    if isinstance(tags, str):
        search_tags = [tags]
    elif isinstance(tags, Sequence):        
        search_tags = tags      # type: ignore
    entries = []
    for _, item in _inventory.items():
        # check for overlap between tags
        if bool(set(search_tags) & set(item["tags"])):
            entries.append(item)
    return entries


def create_measurement(factory_id: str, **kwargs) -> supports_factory:
    """Create or retrieve a measurement callable by factory ID.

    Behavior:
    - For direct function registrations, returns the function as-is.
    - For class registrations, instantiates the class with ``**kwargs``.
    - For callable instances, returns the registered instance.

    Args:
        factory_id: Registered factory ID to resolve.
        **kwargs: Constructor keyword arguments used only when the
            registered item is a class.

    Raises:
        IndexError: If ``factory_id`` is not found.

    Returns:
        A callable measurement object compatible with the registered type.
    """
    if factory_id not in _inventory.keys():
        raise IndexError("factory id %s not found", factory_id)

    entry = _inventory[factory_id]

    # direct
    if entry["meas_type"].startswith("direct"):
        return entry["item"]

    # class based
    item = entry["item"]
    if inspect.isclass(item):
        return item(**kwargs)
    return item


def get_measurement_factory_labels() -> list[str]:
    """Return all registered factory IDs."""
    return list(_inventory.keys())
