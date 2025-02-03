"""Scenario Runner

Versions:
v 0.1
- mvp

References:
-

TODO:

1.0 consider moving functions to another file in module
2.0 consider moving default components/blueprints to toml??

Defects:

1.0

Test
py -m pytest test/scenario/test_scenario_manager.py
"""

import importlib
import os
import sys
import logging
from typing import Literal, Union, Any
import toml
import yaml
from adgtk.common import (
    FactoryBlueprint,
    ComponentDef,
    InvalidScenarioState,
    convert_exp_def_to_string,
    FolderManager)
from adgtk.factory import (
    ObjectFactory,
    DuplicateFactoryRegistration)
from adgtk.journals import ExperimentJournal
from adgtk.instrumentation import measurement_register_list
from .base import Scenario, SCENARIO_GROUP_LABEL


# ----------------------------------------------------------------------
# Module configs
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------

def save_blueprint_to_file(
    blueprint: FactoryBlueprint,
    filename: str,
    blueprint_dir: str,
    blueprint_format: Literal["toml", "yaml"]
) -> None:
    """Formats and saves the blueprint to disk.

    Args:
        blueprint (FactoryBlueprint): The blueprint
        blueprint_dir (str): The folder to save blueprint to
        filename (str): The file to save. if no extension given it will
            add the appropriate extension, ex: file.yaml or file.toml
        format (Literal["toml","yaml"]): The format

    Raises:
        NotImplementedError: TODO Dev
    """
    # ensure folder exists
    os.makedirs(name=blueprint_dir, exist_ok=True)

    # format the output
    file_w_ext = filename
    if blueprint_format == "toml":
        if not filename.lower().endswith(".toml"):
            file_w_ext = f"{filename}.toml"
        else:
            file_w_ext = filename
        file_w_path = os.path.join(blueprint_dir, file_w_ext)
        with open(file_w_path, "w", encoding="utf-8") as outfile:
            toml.dump(blueprint, outfile)
    elif blueprint_format == "yaml":
        if not filename.lower().endswith(".yaml"):
            file_w_ext = f"{filename}.yaml"
        else:
            file_w_ext = filename

        file_w_path = os.path.join(blueprint_dir, file_w_ext)
        with open(file_w_path, "w", encoding="utf-8") as outfile:
            yaml.safe_dump(
                blueprint,
                outfile,
                default_flow_style=False,
                sort_keys=False)
    else:
        raise NotImplementedError("TODO: use the setting default!")

    # save to disk
    file_w_path = os.path.join(blueprint_dir, file_w_ext)


# ----------------------------------------------------------------------
# Management : running experiments and creating blueprints
# ----------------------------------------------------------------------

class ScenarioManager:
    """Manages all aspects of a scenario."""

    def __init__(
        self,
        blueprint_dir: str = "blueprints",
        experiment_definition_dir: str = "experiment-definition",
        settings_file_override: Union[str, None] = None,
        load_base: bool = True,
        load_user_modules: Union[list, None] = None,
    ) -> None:
        if load_user_modules is None:
            load_user_modules = []

        self.blueprint_dir = blueprint_dir
        self.experiment_definition_dir = experiment_definition_dir
        self.active_scenario: Union[Scenario, None] = None
        self.settings_file_override = settings_file_override
        self.load_user_modules_errs: list[str] = []
        # setup internal objects
        self._journal = ExperimentJournal()
        self._factory = ObjectFactory(
            journal=self._journal,
            settings_file_override=settings_file_override)
        self.active_scenario_name = "SCENARIO-MGR-NOT-SET"

        # Load the core such as Measurement Engine
        self._load_core_components()

        for user_module in load_user_modules:
            self._load_user_components(user_module)

    def __str__(self):
        report = "Scenario Manager\n"
        report += "================\n"
        report += f"{self._factory}"
        return report

    def group_report(self, group_label: str) -> str:
        """Creates a report string for a group. Primary use is in the
        command line interface.

        :param group_label: The group to filter on
        :type group_label: str
        :return: a report showing the group members
        :rtype: str
        """
        return self._factory.group_report(group_label)

    def _load_experiment_from_file(self, file_w_path: str) -> ComponentDef:
        """Loads an experiment definition from disk

        Args:
            file_w_path (str): The file containing the definition

        Raises:
            NotImplementedError: More work needed here
            FileNotFoundError: Unable to load the file

        Returns:
            ComponentDef: The settings for the experiment
        """

        # current_directory = os.getcwd()
        # print(f"Current Directory: {current_directory}")

        if os.path.exists(os.path.join(file_w_path)):
            with open(file_w_path, "r", encoding="utf-8") as infile:
                if file_w_path.lower().endswith(".toml"):
                    exp_def = toml.load(infile)
                elif file_w_path.lower().endswith(".yaml"):
                    exp_def = yaml.safe_load(infile)
                else:
                    msg = f"Unexpected file format for {file_w_path}"
                    logging.error(msg)
                    raise InvalidScenarioState(msg)
                if "comments" in exp_def:
                    start_msg = f"Starting: {file_w_path}"
                    logging.info(start_msg)
                    logging.info(exp_def["comments"])
                    self._journal.add_entry(
                        entry_type="comment",
                        component="scenario",
                        entry_text=exp_def["comments"])
                if "configuration" in exp_def:
                    return exp_def["configuration"]

        elif os.path.exists(file_w_path):
            raise NotImplementedError("DEV needed")
        else:
            raise FileNotFoundError(
                f"Unable to find experiment definition: {file_w_path}")

        # should not happen.
        return ComponentDef(
            type_label="error",
            group_label="error",
            arguments={})

    def _load_user_components(self, user_module: str) -> int:
        """Loads a user module and the registers the components from the
        register_list.

        :param user_module: The module to load
        :type user_module: str
        :raises ModuleNotFoundError: user module not found
        :raises AttributeError: register_list not found
        :return: The number of items registered
        :rtype: int
        """
        count = 0

        # ensures the cwd is loaded to the path so that the module the
        # user wants to load is found. W/out this you get a module not
        # found error.
        if sys.path[0] != '':
            sys.path.insert(0, '')
            # uncomment to troubleshoot
            # print(sys.path)

        # moving to an improved design where we skip this step so as to
        # fail with an error instead of gracefully skipping.

        # user_spec = importlib.util.find_spec(user_module)
        # if user_spec is None:
        #     msg = f"Module {user_module} not found at {os.getcwd()}"
        #     print(msg)
        #     logging.error(msg)
        #     return 0

        # attempt to load the module
        try:
            # loaded_module = importlib.import_module(user_spec.name)
            loaded_module = importlib.import_module(user_module)
            msg = f"Loaded {user_module}"
            logging.info(msg)
        except ModuleNotFoundError as e:
            # moved to not using user_spec so that the user can get a
            # better error message than a default.
            print("USER MODULE ERRORS")
            print("==================")
            msg = f"ERROR: User Module [{user_module}]"
            print(msg)
            raise e

            # TODO: cleanup once sure this is not needed
            # should not happen as we found the spec
            msg = f"ERROR: User Module [{user_module}] not found"
            self.load_user_modules_errs.append(msg)
            logging.error(msg)
            print("")
            sys.exit(1)
        try:
            user_register_list = loaded_module.register_list
        except AttributeError:
            msg = f"unable to find register_list in {user_module}"
            logging.error(msg)
            print("")
            self.load_user_modules_errs.append(msg)
            return 0

        for creator in user_register_list:
            self.register(creator=creator)
            count += 1

        return count

    def _load_factories(
        self,
        creator: Any,
        group_label_override: Union[str, None] = None,
        type_label_override: Union[str, None] = None
    ) -> None:

        # Load component
        self._factory.register(
            group_label_override=group_label_override,
            type_label_override=type_label_override,
            creator=creator)

    def _load_core_components(self):
        """Loads components that should be registered regardless. For
        example components that perform measurements."""

        # for measurements
        for creator in measurement_register_list:
            self.register(creator=creator)

    def load_experiment(self, experiment_name: str) -> None:
        """Loads and experiment

        :param experiment_name: The name of the file
        :type experiment_name: str
        """
        file_w_path = os.path.join(
            self.experiment_definition_dir, experiment_name)
        alt1 = f"{file_w_path}.toml"
        alt2 = f"{file_w_path}.yaml"
        exp_def: Union[ComponentDef, None] = None
        if os.path.exists(file_w_path):
            msg = f"Loaded {experiment_name}"
            logging.info(msg)
            exp_def = self._load_experiment_from_file(file_w_path)
        elif os.path.exists(alt1):
            msg = f"expanded from {experiment_name} to {alt1} and loaded"
            logging.info(msg)
            exp_def = self._load_experiment_from_file(alt1)
        elif os.path.exists(alt2):
            msg = f"expanded from {experiment_name} to {alt2} and loaded"
            logging.info(msg)
            exp_def = self._load_experiment_from_file(alt2)
        else:
            msg = f"Unable to load experiment: {experiment_name}"
            logging.error(msg)
            raise InvalidScenarioState(msg)

        # folders should not have the extension so it is stripped
        # It should also be lower case so as to keep things predictable
        experiment_name = experiment_name.lower()
        if experiment_name.endswith(".toml") or \
                experiment_name.endswith(".yaml"):
            experiment_name = experiment_name[:-5]
        self.active_scenario_name = experiment_name

        # update folder manager so that objects created know where to
        # write their files/updates/etc to.
        self._factory.update_folder_manager(name=experiment_name)
        # And update the Journal(s)
        exp_tree = convert_exp_def_to_string(exp_def=exp_def)
        self._journal.add_entry(
            entry_text=exp_tree,
            entry_type="scenario_def",
            include_timestamp=False)

        # and then create the scenario
        self.active_scenario = self._factory.create(exp_def)

    def preview_experiment(self, to_console: bool = True) -> None:
        """Initiates the scenario preview.
        :param to_console: Print the tree to the console
        :type to_console: bool
        :raises InvalidScenarioState: no scenario loaded
        """
        folder_mgr = FolderManager(
            name=self.active_scenario_name,
            clear_and_rebuild=False)

        if self.active_scenario is not None:
            self._journal.generate_preview(
                experiment_name=self.active_scenario_name,
                experiment_folder=folder_mgr.base_folder)

        else:
            msg = "No loaded scenario to preview"
            logging.error(msg)
            raise InvalidScenarioState(msg)

    def run_experiment(self) -> None:
        """Initiates the scenario run

        :raises InvalidScenarioState: no scenario loaded
        """
        if self.active_scenario is not None:
            self.active_scenario.execute(self.active_scenario_name)
        else:
            msg = "No loaded scenario to run"
            logging.error(msg)
            raise InvalidScenarioState(msg)

        # And report
        folder_mgr = FolderManager(
            name=self.active_scenario_name,
            clear_and_rebuild=False)

        self._journal.generate_report(
            experiment_name=self.active_scenario_name)

    def build_blueprint(
        self,
        type_label: str,
        group_label: str = SCENARIO_GROUP_LABEL
    ) -> None:
        """Triggers a save to disk for a blueprint.

        :param type_label: The type.
        :type type_label: str
        :param group_label: The group. Defaults to SCENARIO_GROUP_LABEL.
        :type group_label: str, optional
        """
        blueprint: FactoryBlueprint = self._factory.get_blueprint(
            group_label=group_label,
            type_label=type_label)

        if blueprint is not None:
            save_blueprint_to_file(
                blueprint=blueprint,
                blueprint_dir=self.blueprint_dir,
                blueprint_format="toml",
                filename=f"{group_label}.{type_label}")

    def register(
        self,
        creator: Any,
        override_group_label: Union[str, None] = None,
        override_type_label: Union[str, None] = None
    ) -> None:
        """Registers an object to the internal factories.

        :param creator: The component to build
        :type creator: Any (implements FactoryImplementable)
        :param override_group_label: Override the group label defined in creator. Defaults to None.
        :type override_group_label: Union[str, None], optional
        :param override_type_label: Override the type label defined in creator. Defaults to None.
        :type override_type_label: Union[str, None], optional
        :param set_default_blueprint: Use the blueprint as the default for this group. Defaults to False.
        :type set_default_blueprint: bool, optional
        """
        type_label: Union[str, None] = None
        group_label: Union[str, None] = None
        # load from component if not overridden

        # group
        if override_group_label is None:
            try:
                group_label = creator.blueprint["group_label"]
            except AttributeError as e:
                print("ERROR: Invalid creator. Creator dump:")
                print(creator)
                print("ERROR Raises:")
                raise e
        else:
            group_label = override_group_label

        # type
        if override_type_label is None:
            type_label = creator.blueprint["type_label"]
        else:
            type_label = override_group_label

        # and if set
        if isinstance(type_label, str) and isinstance(group_label, str):
            try:
                self._load_factories(
                    group_label_override=group_label,
                    type_label_override=type_label,
                    creator=creator)
            except DuplicateFactoryRegistration:
                err_msg = "Duplicate Registration attempted for "\
                    f"{group_label}.{type_label}"

                logging.error(err_msg)
        else:
            msg = "Unable to process blueprint"
            logging.error(msg)
            raise InvalidScenarioState(msg)

    def registry_listing(
        self,
        group_label: Union[str, None] = None
    ) -> list[str]:
        """Lists factory entries. if no group listed it returns groups,
        else if a group is entered it returns all types in that group.

        :param group_label: A group label, defaults to None
        :type group_label: Union[str, None], optional
        :return: A listing of types in a group or all groups
        :rtype: list[str]
        """
        return self._factory.registry_listing(group_label)

    def get_blueprint(
        self,
        type_label: str,
        group_label: str = SCENARIO_GROUP_LABEL
    ) -> FactoryBlueprint:
        """Triggers a save to disk for a blueprint.

        :param type_label: The type.
        :type type_label: str
        :param group_label: The group. Defaults to SCENARIO_GROUP_LABEL.
        :type group_label: str, optional
        """
        return self._factory.get_blueprint(
            group_label=group_label, type_label=type_label)

    def get_description(self, group_label: str, type_label: str) -> str:
        """Gets the description of a component that is registed.

        :param group_label: The group the component is a member of
        :type group_label: str
        :param type_label: the member in the group
        :type type_label: str
        :return: a string of the description as defined in the class.
        :rtype: str
        """
        return self._factory.get_description(
            group_label=group_label,
            type_label=type_label)
