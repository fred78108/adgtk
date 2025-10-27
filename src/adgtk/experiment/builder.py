"""Builds and manages experiments via a CLI UX

TODO: take advantage of _working_on
"""
# setup logfile for this and sub-modules
from adgtk.utils import create_logger

import os
from typing import Optional, Union
import yaml
from adgtk.utils import get_user_input, get_more_ask
import adgtk.factory.component as factory
from adgtk.factory.structure import BlueprintQuestion
from adgtk.utils import get_user_input
from adgtk.experiment.structure import (
    EXPERIMENT_LABEL,
    SCENARIO_LABEL,
    AttributeEntry,
    ExperimentDefinition)
import adgtk.tracking.project as project_manager
# ----------------------------------------------------------------------
# Module logging
# ----------------------------------------------------------------------

# Set up module-specific logger
_logger = create_logger(
    "adgtk.builder.log",
    logger_name=__name__,
    subdir="framework"
)

# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------
# public
MIN_LINE_LENGTH = 50

# private
_working_on: list[str] = []        # so we can walk a tree
# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _get_user_selection_from_group(
    group: str,
    user_prompt: str,
    tags: Optional[Union[str, list[str]]] = None,
) -> str:
    """Uses a CLI based experience to list options for the user and
    then via the get_user_input collects the user selection. it then
    returns the associated factory_id of this selection

    :param user_prompt: The prompt to the user
    :type user_prompt: str
    :param group: The group to search for
    :type group: str
    :raises ValueError: Unexpected get_user_input value
    :return: the factory_id of the user selection
    :rtype: str
    """
    entries = factory.list_entries(group=group, tags=tags)

    title = f"Group: {group}:"
    line_length = max(len(title), MIN_LINE_LENGTH)
    print(title)
    print("-"*line_length)
    choices: list[str] = []
    idx_choices = []
    for idx, entry in enumerate(entries):
        print(f"  {idx} : {entry.factory_id:<15} | {entry.summary:50}")
        choices.append(entry.factory_id)
        choices.append(str(idx))
        idx_choices.append(entry.factory_id)
    choice = get_user_input(
        requested="str",
        user_prompt=user_prompt,
        choices=choices,
        allow_whitespace=False)

    # catch numbers.
    # if choice in idx_choices:
    is_index = False
    try:
        _ = int(choice)
        is_index = True
    except ValueError:
        pass

    if is_index:
        # need to convert and return
        if isinstance(choice, str):
            idx = int(choice)
        elif isinstance(choice, int):
            # should really never happen but again, safety
            idx = choice
        else:
            raise ValueError("Unexpected get_user_input value")

        return idx_choices[idx]

    if isinstance(choice, str) and factory.entry_exists(choice):
        return choice

    msg = f"Unexpected get_user_input value: {choice}"
    _logger.error(msg)
    print(f"ERROR: {msg}")
    raise ValueError(msg)


def _perform_interview(
    interview: list[BlueprintQuestion]
) -> list[AttributeEntry]:
    """Performs an interview by iterating through a series of questions.

    :param interview: _description_
    :type interview: list[BlueprintQuestion]
    :raises ValueError: Unexpected combinations
    :return: A list of attributes for init via a factory
    :rtype: list[AttributeEntry]
    """
    item_being_built = _working_on[-1]  # set at _expand

    # not expected but just in case
    if len(interview) == 0:
        raise ValueError("Expand requested with an empty interview")

    attributes = []
    for entry in interview:
        # placeholders
        value: Union[AttributeEntry, str, float, int, bool, list] = ""
        factory_id = None
        if entry.entry_type == "expand":
            if entry.group is None:
                raise ValueError("group must be defined for type expand")
            group_name = entry.group

            if not factory.group_exists(group_name):
                msg = (f"unknown group {group_name}. Valid groups are: "
                       f"{factory.get_group_names()}")
                _logger.error(msg)
                raise ValueError(msg)

            factory_id = _get_user_selection_from_group(
                user_prompt=entry.question,
                group=group_name)
            value = _expand(factory_id=factory_id, attribute=entry.attribute)
        elif entry.entry_type == "ml-string":
            value = get_user_input(
                user_prompt=entry.question,
                requested="ml-str"
            )
        elif entry.entry_type == "list[expand]":
            # get the minimum values
            if entry.group is None:
                raise ValueError("group must be defined for type expand")

            group_name = entry.group
            value = []
            while get_more_ask():
                factory_id = _get_user_selection_from_group(
                    user_prompt=entry.question,
                    group=group_name)

                exp_value = _expand(factory_id=factory_id,
                                    attribute=entry.attribute)
                value.append(exp_value)

        elif entry.choices is not None and len(entry.choices) > 0:
            # handle all choice based calls here
            if entry.entry_type == "bool":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="bool",
                    configuring=item_being_built,
                    choices=entry.choices
                )
            elif entry.entry_type == "str":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="str",
                    configuring=item_being_built,
                    choices=entry.choices
                )
            elif entry.entry_type == "int":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="int",
                    configuring=item_being_built,
                    choices=entry.choices
                )
            elif entry.entry_type == "float":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="float",
                    configuring=item_being_built,
                    choices=entry.choices
                )
            else:
                raise ValueError(
                    "Unexpected requested combination with choices")
        else:
            if entry.entry_type == "bool":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="bool",
                    configuring=item_being_built
                )
            elif entry.entry_type == "str":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="str",
                    configuring=item_being_built
                )
            elif entry.entry_type == "int":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="int",
                    configuring=item_being_built
                )
            elif entry.entry_type == "float":
                value = get_user_input(
                    user_prompt=entry.question,
                    requested="float",
                    configuring=item_being_built
                )
        if isinstance(value, str) and len(value) == 0:
            raise ValueError("Value not captured")

        # now update the list
        if isinstance(value, AttributeEntry):
            attributes.append(value)
        else:
            attributes.append(AttributeEntry(
                attribute=entry.attribute,
                init_config=value,
                factory_id=factory_id
            ))

    return attributes


def _expand(factory_id: str, attribute: str) -> AttributeEntry:
    """Expands an attribute

    :param factory_id: The factory ID to expand
    :type factory_id: str
    :param attribute: The label of the attribute
    :type attribute: str
    :raises ValueError: unknown factory_id
    :return: The collected configuration
    :rtype: AttributeEntry
    """
    global _working_on

    if not factory.entry_exists(factory_id):
        msg = f"Requesting to expand an unknown factory_id {factory_id}"
        _logger.error(msg)
        raise ValueError(msg)
    interview = factory.get_interview(factory_id=factory_id)

    if len(interview) == 0:
        factory_init = False
        init_config: Optional[list] = None
        if attribute == SCENARIO_LABEL:
            # scenarios are unique at the root and must be created
            factory_init = True
            init_config = []

        return AttributeEntry(
            attribute=attribute,
            factory_id=factory_id,
            init_config=init_config,
            factory_init=factory_init
        )

    _working_on.append(factory_id)

    return_value = AttributeEntry(
        factory_id=factory_id,
        attribute=attribute,
        init_config=_perform_interview(interview=interview),
        factory_init=True
    )

    _working_on.pop()
    return return_value


# ----------------------------------------------------------------------
# Public
# ----------------------------------------------------------------------
def create_experiment_name_ux() -> str:
    user_prompt = "Do you want the system to automatically create a name"
    auto_create = get_user_input(
        user_prompt=user_prompt,
        requested="str",
        choices=["yes", "no", "y", "n"],
        allow_whitespace=False,
        default_selection="yes"
    )
    if not isinstance(auto_create, str):
        msg = "create_experiment_name_ux get_user_input failure"
        _logger.error(msg)
        raise ValueError("Unexpected get_user_input")

    if auto_create.lower().startswith("y"):
        cur_prefix_options = project_manager.get_prefix_list()
        if len(cur_prefix_options) > 0:
            print(f"Existing prefixes:")
            for entry in cur_prefix_options:
                print(f" - {entry}")

        helper_str = ("if you want to create a new prefix simply "
                      "enter one here")
        prefix = get_user_input(
            user_prompt="What prefix do you want to use",
            requested="str",
            allow_whitespace=False,
            helper=helper_str,
            min_characters=1,
            max_characters=20)
        if not isinstance(prefix, str):
            msg = "create_experiment_name_ux get_user_input failure"
            _logger.error(msg)
            raise ValueError("Unexpected get_user_input")
        # return here
        return project_manager.generate_experiment_name(
            prefix=prefix, update_next="minor")

    name = get_user_input(
        user_prompt="Please enter an experiment name",
        requested="str",
        allow_whitespace=False)
    if not isinstance(name, str):
        msg = "create_experiment_name_ux get_user_input failure"
        _logger.error(msg)
        raise ValueError("Unexpected get_user_input")

    return name


# TODO: add tags, etc.
def build_experiment(
    name: Optional[str] = None,
    scenario_factory_id: Optional[str] = None,
    tags: Optional[str] = None
) -> None:

    if name is None:
        name = create_experiment_name_ux()

    description = get_user_input(
        user_prompt="Experiment description",
        requested="str",
        max_characters=80,
        min_characters=1
    )

    if scenario_factory_id is not None:
        # check first
        if not factory.entry_exists(scenario_factory_id):
            print("WARNING: Scenario with that factory_id does not exist.")
        scenario_factory_id = None

    if scenario_factory_id is None:
        scenario_factory_id = _get_user_selection_from_group(
            group="scenario",
            user_prompt="Please select the scenario you wish to build",
            tags=tags)

    scenario_config = _expand(scenario_factory_id, attribute=SCENARIO_LABEL)

    if not isinstance(name, str):
        raise ValueError("Unexpected return for value")
    if not isinstance(description, str):
        raise ValueError("Unexpected return for description")

    exp_def = ExperimentDefinition(
        name=name,
        attribute=EXPERIMENT_LABEL,
        description=description,
        init_config=scenario_config,
        factory_init=True
    )

    filename = f"{name}.yaml"
    file_w_path = os.path.join("blueprints", filename)
    with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
        yaml.safe_dump(
            exp_def.model_dump(),
            outfile,
            default_flow_style=False,
            sort_keys=False)

    _logger.info(f"Created experiment file: {file_w_path}")
