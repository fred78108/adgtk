"""Provides a central measurement factory.

Goals
=====
a dynamic factory that is focused on measuring of data.

Design
======
1. manages both classes as well as functions.
2. if its a class, supports both the class and an instance of
3. if its a class, the init must not require arguments. If you need
   to modify the init, use the full component factory
4. The goal is to centralize the measurements, both  those built-in and
   user defined.

Testing
=======
Pending

Notes
=====
1. 
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
    """For generic class based measurements"""

    def __call__(self, a:Any) -> Union[int, float]: ...


@runtime_checkable
class ClassBasedComparison(Protocol):
    """For generic class based comparisons"""

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
    factory_id:str
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
def get_measurement_factory_entry(factory_id:str) -> MeasFactoryEntry:
    """Gets the entry for a factory id

    Args:
        factory_id (str): the id to get

    Raises:
        IndexError: Unable to locate the factory id requested

    Returns:
        MeasFactoryEntry: The entry in the factory
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
    """Decorator that registers a measurement to the factory

    Args:
        description (Optional[str]): Overrides the docstring
        tags (Optional[list[str]]): For filtering by user tag
        factory_id (Optional[str]): Requesting a specific ID

    Raises:
        ValueError: No docstring or description set
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
    description:str,
    tags: Optional[list[str]] = None,
    factory_id: Optional[str] = None,
) -> str:
    """registers a measurement to the measurement factory

    Args:
        item (supports_factory): The item to register
        description (str): The associated description
        tags (Optional[list[str]], optional): Tags for further filtering
            Defaults to None.
        factory_id (Optional[str], optional): The requested ID
            Defaults to None.

    Raises:
        KeyError: The requested factory ID already exists

    Returns:
        str: the registered factory id
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
    filter_by_type:Optional[measurement_type] = None
) -> list[MeasFactoryEntry]:
    """Returns the measurements in the factory based on type

    Args:
        filter_by_type (Optional[measurement_type], optional): Filter by
            type. Defaults to None.

    Returns:
        list[MeasFactoryEntry]: All factory entries that fit the search
    """
    if filter_by_type is None:
        return list(_inventory.values())
    entries = []
    for _, item in _inventory.items():
        if item["meas_type"] == filter_by_type:
            entries.append(item)
    return entries

def get_measurements_by_tag(
    tags:Optional[Union[str, list[measurement_type]]]
) -> list[MeasFactoryEntry]:
    """Returns the measuments in the factory based on tag

    Args:
        tags (Optional[Union[str, list[measurement_type]]]): _description_

    Returns:
        list[MeasFactoryEntry]: _description_
    """
    
    if tags is None:
        return list(_inventory.values())
    if isinstance(tags, str):
        search_tags = [tags]
    elif isinstance(tags, Sequence):
        search_tags = tags    
    entries = []
    for _, item in _inventory.items():
        # check for overlap between tags
        if bool(set(search_tags) & set(item["tags"])):
            entries.append(item)
    return entries


def create_measurement(factory_id:str, **kwargs) -> supports_factory:
    """Creates the measurement for calling purposes. If already callable
    it returns the registered measurement.

    Args:
        factory_id (str): The factory ID to create
        **kwargs: Additional arguments to pass to the class constructor
                  if the item is a class.

    Raises:
        IndexError: If the factory ID is not found.

    Returns:
        supports_factory: The created or registered measurement.
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
    return list(_inventory.keys())
