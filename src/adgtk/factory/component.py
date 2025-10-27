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
    cast,
    Callable,
    Optional,
    Type,
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
    """A decorator for registration to the factory"""
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
    """Registers an item into the factory.

    :param item: The callable item
    :type item: Union[Callable, SupportsFactory]
    :param group: the group name if not SupportsFactory. Required if
        item is not SupportsFactory. If SupportsFactory it overrides
        the item value for the group. defaults to None
    :type group: Optional[str], optional
    :param tags: tags for searching the factory, defaults to None
    :type tags: Optional[list], optional
    :param factory_id: The id for the factory, defaults to None
    :type factory_id: Optional[str], optional
    :param summary: The summary for listings, defaults to "No summary recorded"
    :type summary: str, optional
    :param interview_blueprint: The questions to ask for experiment
        definitions, defaults to None
    :type interview_blueprint: Optional[list[BlueprintQuestion]], optional
    :raises ValueError: Invalid request, failure to process, etc    
    :raises IndexError: Entry already exists
    :return: The factory id now entered into the factory
    :rtype: str
    """
    global _inventory, _groups

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
    """Creates an object using a FactoryOrder. This provides an easier
    interface for Scenario loading, etc. This does not work for fetching
    a callable.

    :param order: The order to process
    :type order: FactoryOrder
    :return: The resulting object with the values set in the init_args
    :rtype: T
    """
    if not isinstance(order, FactoryOrder):
        try:
            order = FactoryOrder(**order)
        except ValidationError as e:
            _logger.error("Invalid order submitted")
            raise

    if order.init_args is None:
        return create(factory_id=order.factory_id)

    init_args = order.init_args
    created = create(factory_id=order.factory_id, **init_args)
    return created


def create(factory_id: str, **kwargs) -> SupportsFactory:
    """Creates an instance of the item

    :param factory_id: The id to create
    :type factory_id: str
    :raises KeyError: Unable to find in the factory
    :return: An instance of the factory item
    :rtype: T
    """
    global _inventory

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
    """Provides an interview for a factory item based on the
    data provided at registration

    :param factory_id: The id to obtain the interview for
    :type factory_id: str
    :raises KeyError: Unable to find the id in the factory
    :return: The interview
    :rtype: list[BlueprintQuestion]
    """
    if factory_id not in _inventory:
        msg = f"{factory_id} not in factory"
        _logger.error(msg)
        raise KeyError(msg)

    item = _inventory[factory_id]
    return item.interview_blueprint


def get_callable(factory_id: str) -> Callable:
    """Returns a callable. It does not attempt to initialize.

    :param factory_id: The id of the item to fetch
    :type factory_id: str
    :raises KeyError: Unable to find the factory id
    :return: a callable object, ex function. does not invoke
    :rtype: Callable
    """
    global _inventory

    if factory_id not in _inventory:
        msg = f"{factory_id} not in factory"
        _logger.error(msg)
        raise KeyError(msg)

    entry = _inventory[factory_id]
    return entry.creator


def remove(factory_id: str) -> None:
    """Removes an item from the factory

    :param factory_id: The id of the item to remove
    :type factory_id: str
    :raises KeyError: Unable to locate id
    """

    global _inventory

    if not factory_id in _inventory.keys():
        msg = f"{factory_id} not in factory"
        _logger.error(msg)
        raise KeyError(msg)

    # TODO: in the future, consider removing from _groups
    del _inventory[factory_id]


def list_entries(
    tags: Optional[Union[str, list[str]]] = None,
    group: Optional[str] = None
) -> list:
    """Lists the entries within the factory

    :param tags: Filter on tag(s), defaults to None
    :type tags: Optional[Union[str, list[str]]], optional
    :param group: Filter on a group, defaults to None
    :type group: Optional[str], optional
    :raises ValueError: Corruption of the inventory
    :return: A list of entries that match the search
    :rtype: list
    """
    global _inventory

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
    """Generates a report and prints to console of all the files that
    are curently in the inventory.

    :param tags: The tags to filter for, defaults to None
    :type tags: Optional[Union[str, list]], optional
    """
    global _groups

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

    return factory_id in _inventory


def group_exists(group: str) -> bool:
    return group in _groups


def get_group_names() -> list:
    return copy.deepcopy(_groups)
