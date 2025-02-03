"""Used to demonstrate a typical extension for ADGTK.

Pattern design (to extend the code base with a plugin)
======================================================
Note: This is only needed if you want to register and build with the
Factory. If you are just using the code, you can skip this.
1. Create your module
2. Create a Class with a blueprint, description, and component features.
3. update the __init__.py file to include the class and add to
   register_list.
4. update the settings file to list the module. the "user_modules" list
"""

from adgtk.common import (
    ComponentDef,
    FactoryBlueprint,
    ArgumentSetting,
    ArgumentType)

from adgtk.factory import ObjectFactory


class TestClassOne:
    """An extremely basic class for demonstrating plugin usage.py"""

    description = "This is the text used when giving a user an option."

    blueprint: FactoryBlueprint = {

        "group_label": "plugin",
        "type_label": "test_class_one",
        "arguments": {
            "counter": ArgumentSetting(
                help_str="An example of how to tell the factory to pass a value",
                default_value=0,
                argument_type=ArgumentType.INT),
            "agent": ArgumentSetting(
                help_str="An example of configuring another blueprint",
                default_value="agent",
                argument_type=ArgumentType.BLUEPRINT)
        }
    }

    def __init__(
        self,
        factory: ObjectFactory,
        counter: int,
        agent: ComponentDef
    ):
        # Notice this matches the ArgumentSetting in the arguments of
        # the blueprint.
        self.counter = counter
        self.agent = factory.create(agent)

    def hello(self):
        """Print something to console
        """
        print("Hello World")

    def greeting(self):
        """Print something to console
        """
        print("Greetings from the demo code")
