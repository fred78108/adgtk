"""Common structure. Primary purpose is to avoid circular imports as
well as consistent data structure.
"""

import logging
from enum import Enum, auto
from typing import TypedDict, Required, Any, Union, cast, Optional, NotRequired
from numbers import Number
import anytree


# ----------------------------------------------------------------------
# Common structures
# ----------------------------------------------------------------------
# These structures are used for blueprint/generation of experiment
# blueprints only. They are NOT used when writing to disk the experiment
# which will be just the values.


class ArgumentType(Enum):
    """Identify the argument type."""
    BLUEPRINT = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    ML_STRING = auto()
    LIST = auto()
    DICT = auto()
    BOOL = auto()


class ArgumentSetting(TypedDict):
    """The indiviudal setting."""
    help_str: Required[str]
    argument_type: Required[ArgumentType]    
    default_value: NotRequired[Any]
    group_label: NotRequired[str]               # require when Blueprint
    list_arg_type: NotRequired[ArgumentType]    # arg type for lists
    list_group_label: NotRequired[str]          # for list of Blueprints
    list_intro: NotRequired[str]                # UX for lists
    list_min: NotRequired[int]                  # minimum list count
    introduction: NotRequired[str]

    

class FactoryBlueprint(TypedDict):
    """A Blueprint is used to create a template for an experiment. The
    blueprint pattern is seeking to create a generic template for a user
    of the package to create their own specifications without needing to
    code one. A common set of factories takes these specifications and
    creates the required objects in order to perform an experiment. The
    creators (typically a Class) must include a FactoryBlueprint as well
    in order to ensure consistency from user defined "experiment" to the
    factories.

    group_label     : identifies which group. Useful for defaults.
    type_label      : the identifier within the group of the creator
    arguments       : the arguments to be passed on init to the creator
    introduction    : used to introduce a component to an agent or human
    """    
    group_label: Required[str]
    type_label: Required[str]
    arguments: Required[dict[str, ArgumentSetting]]
    introduction: NotRequired[str]


class ExperimentDefinition(TypedDict):
    """The outer wrapper of an experiment. writes to disk, etc

    :param TypedDict: _description_
    :type TypedDict: _type_
    """
    configuration: Required[FactoryBlueprint]
    comments: str


class ComponentDef(TypedDict):
    """A ComponenttDef is used to create an ojbect. The    
    group_label     : identifies which group. Useful for defaults.
    type_label      : the identifier within the group of the creator
    arguments       : the arguments to be passed on init to the creator
    """
    group_label: Required[str]
    type_label: Required[str]
    arguments: Required[dict[str, Union[str, list, int, float, dict]]]

# ----------------------------------------------------------------------
# functions
# ----------------------------------------------------------------------


def default_is_arg_type(sample: dict) -> bool:
    """Validates the default argument aligns with the type

    :param sample: the sample
    :type sample: ArgumentSetting
    :return: expected type
    :rtype: True
    """
    valid = True
    if not isinstance(sample, dict):
        valid = False
    elif sample["argument_type"] == ArgumentType.BLUEPRINT:
        valid = isinstance(sample["default_value"], str)
    elif sample["argument_type"] == ArgumentType.STRING:
        valid = isinstance(sample["default_value"], str)
    elif sample["argument_type"] == ArgumentType.INT:
        valid = isinstance(sample["default_value"], int)
    elif sample["argument_type"] == ArgumentType.FLOAT:
        valid = isinstance(sample["default_value"], float)
    elif sample["argument_type"] == ArgumentType.BOOL:
        valid = isinstance(sample["default_value"], bool)
    elif sample["argument_type"] == ArgumentType.DICT:
        valid = isinstance(sample["default_value"], dict)
    elif sample["argument_type"] == ArgumentType.LIST:
        valid = isinstance(sample["default_value"], list)
    else:
        valid = False

    return valid


def is_valid_arg_setting(sample: dict) -> bool:
    """Validates properly formatted arg setting

    :param sample: the potential blueprint arguments
    :type sample: dict
    :return: T: Valid argument setting
    :rtype: bool
    """
    valid = True
    if not isinstance(sample, dict):
        valid = False
    elif "argument_type" not in sample.keys():
        valid = False
    elif "default_value" not in sample.keys():
        valid = False
    elif "help_str" not in sample.keys():
        return False

    if not valid:
        return False

    if not isinstance(sample["argument_type"], ArgumentType):
        valid = False
    if not isinstance(sample["help_str"], str):
        valid = False
    if not isinstance(sample["argument_type"], ArgumentType):
        valid = False

    if not valid:
        return False

    return default_is_arg_type(sample)


def is_blueprint(sample: dict) -> bool:
    """verifies a dict is a blueprint

    :param sample: the potential blueprint
    :type sample: dict
    :return: T: is a blueprint
    :rtype: bool
    """
    valid = True

    try:
        if not isinstance(sample, dict):
            return False

        if "group_label" not in sample.keys() and valid:
            valid = False
        elif "type_label" not in sample.keys() and valid:
            valid = False

        if "arguments" not in sample.keys() and valid:
            valid = False
        else:
            if not isinstance(sample["arguments"], dict):
                valid = False

        if not valid:
            return False

        # value checks
        if not isinstance(sample["group_label"], str):
            valid = False
        if not isinstance(sample["type_label"], str):
            valid = False

        if not valid:
            return False

        for _, item in sample["arguments"].items():
            valid = is_valid_arg_setting(item)
            if not valid:
                return False

        return True
    except KeyError:
        # and to be extra safe.
        return False


def build_tree(
    blueprint: dict[str, Any],
    parent: anytree.Node
) -> None:
    """Uses Anytree to create a tree object for rendering. The function
    is designed to be recursive in order to be as flexible as possible.

    :param blueprint: The blueprint for the item
    :type blueprint: FactoryBlueprint
    :param parent: The parent
    :type parent: anytree.Node
    """
    if parent is None:
        parent = anytree.Node(blueprint["group_label"])

    item_node = anytree.Node(blueprint["type_label"], parent=parent)

    for key, item in blueprint["arguments"].items():
        please_add = True
        if isinstance(item, dict):
            if "arguments" in item and "group_label" in item \
                    and "type_label" in item:
                child_node = anytree.Node(key, parent=item_node)
                build_tree(blueprint=item, parent=child_node)
                please_add = False
        if isinstance(item, list):
            please_add = False
            list_node = anytree.Node(key, parent=item_node)
            for entry in item:
                if "arguments" in entry and "group_label" in entry \
                        and "type_label" in entry:
                    entry = cast(dict, entry)
                    build_tree(blueprint=entry, parent=list_node)
                else:
                    for item_entry in entry:
                        child_node = anytree.Node(item_entry, parent=list_node)
                        anytree.Node(f"{key}:{item}", parent=item_node)

        if please_add:
            if isinstance(item, str):
                anytree.Node(f"{key}:{item}", parent=item_node)
            elif isinstance(item, Number):
                anytree.Node(f"{key}:{item}", parent=item_node)
            elif isinstance(item, bool):
                anytree.Node(f"{key}:{item}", parent=item_node)
            elif isinstance(item, dict):
                anytree.Node(f"{key}:{item}", parent=item_node)
            elif isinstance(item, list):
                anytree.Node(f"{key}:{item}", parent=item_node)
            else:
                # catching unexpected configuration items.
                msg = f"Unable to build tree for item: {key}: {item}"
                logging.warning(msg)


def convert_exp_def_to_string(
        exp_def: Union[FactoryBlueprint, dict, ComponentDef]
) -> str:
    """Converts an experiment definition to a string

    :param exp_def: The experiment/blueprint
    :type blueprint: FactoryBlueprint
    :return: the tree as a string
    :rtype: str
    """
    root_node = anytree.Node(exp_def["group_label"])
    build_tree(blueprint=dict(exp_def), parent=root_node)
    return anytree.RenderTree(root_node, maxlevel=None).by_attr("name")
    # return anytree.RenderTree(root_node, maxlevel=5)
