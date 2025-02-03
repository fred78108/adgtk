"""Simple formatters
"""

import yaml
from adgtk.common import FactoryBlueprint, ArgumentType, ArgumentSetting

# ----------------------------------------------------------------------
# py -m pytest -s test/data/test_presentation.py
# ----------------------------------------------------------------------


class YamlPresentation:
    """A format for presenting a Presentable Record in YAML format."""

    description = "YAML based text presentation"
    blueprint: FactoryBlueprint = {
        "group_label": "presentation",
        "type_label": "yaml",
        "arguments": {
            "default_flow_style": ArgumentSetting(
                default_value=False,
                help_str="should the presentation use the default style?",
                argument_type=ArgumentType.BOOL)
        }
    }

    def __init__(self, default_flow_style: bool = True):
        self.default_flow_style = default_flow_style

    def present(self, data: dict) -> str:
        """Presents data based on its configuration
        :param data: the data to be presented
        :type data: dict
        :return: a string in the format configured
        :rtype: str
        """
        return yaml.dump(data=data, default_flow_style=self.default_flow_style)
