"""component.py is the new factory design introduced with the v0.2.0
re-write. The goal of this re-write is to greatly simplify the amount of
boilerplate code needed by grounding the design with pydantic + Protocol

This is intended to be non-persistent so each run will need to handle
their own assembly.

Goals
=====
A dynamic factory for both internal and user defined objects.

Testing
=======
py -m pytest -s test/factory/test_component_factory.py

Notes
=====
1. MVP design.
2. Goal remains the ability to intermix both framework provided with the
   user provided entries.
3. No persistent storage. The factory is loaded via the CLI by the
   bootstrap.py file. The design has the user update their bootstrap
   file.
4. When to log. when a raise is about communication, no log, else log

Roadmap
=======
1. Consider internal_only objects that are hidden from reports as well
   as denied the ability to register if outside of this project. i.e. a
   user cannot register additional internal-only objects group.
2. Consider an experiment definition override to another bootstrap file.
3. on the report, between sections increase the line length to match.

Defects
=======
1.
"""
import os
import sys
# before importing others
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

from adgtk.factory.structure import (
    BlueprintQuestion,
    SupportsFactory,
    FactoryEntry,
    FactoryOrder
)
from pydantic import ValidationError
from typing import (
    Callable,
    Optional,
    Union)
import secrets
import inspect
import copy

# setup logfile for this and sub-modules
from adgtk.utils import create_logger

# Set up module-specific logger
_logger = create_logger(
    "adgtk.factory.log",
    logger_name=__name__,
    subdir="framework"
)


# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------

_inventory: dict[str, FactoryEntry] = {}  # all constructors
_groups: list[str] = []                   # only grows, consider dict[str,int]


# ----------------------------------------------------------------------
# Decorator
# ----------------------------------------------------------------------
def register_to_factory(cls):
    """A decorator for registration to the factory.

    Args:
        cls: The class to be registered. Must be a subclass of SupportsFactory.

    Returns:
        The registered class.

    Raises:
        ValueError: If the class does not inherit from SupportsFactory.
    """
    if issubclass(cls, SupportsFactory):
        register(
            item=cls,
            group=cls.group,
            tags=cls.tags,
            factory_id=cls.factory_id,
            summary=cls.summary,
            interview_blueprint=cls.interview_blueprint,
            factory_can_init=cls.factory_can_init
        )
        return cls

    raise ValueError(
        "This decorator supports children of SupportsFactory class")

# ----------------------------------------------------------------------
# Public
# ----------------------------------------------------------------------


def register(
    item: Union[Callable, SupportsFactory],
    group: Optional[str] = None,
    tags: Optional[list] = None,
    factory_id: Optional[str] = None,
    summary: str = "No summary recorded",
    interview_blueprint: Optional[list[BlueprintQuestion]] = None,
    factory_can_init: Optional[bool] = None
) -> str:
    """Registers an item into the factory inventory.

    Args:
        item: The callable item or a class inheriting from SupportsFactory.
        group: The group name. Required if item is not a SupportsFactory.
            If item is a SupportsFactory, this overrides the item's
            default group.
        tags: Tags for searching the factory. Defaults to None.
        factory_id: The identifier for the factory entry. If None, it uses
            item.factory_id or generates a random temporary ID.
        summary: A brief summary for listings.
            Defaults to "No summary recorded".
        interview_blueprint: Questions to ask for experiment definitions.
            Defaults to None.
        factory_can_init: Whether the factory can initialize the item. If None,
            it is determined based on the item type.

    Returns:
        The factory ID used for registration.

    Raises:
        ValueError: If the item is not callable or the factory_id is invalid.
        IndexError: If the factory_id already exists in the inventory.
    """
    # set the factory_can_init
    if factory_can_init is None:
        # If not set then check, if not SupportsFactory then false
        factory_can_init = False
        if inspect.isclass(item) and issubclass(item, SupportsFactory):
            factory_can_init = item.factory_can_init

    if not callable(item):
        raise ValueError("Invalid item. It must be callable.")

    # shorter than UUID.
    factory_id = factory_id or getattr(
        item, "factory_id", f"tmp.{secrets.token_hex(4)}")

    if factory_id is None:
        msg = "Failed to create factory_id"
        _logger.error(msg)
        raise ValueError(msg)

    # verify formatting
    if isinstance(factory_id, int):
        msg = "Invalid factory_id. Must not be able to convert to int"
        _logger.info(msg)
        raise ValueError(msg)
    try:
        _ = int(factory_id)
    except ValueError:
        pass
    else:
        msg = (f"Invalid factory_id {factory_id}. Must not be able "
               "to convert to int")
        _logger.info(msg)
        raise ValueError(msg)

        pass
    if factory_id in _inventory:
        raise IndexError(f"factory_id: {factory_id} already exists")

    if (inspect.isclass(item) and issubclass(item, SupportsFactory)):
        if summary == "No summary recorded":
            summary = item.summary

        group = group or item.group
        tags = (tags or []) + item.tags
        interview_blueprint = item.interview_blueprint
    else:
        if group is None:
            raise ValueError("Group required if not using SupportsFactory.")
        tags = tags or []
        if interview_blueprint is None:
            interview_blueprint = []

    entry = FactoryEntry(
        factory_id=factory_id,
        factory_can_init=factory_can_init,
        creator=item,
        group=group,
        tags=tags,
        interview_blueprint=interview_blueprint,
        summary=summary
    )

    if group not in _groups:
        _groups.append(group)
    if entry.factory_id is None:
        raise ValueError("entry construction error. missing factory_id")

    _inventory[entry.factory_id] = entry
    msg = f"Registered factory_id: {factory_id}"
    _logger.info(msg)
    return entry.factory_id


def create_using_order(order: FactoryOrder) -> SupportsFactory:
    """Creates an object using a FactoryOrder structure.

    Provides a simplified interface for Scenario loading and structured
    component instantiation. This is not intended for fetching uninitialized
    callables.

    Args:
        order: The FactoryOrder containing the factory_id and initialization
            arguments.

    Returns:
        The instantiated object.

    Raises:
        ValidationError: If the order does not conform to the
        FactoryOrder model.
    """
    if not isinstance(order, FactoryOrder):
        try:
            order = FactoryOrder(**order)
        except ValidationError:
            _logger.error("Invalid order submitted")
            raise

    if order.init_args is None:
        return create(factory_id=order.factory_id)

    init_args = order.init_args
    created = create(factory_id=order.factory_id, **init_args)
    return created


def create(factory_id: str, **kwargs) -> SupportsFactory:
    """Creates an instance of an item from the factory inventory.

    Args:
        factory_id: The ID of the item to instantiate.
        **kwargs: Arbitrary keyword arguments passed to the item's constructor.

    Returns:
        An instance of the registered factory item.

    Raises:
        KeyError: If the factory_id is not found in the inventory.
        ValueError: If the item is marked as not supporting initialization.
    """
    if factory_id not in _inventory:
        msg = f"{factory_id} not in factory"
        _logger.error(msg)
        raise KeyError(msg)

    item = _inventory[factory_id]
    creator = item.creator
    if item.factory_can_init:
        created = creator(**kwargs)
        return created

    msg = (f"Attempted to init factory_id: {item.factory_id} that does "
           "not support init.")
    _logger.error(msg)
    raise ValueError(msg)


def get_interview(factory_id: str) -> list[BlueprintQuestion]:
    """Retrieves the interview blueprint for a factory item.

    Args:
        factory_id: The ID of the item to retrieve the interview for.

    Returns:
        A list of BlueprintQuestion objects.

    Raises:
        KeyError: If the factory_id is not found in the inventory.
    """
    if factory_id not in _inventory:
        msg = f"{factory_id} not in factory"
        _logger.error(msg)
        raise KeyError(msg)

    item = _inventory[factory_id]
    return item.interview_blueprint


def get_callable(factory_id: str) -> Callable:
    """Returns the underlying callable from the factory without
    initializing it.

    Args:
        factory_id: The ID of the item to fetch.

    Returns:
        The registered callable (e.g., function or class constructor).

    Raises:
        KeyError: If the factory_id is not found in the inventory.
    """
    if factory_id not in _inventory:
        msg = f"{factory_id} not in factory"
        _logger.error(msg)
        raise KeyError(msg)

    entry = _inventory[factory_id]
    return entry.creator


def remove(factory_id: str) -> None:
    """Removes an item from the factory inventory.

    Args:
        factory_id: The ID of the item to remove.

    Raises:
        KeyError: If the factory_id is not found in the inventory.
    """
    if factory_id not in _inventory.keys():
        msg = f"{factory_id} not in factory"
        _logger.error(msg)
        raise KeyError(msg)

    # TODO: in the future, consider removing from _groups
    del _inventory[factory_id]


def list_entries(
    tags: Optional[Union[str, list[str]]] = None,
    group: Optional[str] = None
) -> list:
    """Lists the entries within the factory inventory, optionally filtered.

    Args:
        tags: A single tag or list of tags to filter by. Entries must contain
            all provided tags. Defaults to None.
        group: A specific group name to filter by. Defaults to None.

    Returns:
        A list of FactoryEntry objects that match the search criteria.

    Raises:
        ValueError: If the inventory appears to be corrupted.
    """
    found: list[FactoryEntry] = []
    entry: FactoryEntry

    # cleanup input
    if isinstance(tags, str) and len(tags) > 0:
        tags = [tags]

    # this should always return true but just in case:
    if isinstance(tags, list):
        # cleanup any white-space
        tags = [x.strip() for x in tags]

        # and if all that is left is an empty string
        for tag in tags:
            if tag == "":
                tags.remove("")

    for _, entry in sorted(_inventory.items(), key=lambda x: x[0]):
        if not isinstance(entry, FactoryEntry):
            try:
                entry = FactoryEntry(**entry)
            except ValidationError:
                msg = "The Inventory appears to be corrupted"
                _logger.error(msg)
                raise ValueError(msg)

        if tags is None:
            if group is None:
                found.append(entry)
            elif group.lower() == entry.group.lower():
                found.append(entry)
        elif all(entry_tag in entry.tags for entry_tag in tags):
            if group is None:
                found.append(entry)
            elif group == entry.group:
                found.append(entry)
    return found


def report(
    tags: Optional[Union[str, list[str]]] = None,
    group: Optional[str] = None
) -> None:
    """Generates and prints a formatted report of factory entries to
    the console.

    Args:
        tags: Filter report entries by specific tags. Defaults to None.
        group: Filter report entries by a specific group. Defaults to None.
    """
    title = "Factory report"
    if group is not None:
        title += f" - group={group}"
    if tags is not None:
        if isinstance(tags, list):
            tag_str = " ".join(tags)
            title += f", tags={tag_str}"
        else:
            title += f", tag={tags}"

    longest = 0
    all_entries = ""
    first = True
    if group is not None:
        search_groups = [group]
    else:
        _groups.sort()
        search_groups = _groups

    for group in search_groups:
        if first:
            all_entries += f"{group.upper()}\n"
            first = False
        else:
            all_entries += "-"*79
            all_entries += f"\n{group.upper()}\n"

        entries = list_entries(tags=tags, group=group)
        for entry in entries:
            entry_str = f"  - {entry.factory_id:<15} | "
            if entry.factory_can_init:
                entry_str += " Y  |  "
            else:
                entry_str += " N  |  "
            entry_str += f"{entry.summary:50} |"

            tags_str = ""
            if entry.tags is not None:
                tags_str = " ".join(entry.tags)
            entry_str += tags_str

            if len(entry_str) > longest:
                longest = len(entry_str)

            all_entries += f"{entry_str}\n"

    # Setup title/'banner', the spaced out title for the columns
    name = "Factory ID"
    summary = "Summary"
    banner = f"    {name:<15} | init | {summary:<50} | Tags"
    if len(title) > longest:
        longest = len(title)
    if len(banner) > longest:
        longest = len(banner)

    if longest > len(title):
        # now center the title
        spaces = int((longest-len(title))/2)
        space_str = " "*spaces
        title = f"\n{space_str}{title}"
    # and finally put everything together and print
    line = "="*longest
    small_line = "-"*longest
    title += f"\n{line}\n{banner}\n{small_line}\n{all_entries}"
    print(title)


def entry_exists(factory_id: str) -> bool:
    """Checks if a factory ID exists in the inventory.

    Args:
        factory_id: The factory ID to check.

    Returns:
        True if the ID exists, False otherwise.
    """
    return factory_id in _inventory


def group_exists(group: str) -> bool:
    """Checks if a group exists in the factory.

    Args:
        group: The group name to check.

    Returns:
        True if the group exists, False otherwise.
    """
    return group in _groups


def get_group_names() -> list:
    """Returns a list of all registered group names.

    Returns:
        A list of strings representing group names.
    """
    return copy.deepcopy(_groups)
