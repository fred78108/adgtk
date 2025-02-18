"""Summary goes here.

Versions:
v 0.1
- mvp

References:
-

TODO:

1.0 Consider moving to the factory module?

Defects:

1.0

Test
py -m pytest -s test/factory/test_component_factory.py
"""

from __future__ import annotations
import logging
import os
import sys
import toml
import yaml
from typing import Any, Union, List, TYPE_CHECKING
from adgtk.journals import ExperimentJournal
from adgtk.common import FactoryBlueprint, ComponentDef
from adgtk.common import FolderManager
from adgtk.utils import create_line, load_settings, prepare_string
from .base import DuplicateFactoryRegistration, FactoryImplementable


# ----------------------------------------------------------------------
# Module Options
# ----------------------------------------------------------------------
# used for development and troubleshooting.
LOG_FACTORY_CREATE_OF_FULL_FACTORY_BLUEPRINTS = True

README_TEXT = """BLUEPRINT_DIR
=============
This folder and its contents are re-created everytime the factory is loaded.

IMPORTANT: Do not edit any file in this folder as any changes will be lost.

The purpose of this folder is to provide you with all the blueprints if you want
to craft your experiment by hand. You can of course always use:

adgtk-manager -b 

which will provide you an interactive experience for crafting your experiment.

Note: The current version only supports blueprints to toml. Future versions may support additional versions.
"""
# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


class ObjectFactory:
    """A dynamic factory that creates and manages groups and types"""

    def __init__(
        self,
        journal: Union[ExperimentJournal, None] = None,
        factory_name: str = "Object Factory",
        settings_file_override: Union[str, None] = None,
        use_formatting: bool = True,
        dark_mode: bool = False,
        create_blueprint_files: bool = False
    ) -> None:
        self.factory_name = factory_name
        # A common place to establish the folder manager
        # should be set before creation. So it is set at experiment run.
        # this way an Agent if designed can run different experiments
        # in parallel or series.
        self.settings_file_override = settings_file_override
        self.folder_manager: FolderManager

        self.create_blueprint_files = create_blueprint_files

        if journal is None:
            logging.warning("Using default journal.")
            self.journal = ExperimentJournal()

        self._journal: Union[ExperimentJournal, None] = None
        self._registry: dict[str, dict[str, FactoryImplementable]] = {}
        self.registered_count = 0

        self.settings = load_settings()
        # formatting
        self.dark_mode = dark_mode
        self.use_formatting = use_formatting
        self.terminal_css = self.settings.terminal["css"]
        self.file_format = self.settings.default_file_format
        self.blueprint_dir = self.settings.blueprint_dir

        # Blueprint dir preperation
        if not os.path.exists(self.blueprint_dir):
            os.makedirs(self.blueprint_dir)

        readme_file = os.path.join(self.blueprint_dir, "README.md")
        with open(file=readme_file, mode="w", encoding="utf-8") as outfile:
            outfile.write(README_TEXT)

    def __len__(self) -> int:
        return self.registered_count

    def update_folder_manager(self, name: str) -> None:
        self.folder_manager = FolderManager(
            name=name,
            settings_file_override=self.settings_file_override)

    def __str__(self) -> str:
        title = "Object Factory report"
        if self.use_formatting:
            title = prepare_string(
                text=title, css="emphasis", terminal_css=self.terminal_css)
        report = ""
        report += f"{title}\n"
        report += "---------------------\n"
        for key, group in sorted(self._registry.items()):
            if self.use_formatting:
                key = prepare_string(
                    text=key, css="build", terminal_css=self.terminal_css)
            report += f"Group-label: {key}\n"
            for item, _ in sorted(group.items()):
                report += f"  - type: {item}\n"

        return report

    def group_report(self, group_label: str) -> str:
        """Creates a report string for a group. Primary use is in the
        command line interface.

        :param group_label: The group to filter on
        :type group_label: str
        :return: a report showing the group members
        :rtype: str
        """

        title = f"Object Factory report for group1: {group_label}"
        if self.use_formatting:
            title = prepare_string(
                text=title, css="emphasis", terminal_css=self.terminal_css)

        line = create_line(title, "=")
        report = title
        report += f"\n{line}\n"
        if group_label not in self._registry:
            report = f"ERROR: No group {group_label} found\n\n"
            if self.use_formatting:
                report = prepare_string(
                    text=report, css="error", terminal_css=self.terminal_css)
            report += "Valid groups are:\n"
            report += create_line("", char=".", modified=17)
            report += "\n"
            for key in self._registry.keys():
                report += f"  - {key}\n"
            return report

        for item, _ in sorted(self._registry[group_label].items()):
            report += f"  - type: {item}  | "
            report += f" {self._registry[group_label][item].description}\n"

        return report

    def _save_blueprint(self, blueprint: FactoryBlueprint) -> None:
        file_w_path = os.path.join(
            self.blueprint_dir,
            f"{blueprint['group_label']}.{blueprint['type_label']}")

        file_w_path += ".toml"
        with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
            toml.dump(blueprint, outfile)

        return None

        # issues with yaml safe_dump and blueprints. Future work may
        # research alternative options for writing yaml to disk for the
        # blueprint. For now, defaulting to toml only. This is also an
        # edge case. Most users will hopefully use the CLI wizard. This
        # option may therefore be removed in future releases.
        if self.file_format == "toml":
            file_w_path += ".toml"
            with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
                toml.dump(blueprint, outfile)
        elif self.file_format == "yaml":
            file_w_path += ".yaml"
            with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
                try:
                    yaml.safe_dump(blueprint,
                                   outfile,
                                   default_flow_style=False,
                                   sort_keys=False)
                except yaml.representer.RepresenterError:
                    print(f"Failed to save: {blueprint['type_label']}")

    def register(
        self,
        creator: Any,
        group_label_override: Union[str, None] = None,
        type_label_override: Union[str, None] = None,
        log_entry: bool = True
    ) -> None:
        """Register an object.

        Args:
        :param group_label_overide: The group to which it belongs
        :type group_label_overide: str
        :param type_label_overide: the type within that group
        :type type_label_overide: str
        :param creator: The class to create
        :type creator: Any (implements Protocol FactoryImplementable)
        :raises DuplicateFactoryRegistration: The type label exists
        :raises TypeError: creator does not implement protocol
        """

        group_label: str = creator.blueprint["group_label"]
        type_label: str = creator.blueprint["type_label"]

        if group_label_override is not None:
            group_label = group_label_override
        if type_label_override is not None:
            type_label = type_label_override

        # Safety check
        if not isinstance(creator, FactoryImplementable):
            msg = f"Creator {creator} does not Implement FactoryImplementable"

            raise TypeError(msg)
        if group_label not in self._registry:
            self._registry[group_label] = {}

        # get groups
        c_group = self._registry[group_label]

        # and add to groups
        if type_label in c_group:
            raise DuplicateFactoryRegistration

        c_group[type_label] = creator

        # and journal?
        if self._journal is not None and log_entry:
            self._journal.add_factory_registration(
                factory=self.factory_name,
                group_label=group_label,
                type_label=type_label)

        # and create a local file should the user want to create by hand
        if self.create_blueprint_files:
            self._save_blueprint(creator.blueprint)

        self.registered_count += 1

    def unregister(self, group_label: str, type_label: str) -> None:
        """Unregisters a type from a group

        :param group_label: The group to which it belongs
        :type group_label: str
        :param type_label: the type within that group
        :type type_label: str
        :raises KeyError: Group label not found
        """
        if group_label in self._registry:
            c_group = self._registry[group_label]
            if type_label in c_group:
                c_group.pop(type_label, None)
        else:
            raise KeyError("Group label not found")

        self.registered_count -= 1

    def get_blueprint(
        self,
        group_label: str,
        type_label: str
    ) -> FactoryBlueprint:
        """Gets a blueprint for a component creator

        :param group_label: the group label
        :type group_label: str
        :param type_label: The type label
        :type type_label: str
        :raises KeyError: Group not found
        :raises KeyError: Type not found
        :return: The component blueprint
        :rtype: FactoryBlueprint
        """

        if group_label in self._registry:
            c_group = self._registry[group_label]
        else:
            raise KeyError("Group label not found")

        if type_label in c_group:
            component = c_group[type_label]
            return component.blueprint

        raise KeyError("Type label not found")

    def create(self, component_def: ComponentDef) -> Any:
        """creates a component based on a blueprint

        :param component_def: The item to build
        :type component_def: ComponentDef
        :raises KeyError: unable to find the object
        :return: A created object using the blueprint
        :rtype: Any
        """

        try:
            if component_def is None:
                raise ValueError("Missing component definition")

            if "group_label" not in component_def:
                msg = "Invalid component definition, missing group_label"
                raise KeyError(msg)

            if "type_label" not in component_def:
                msg = "Invalid component definition, missing group_label"
                raise KeyError(msg)

            if component_def["group_label"] not in self._registry:
                msg = f'{component_def["group_label"]} not in factory. '\
                      "Unable to create"
                logging.error(msg)
                print(msg)
                sys.exit(1)
            g_label = component_def["group_label"]
            t_label = component_def["type_label"]
            component_create = self._registry[g_label][t_label]
            # group = self._registry[component_def["group_label"]]
            # print(f"GROUP: {group} | {component_def['group_label']}")
            # if group[component_def["type_label"]] not in group:
            #    msg = f'{component_def["group_label"]}| '\
            #          f'{component_def["type_label"]} not in factory. '\
            #          "Unable to create"
            #    logging.error(msg)
            #    print(msg)
            #    sys.exit(1)

            # component_create: FactoryImplementable = \
            #    group[component_def["type_label"]]
        except KeyError as e:
            msg = "No valid creator found at: "\
                  f"{component_def['group_label']}:{component_def['type_label']}"
            logging.error(e)
            raise KeyError(e) from e

        # do we init w/factory & journal, factory only, or none?
        factory_flag = component_create.features.object_factory
        j_flag = component_create.features.experiment_journal
        if factory_flag and j_flag:
            if LOG_FACTORY_CREATE_OF_FULL_FACTORY_BLUEPRINTS:
                g_label = component_def["group_label"]
                t_label = component_def["type_label"]
                msg = f"creating {g_label}:{t_label}"
                print(msg)
                logging.info(msg)
            if not TYPE_CHECKING:
                # bit of a hack to work around MyPy and ABC
                try:
                    new_component = component_create(
                        factory=self,
                        journal=self._journal,
                        **component_def["arguments"])
                except TypeError as e:
                    msg = f"Invalid settings for {g_label}|{t_label}. "\
                          "Unable to create using the factory. See log for "\
                          "more details."
                    logging.error(msg)
                    logging.error(e)
                    raise TypeError(msg) from e

                return new_component

        elif factory_flag:
            if not TYPE_CHECKING:
                # bit of a hack to work around MyPy and ABC
                try:
                    new_component = component_create(
                        factory=self,
                        **component_def["arguments"])
                except TypeError as e:
                    msg = f"Invalid settings for {g_label}|{t_label}. "\
                          "Unable to create using the factory. See log for "\
                          "more details."
                    logging.error(msg)
                    logging.error(e)
                    raise TypeError(msg) from e

                return new_component

        elif j_flag:
            if not TYPE_CHECKING:
                # bit of a hack to work around MyPy and ABC
                try:
                    new_component = component_create(
                        journal=self._journal,
                        **component_def["arguments"])
                except TypeError as e:
                    msg = f"Invalid settings for {g_label}|{t_label}. "\
                          "Unable to create using the factory. See log for "\
                          "more details."
                    logging.error(msg)
                    logging.error(e)
                    raise TypeError(msg) from e

                return new_component

        else:
            if not TYPE_CHECKING:
                # bit of a hack to work around MyPy and ABC
                try:
                    new_component = component_create(
                        **component_def["arguments"])
                except TypeError as e:
                    msg = f"Invalid settings for {g_label}|{t_label}. "\
                          "Unable to create using the factory. See log for "\
                          "more details."
                    logging.error(msg)
                    logging.error(e)
                    raise TypeError(msg) from e

                return new_component

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
        if group_label is None:
            return list(self._registry.keys())
        else:
            try:
                group = self._registry[group_label]
                return list(group.keys())
            except KeyError as e:
                msg = f"Invalid group_label: {group_label} not found."
                raise KeyError(msg) from e
