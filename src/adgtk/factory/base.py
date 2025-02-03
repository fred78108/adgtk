"""The Factory is a Dynamic Factory that is easy to extend object types.
The factory is a shared common resource. By having a flexible factory it
is easier to extend to new objects on behalf of the user without needing
the user to create their own factory and register that factory.

Versions:
v 0.1
- mvp

References:
- https://docs.python.org/3/library/typing.html#typing.TypedDict

TODO:

1.0

Defects:

1.0
"""

from typing import Protocol, Union, List, runtime_checkable, Callable, TypeVar
from adgtk.common import FactoryBlueprint

# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------


class DuplicateFactoryRegistration(Exception):
    """Used for registration collision"""

    default_msg = "Registration exists. Unregister first."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


class InvalidBlueprint(Exception):
    """Used when a blueprint is invalid. Covers both a FactoryBlueprint
    as well as any future blueprints."""

    default_msg = "Invalid Blueprint."

    def __init__(self, message: str = default_msg):
        super().__init__(message)


# ----------------------------------------------------------------------
# Protocols, Types, & TypeDict
# ----------------------------------------------------------------------

T = TypeVar("T", bound=Callable, covariant=True)

@runtime_checkable
class FactoryImplementable(Protocol):
    """Can be registered and created with the factory.
    """
    blueprint: FactoryBlueprint
    description: str

    __init__: Callable
    

class SupportsFactoryRegistry(Protocol):
    """A factory must have the following"""

    def registry_listing(
        self,
        group_label: Union[str, None] = None
    ) -> List[str]:
        """Lists factory entries. if no group listed it returns groups,
        else if a group is entered it returns all types in that group.

        :param group_label: A group label, defaults to None
        :type group_label: Union[str, None], optional
        :return: A listing of types in a group or all groups
        :rtype: List[str]
        """


# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------
