"""Builds and manages experiments"""
import logging
import sys
import os
from typing import Union, cast
import toml
import yaml
from adgtk.factory import InvalidBlueprint
from adgtk.common import (
    FactoryBlueprint,
    ExperimentDefinition,
    ArgumentSetting,
    ArgumentType,
    convert_exp_def_to_string)
from adgtk.scenario import ScenarioManager, SCENARIO_GROUP_LABEL
from adgtk.utils import (
    get_user_input,
    get_more_ask,
    create_line)


class ExperimentBuilder():
    """Used to build experiments"""

    def __init__(
        self,
        experiment_definition_dir: str,
        load_user_modules:list,
        scenario_manager: Union[ScenarioManager, None] = None,
    ):
        self.experiment_definition_dir = experiment_definition_dir
        self.outer_configuring = "Scenario"     # for list processing
        self.currently_configuring = "Experiment"
        self.file_format = "yaml"
        self.last_line = ""

        if scenario_manager is None:
            self.scenario_manager = ScenarioManager(
                blueprint_dir="blueprints",
                load_user_modules=load_user_modules,
                experiment_definition_dir=experiment_definition_dir)
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
            err_msg = "group not found. Check factory"
            if group == SCENARIO_GROUP_LABEL:                
                err_msg = "no scenarios found. Review your factory and"\
                          " code. The scenario should be listed when you "\
                          f"review the factory. observed {group}"
            else:
                if isinstance(group, str):
                    err_msg = f"group not found: {group}. Check factory"

            logging.error(err_msg)
            sys.exit(1)
        if not to_console:
            return registered_types

        group_title = f"\n Registered {group} types are :"
        line_list = ["."] * len(group_title)
        line = "".join(line_list)
        print(group_title)
        print(line)
        print()

        for label in registered_types:
            label_text = f" - {label}"
            desc = self.scenario_manager.get_description(
                group_label=group,
                type_label=label)

            print(f"{label_text:<30} | {desc}")

        print()  # extra space
        return registered_types

    def build_interactive(self, name: Union[str, None] = None):
        """Interactive building of an experiment. This is the entry
        point for the experiment builder. It provides the UX for
        creating an experiment and saving to disk.

        :param name: The name of the experiment, defaults to None
        :type name: Union[str, None], optional
        """

        exp_title = ". Experiment builder wizard ."
        self.last_line = create_line(exp_title, char=".")
        print(self.last_line)
        print(exp_title)
        print(self.last_line)

        # -------------------------------------------------------------
        # get the global settings, name, description
        # -------------------------------------------------------------
        if name is None:
            exp_name = get_user_input(
                configuring=self.currently_configuring,
                request="Please enter the name of the experiment",
                requested="str",
                allow_whitespace=False,
                helper="This should be a unique name. This is your filename")
        else:
            exp_name = name

        comments = get_user_input(
            configuring=self.currently_configuring,
            requested="str",
            request="Short description of the experiment",
            max_characters=50,
            helper="This should be less than 50 characters")

        if not isinstance(comments, str):
            comments = ""
            logging.warning("Error processing comments input")

        # start working on the scenario
        self.currently_configuring = "Scenario"
        scenario_setting = ArgumentSetting(
            help_str="\nWhat scenario do you wish to construct from?",
            group_label="scenario",
            argument_type=ArgumentType.BLUEPRINT)
        exp_conf = self._proc_blueprint(scenario_setting)
        experiment = ExperimentDefinition(
            configuration=exp_conf, comments=comments)
        
        # ensure group label is set post processing.
        exp_conf["group_label"] = SCENARIO_GROUP_LABEL
        preview = convert_exp_def_to_string(exp_conf)
        intro = f"\nExperiment preview for {exp_name}: "
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
        
        save_as = get_user_input(
            configuring=self.currently_configuring,
            request="Save file as",
            requested="str",
            default_selection=file_w_path,
            allow_whitespace=False)

        # take the default?
        if isinstance(save_as, str):
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
        else:
            logging.error("Unable to save file due to unexpected input")

    def _proc_blueprint(self, setting: ArgumentSetting) -> FactoryBlueprint:
        """Processes a blueprint argugment

        :param setting: The setting to process
        :type setting: ArgumentSetting
        :raises InvalidBlueprint: Missing Blueprint definition
        :return: A blueprint for the factory
        :rtype: FactoryBlueprint
        """

        exp_def: FactoryBlueprint = {
            "group_label": "experiment",    # not used in this context
            "type_label" : "",
            "arguments" : {},
        }
        if "group_label" not in setting:
            msg = f"Invalid blueprint: {setting}. Missing group_label"
            logging.error(msg)
            raise InvalidBlueprint(msg)

        try:
            type_listing = self.get_registered(
                group=setting["group_label"], to_console=False)
        except ValueError:
            print(f"ERROR: group not found {setting['default_value']}")
            print(self.scenario_manager)
            sys.exit()


        if len(type_listing) == 1:

            # skip the UX for the built-in objects that have only one
            if setting["group_label"]  == "measurement-engine":
                pass
            elif setting["group_label"]  == "measurement-set":
                pass
            else:
                msg = f"\nNOTE: Factory only has option: {setting['group_label']}:"
                msg += f"{type_listing[0]}"
                self.last_line = create_line(msg, char=".")
                print(msg)
                print(self.last_line)
                print()

            
            type_label = type_listing[0]

        else:
            # re-pull, but display to console
            type_listing = self.get_registered(
                group=setting["group_label"], to_console=True)

            type_label = get_user_input(
                configuring=self.currently_configuring,
                request=setting["help_str"],
                choices=type_listing,
                requested="str")

        blueprint = self.scenario_manager.get_blueprint(
            group_label=setting["group_label"], type_label=type_label)
        
        if "introduction" in blueprint:
            print()
            print()
            self.last_line = create_line(
                text=self.last_line, char="=", title=blueprint["group_label"])
            print(self.last_line)
            print(blueprint["introduction"])
            self.last_line = create_line(text=self.last_line, char="=")
            print(self.last_line)

        exp_def["type_label"] = type_label
        if blueprint is None:
            raise InvalidBlueprint("Missing Blueprint definition")

        self.currently_configuring = \
            f"{blueprint['group_label']}:{blueprint['type_label']}"

        exp_def["arguments"] = self._proc_arguments(blueprint["arguments"])
        return exp_def

    def _proc_arguments(self, arguments: dict) -> dict:
        """Processes the arguments for the blueprint

        :param arguments: The arguments to process
        :type arguments: dict
        :return: The processed arguments
        :rtype: dict
        """

        exp_config = {}
        for key, value in arguments.items():
            exp_config[key] = self._proc_arg(setting=value)

        return exp_config

    def _proc_arg(
        self,
        setting: ArgumentSetting
    ) -> Union[list, int, str, float, bool, dict, FactoryBlueprint]:
        """Process a single argument

        :param setting: The argument to process
        :type setting: ArgumentSetting
        :raises InvalidBlueprint: Invalid blueprint found
        :return: The result based on the requested type in the setting
        :rtype: Union[list, int, str, float, bool, dict, FactoryBlueprint]
        """
        if "argument_type" not in setting:
            msg = f"Invalid blueprint: {setting}"
            logging.error(msg)
            raise InvalidBlueprint(msg)

        # cover the optional key(s)
        if "default_value" not in setting:
            setting["default_value"] = None
    

        if setting["argument_type"] == ArgumentType.ML_STRING:
            return get_user_input(
                configuring=self.currently_configuring,
                request=setting["help_str"],
                default_selection=setting["default_value"],
                requested="ml-str",
                helper="Press [Esc] followed by [Enter] to complete input")
            
        if setting["argument_type"] == ArgumentType.STRING:

            return get_user_input(
                configuring=self.currently_configuring,
                request=setting["help_str"],
                default_selection=setting["default_value"],
                requested="str",
                helper="please enter a string")
        elif setting["argument_type"] == ArgumentType.INT:
            return get_user_input(
                configuring=self.currently_configuring,
                request=setting["help_str"],
                default_selection=setting["default_value"],
                requested="int",
                helper="please enter an Integer")
        elif setting["argument_type"] == ArgumentType.FLOAT:
            return get_user_input(
                configuring=self.currently_configuring,
                request=setting["help_str"],
                default_selection=setting["default_value"],
                requested="float",
                helper="please enter a float")
        elif setting["argument_type"] == ArgumentType.BOOL:
            return self._proc_bool(setting=setting)
        elif setting["argument_type"] == ArgumentType.BLUEPRINT:
            return self._proc_blueprint(setting=setting)
        elif setting["argument_type"] == ArgumentType.LIST:
            return self._proc_list(setting=setting)
        elif setting["argument_type"] == ArgumentType.DICT:
            return self._proc_dict(setting=setting)

    def _get_bool_reply(self, help_str:str,default:Union[str, bool]) -> bool:
        if isinstance(default, str):
            default_str = default.lower()
        else:
            if default:
                default_str = "true"
            else:
                default_str = "false"

        value = get_user_input(
            request=help_str,
            requested="str",
            choices=["true", "false"],
            default_selection=default_str,
            configuring=self.currently_configuring)

        if isinstance(value, str):
            if value.lower() == "true":
                return True

        return False               

    def _proc_bool(self, setting: ArgumentSetting) -> bool:
        """Process a boolean setting request

        :param setting: The requested setting
        :type setting: ArgumentSetting
        :return: The user input
        :rtype: bool
        """
        return self._get_bool_reply(
            help_str=setting["help_str"],
            default=setting["default_value"])
        
    def _proc_list(self, setting: ArgumentSetting) -> list:
        """Process a list of entries from the user

        :param setting: The requested argument entries
        :type setting: ArgumentSetting
        :return: The user input
        :rtype: list
        """

        # Introductions
        
        if "list_intro" in setting:
            self.last_line = create_line(
                text=self.last_line, char=".", title="list entry")
            print(self.last_line)
            if "group_label" in setting:
                title = create_line(
                text=self.last_line, char="=", title=setting["group_label"])    
            else:
                title = create_line(text=self.last_line, char="=")    
            
            print(setting["list_intro"])
            print(title)
                
        if "list_arg_type" not in setting:
            msg = f"Invalid blueprint: {setting}. Missing list_arg_type"
            logging.error(msg)
            raise InvalidBlueprint(msg)
        
        arg_setting = ArgumentSetting(
                help_str=setting["help_str"],                
                argument_type=setting["list_arg_type"])
    
        # copy over optional?
        if "default_value" in setting:
                arg_setting["default_value"] = setting["default_value"]
        if "introduction" in setting:
                arg_setting["introduction"] = setting["introduction"]
        
        if setting["list_arg_type"] == ArgumentType.BLUEPRINT:
            if "list_group_label" not in setting:
                msg = f"Invalid blueprint: {setting}. Missing list_group_label"
                logging.error(msg)
                raise InvalidBlueprint(msg)
            arg_setting["group_label"] = setting["list_group_label"]  
                
        # setup
        items = []

        more = True
        print(setting['help_str'])

        # Is empty ok?
        if "list_min" in setting:
            if setting["list_min"] == 0:
                no_data = self._get_bool_reply(
                    help_str="Do you want to set as []",
                    default=True)

                if no_data:
                    return []        


        self.outer_configuring = self.currently_configuring
        while more:
            items.append(self._proc_arg(setting=arg_setting))
            more = get_more_ask(self.currently_configuring)
        print()
        self.currently_configuring = self.outer_configuring

        return items

    def _proc_dict(self, setting: ArgumentSetting) -> dict:
        """Processes collection of a dictionary key value pairs from the
        user.

        :param setting: The argument to process
        :type setting: ArgumentSetting
        :return: The user input
        :rtype: dict
        """

        data = {}
        more = True

        while more:
            key = get_user_input(
                request=f"{setting['help_str']} [key]",
                configuring=self.currently_configuring,
                requested="str",
                min_characters=1,
                allow_whitespace=False)

            value = get_user_input(
                request=f"{setting['help_str']} [{key} value]",
                configuring=self.currently_configuring,
                requested="str",
                allow_whitespace=True)

            if key in data:
                print(f"Key {key} already exists. no action taken.")
            else:
                data[key] = value

            more = get_more_ask(self.currently_configuring)

        return data
