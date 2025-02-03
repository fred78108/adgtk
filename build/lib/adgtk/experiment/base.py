"""Builds and manages experiments"""
import logging
import sys
import os
from typing import Union, cast, Literal
import toml
import yaml
from adgtk.factory import InvalidBlueprint
from adgtk.common import (
    FactoryBlueprint,
    ExperimentDefinition,
    ArgumentSetting,
    ListArgumentSetting,
    ArgumentType,
    convert_exp_def_to_string)
from adgtk.scenario import ScenarioManager
from adgtk.common import (
    DEFAULT_DATA_DIR,
    DEFAULT_SETTINGS,
    DEFAULT_FILE_FORMAT)
from adgtk.utils import (
    string_to_bool,
    create_line,
    prepare_string,
    DEFAULT_TERMINAL_CSS,
    TerminalCSS,
    load_settings)



class ExperimentBuilder():
    """Used to build experiments"""

    def __init__(
        self,
        scenario_manager: Union[ScenarioManager, None] = None,
        settings_file_override: Union[str, None] = None,
        use_formatting: bool = True,
        dark_mode: bool = False,
    ):

        # Setup folder specs, etc
        self.terminal_css: TerminalCSS = DEFAULT_TERMINAL_CSS
        self.data_dir: str = DEFAULT_DATA_DIR
        self.file_format: Literal["toml", "yaml"] = DEFAULT_FILE_FORMAT
        try:
            settings = load_settings(file_override=settings_file_override)
            # load from settings
            self.data_dir = settings.experiment["data_dir"]
            self.terminal_css = settings.terminal["css"]
            self.file_format = settings.default_file_format
        except FileNotFoundError:
            msg = "Missing and required settings file. Using defaults"
            logging.error(msg)

        # and establish the remaining
        self.dark_mode = dark_mode
        self.use_formatting = use_formatting
        self.experiment_definition_dir = settings.experiment["definition_dir"]
        self.scenario_manager: ScenarioManager
        if scenario_manager is None:
            self.scenario_manager = ScenarioManager(
                blueprint_dir="blueprints",
                experiment_definition_dir="experiment-def")
        else:
            self.scenario_manager = scenario_manager

    def get_registered(
        self,
        group: str,
        to_console: bool = True
    ) -> list:
        """Gets the type listing and if to_console prints to console as well

        :param manager: The scenario manager to work with
        :type manager: ScenarioManager
        :param group: The group to fetch
        :type group: str
        :param to_console: print to console?, defaults to True
        :type to_console: bool, optional
        :return: a list of valid types for this group
        :rtype: list
        """
        try:
            registered_types = self.scenario_manager.registry_listing(group)
        except KeyError:
            err_msg = prepare_string(
                text=f"!!! ERROR: group not found: {group}",
                css="error",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
            print(err_msg)
            print(self.scenario_manager)
            logging.error("Unable to locate group %s", group)
            sys.exit(1)
        if not to_console:
            return registered_types

        group_title = f"\n Registerd {group} types are :"
        line_list = ["."] * len(group_title)
        line = "".join(line_list)
        if self.use_formatting:
            group_title = prepare_string(
                text=group_title,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
        print(group_title)
        print(line)
        print()

        for idx, label in enumerate(registered_types):
            label_text = f"{idx}) {label}"
            if self.use_formatting:
                label_text = prepare_string(
                    text=label_text,
                    css="build",
                    terminal_css=self.terminal_css,
                    dark_mode=self.dark_mode)
            print(label_text)

        return registered_types

    def build_interactive(self):
        """Interactive building of an experiment"""
        exp_title = ". Experiment builder wizard ."
        line = create_line(exp_title, char=".")
        if self.use_formatting:
            exp_title = prepare_string(
                text=exp_title, css="emphasis")
            line = prepare_string(
                text=line,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
        print(line)
        print(exp_title)
        print(line)

        # uncomment to debug factory
        # print(self.scenario_manager._factory)

        # get the source scenario then pass to build_args for recursive
        # building of the experiment

        exp_name_input = "Name of experiment: "
        if self.use_formatting:
            exp_name_input = prepare_string(
                text=exp_name_input,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
        exp_name = input(exp_name_input)

        if len(exp_name) == 0:
            err_msg = "Warning. defaulting to 'example.`"
            if self.use_formatting:
                err_msg = prepare_string(
                    text=err_msg,
                    css="error",
                    terminal_css=self.terminal_css,
                    dark_mode=self.dark_mode)
            print(err_msg)

            exp_name = "example"

        # cleanup any whitespace
        exp_name = "".join(exp_name.split())
        comment_input = "Comments: "
        if self.use_formatting:
            comment_input = prepare_string(
                text=comment_input,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
        comments = input(comment_input)
        scenario_setting = ArgumentSetting(
            help_str="\nWhat scenario do you wish to construct from?",
            default_value="scenario",
            argument_type=ArgumentType.BLUEPRINT)
        exp_conf = self._proc_blueprint(
            setting=scenario_setting, to_console=True)
        experiment = ExperimentDefinition(
            configuration=exp_conf, comments=comments)
        preview = convert_exp_def_to_string(exp_conf)
        intro = f"\nExperiment preview for {exp_name}: "
        if self.use_formatting:
            preview = prepare_string(
                preview,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
            intro = prepare_string(
                text=intro,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
        print(intro)
        print(preview)
        file_w_path = "not-set"
        if self.file_format == "toml":
            file_w_path = os.path.join(
                self.experiment_definition_dir,
                f"{exp_name}.toml")
        elif self.file_format == "yaml":
            file_w_path = os.path.join(
                self.experiment_definition_dir,
                f"{exp_name}.yaml")
        else:
            msg = f"unknown format {self.file_format}. Reverting to yaml"
            logging.error(msg)
            self.file_format = "yaml"
            file_w_path = os.path.join(
                self.experiment_definition_dir,
                f"{exp_name}.yaml")

        save_intro = f"create file [{file_w_path}]: "
        if self.use_formatting:
            save_intro = prepare_string(
                text=save_intro,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
        save_as = input(save_intro)
        # take the default?
        if len(save_as) == 0:
            save_as = file_w_path

        with open(save_as, encoding="utf-8", mode="w") as outfile:
            if self.file_format == "toml":
                toml.dump(experiment, outfile)
            elif self.file_format == "yaml":
                yaml.safe_dump(
                    experiment,
                    outfile,
                    default_flow_style=False,
                    sort_keys=False)

    def _proc_blueprint(
        self,
        setting: ArgumentSetting,
        to_console: bool = True
    ) -> FactoryBlueprint:
        if not to_console:
            # placeholder/cover just in case
            raise NotImplementedError

        exp_def: FactoryBlueprint = {
            "group_label": setting["default_value"],
            "type_label": "",
            "arguments": {}
        }
        # consider moving into two func, interactive & not?
        try:
            type_listing = self.get_registered(group=setting["default_value"])
        except ValueError:
            print(f"ERROR: group not found {setting['default_value']}")
            print(self.scenario_manager)

        idx = len(type_listing) + 10    # more than valid

        if len(type_listing) == 1:
            if self.use_formatting:
                item_listing = prepare_string(
                    text=f"\n--- Only option | {type_listing[0]} ---",
                    css="emphasis",
                    terminal_css=self.terminal_css,
                    dark_mode=self.dark_mode)
            else:
                item_listing = f"\n--- Only option | {type_listing[0]} ---"
            print(item_listing)
            idx = 0
        else:
            while idx > len(type_listing) or idx < 0:
                msg = f"\nWhat is the {setting['default_value']} you wish to "\
                    f"construct from? Enter 0-{len(type_listing)-1} [0]: "
                if self.use_formatting:
                    msg = prepare_string(
                        text=msg,
                        css="build",
                        terminal_css=self.terminal_css,
                        dark_mode=self.dark_mode)

                type_label = input(msg)
                if len(type_label) == 0:
                    type_label = "0"
                idx = int(type_label)

                if idx > len(type_listing):
                    msg = f"ERROR. Invalid option {type_label}. Please enter a number "\
                        f" from 0 to {len(type_listing)-1} [0]: "
                    print(msg)

            print()

        if self.scenario_manager is None:
            raise UnboundLocalError("scenario_manager not created")

        blueprint = self.scenario_manager.get_blueprint(
            group_label=setting["default_value"], type_label=type_listing[idx])
        exp_def["type_label"] = type_listing[idx]
        if blueprint is None:
            raise InvalidBlueprint("Missing Blueprint definition")
        type_label_section = f'  {blueprint["type_label"]}  '
        line = create_line(type_label_section, char="-")
        if self.use_formatting:
            line = prepare_string(
                text=line,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
            type_label_section = prepare_string(
                text=type_label_section,
                css="build",
                terminal_css=self.terminal_css,
                dark_mode=self.dark_mode)
        print()
        print(type_label_section)
        print(line)
        print()

        exp_def["arguments"] = self._proc_arguments(
            blueprint["arguments"], to_console=True)
        return exp_def

    def _proc_arguments(self, arguments: dict, to_console: bool = True) -> dict:

        exp_config = {}
        for key, value in arguments.items():
            if to_console:
                msg = f"  - Configuring setting <{key}> : "
                if self.use_formatting:
                    msg = prepare_string(
                        text=msg,
                        css="build",
                        terminal_css=self.terminal_css,
                        dark_mode=self.dark_mode)
                print(msg)
            exp_config[key] = self._proc_arg(
                setting=value, to_console=to_console)

        return exp_config

    def _proc_arg(
        self,
        setting: Union[ArgumentSetting, ListArgumentSetting],
        to_console: bool = True
    ) -> Union[list, int, str, float, bool, dict, FactoryBlueprint]:
        if "argument_type" not in setting:
            msg = f"Invalid blueprint: {setting}"
            logging.error(msg)
            raise InvalidBlueprint(msg)

        if setting["argument_type"] == ArgumentType.STRING:
            return self._proc_str(setting=setting, to_console=to_console)
        elif setting["argument_type"] == ArgumentType.INT:
            return self._proc_int(setting=setting, to_console=to_console)
        elif setting["argument_type"] == ArgumentType.FLOAT:
            return self._proc_float(setting=setting, to_console=to_console)
        elif setting["argument_type"] == ArgumentType.BOOL:
            return self._proc_bool(setting=setting, to_console=to_console)
        elif setting["argument_type"] == ArgumentType.BLUEPRINT:
            return self._proc_blueprint(setting=setting, to_console=to_console)
        elif setting["argument_type"] == ArgumentType.LIST:
            setting = cast(ListArgumentSetting, setting)
            return self._proc_list(setting=setting, to_console=to_console)
        elif setting["argument_type"] == ArgumentType.DICT:
            return self._proc_dict(setting=setting, to_console=to_console)

        # should not happen.
        msg = f"Unknown argument type {setting['argument_type']}"
        logging.error(msg)
        raise InvalidBlueprint(msg)

    def _proc_dict(self, setting: ArgumentSetting, to_console: bool = True) -> str:
        """Uses the default only.

        :param setting: _description_
        :type setting: ArgumentSetting
        :param to_console: _description_, defaults to True
        :type to_console: bool, optional
        :return: _description_
        :rtype: str
        """
        if to_console:
            msg = f"    - {setting['help_str']} <= {setting['default_value']}"
            if self.use_formatting:
                msg = prepare_string(
                    text=msg,
                    css="build",
                    terminal_css=self.terminal_css,
                    dark_mode=self.dark_mode)
            print(msg)

        return setting["default_value"]

    def _proc_str(self, setting: ArgumentSetting, to_console: bool = True) -> str:
        if to_console:
            ask_is = f"    - {setting['help_str']} "\
                f"[{setting['default_value']}]: "
            if self.use_formatting:
                ask_is = prepare_string(
                    text=ask_is,
                    css="build",
                    terminal_css=self.terminal_css,
                    dark_mode=self.dark_mode)
            result = input(ask_is)
            if len(result) == 0:
                return setting["default_value"]
        return result

    def _proc_int(self, setting: ArgumentSetting, to_console: bool = True) -> int:

        if to_console:
            not_valid = True
            while not_valid:
                ask_for = f"    - {setting['help_str']} "\
                    f"[{setting['default_value']}]: "
                if self.use_formatting:
                    ask_for = prepare_string(
                        text=ask_for,
                        css="build",
                        terminal_css=self.terminal_css,
                        dark_mode=self.dark_mode)
                result = input(ask_for)
                try:
                    if len(result) == 0:
                        return int(setting["default_value"])
                    return int(result)
                except ValueError:
                    print("Invalid value.")

        # default. should be needed
        return 0

    def _proc_float(
        self,
        setting: ArgumentSetting,
        to_console: bool = True
    ) -> float:
        if to_console:
            not_valid = True
            while not_valid:
                ask_for = f"    - {setting['help_str']} "\
                    f"[{setting['default_value']}]: "
                if self.use_formatting:
                    ask_for = prepare_string(
                        text=ask_for,
                        css="build",
                        terminal_css=self.terminal_css,
                        dark_mode=self.dark_mode)
                result = input(ask_for)
                try:
                    if len(result) == 0:
                        return float(setting["default_value"])
                    return float(result)
                except ValueError:
                    print("Invalid value.")
        # default. should be needed
        return 0.0

    def _proc_bool(
        self,
        setting: ArgumentSetting,
        to_console: bool = True
    ) -> bool:
        if to_console:
            not_valid = True
            while not_valid:
                ask_for = f"    - {setting['help_str']} "\
                    f"[{setting['default_value']}]: "
                if self.use_formatting:
                    ask_for = prepare_string(
                        text=ask_for,
                        css="build",
                        terminal_css=self.terminal_css,
                        dark_mode=self.dark_mode)
                result = input(ask_for)

                try:
                    if len(result) == 0:
                        return string_to_bool(setting["default_value"])
                    return string_to_bool(result)
                except ValueError:
                    print("Invalid value.")

        # default. should be needed
        return False

    def _proc_list(
        self,
        setting: ListArgumentSetting,
        to_console: bool = True
    ) -> list:

        # safety chceks
        if "list_arg_default_value" not in setting:
            raise InvalidBlueprint("Missing list_arg_default_value.")
        elif "list_arg_type" not in setting:
            raise InvalidBlueprint("Missing list_arg_type.")

        # setup
        items = []

        # create a unique ArgumentSetting based on the outer setting
        arg_setting = ArgumentSetting(
            help_str=setting["help_str"],
            default_value=setting["list_arg_default_value"],
            argument_type=setting["list_arg_type"])

        # and interact
        if to_console:
            more = "A"
            print("\n-- START List creation mode -- ")
            while more.upper() != "E":
                more = "E"
                items.append(
                    self._proc_arg(setting=arg_setting, to_console=to_console))
                input_more = input("\nE to end, any other to add more [E]: ")
                if len(input_more) == 0:
                    more = "E"
                else:
                    more = input_more.upper()

            print("-- DONE List creation mode -- \n")            

        return items