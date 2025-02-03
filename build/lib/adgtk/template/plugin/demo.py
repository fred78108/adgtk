"""Used to demonstrate a typical extension for ADGTK.

Pattern design (to extend the code base with a plugin)
======================================================
Note: This is only needed if you want to register and build with the
Factory. If you are just using the code, you can skip this.
1. Create your module (or add to this one)
2. Create your Class with a blueprint and component features.
3. update the __init__.py file to include the class and add to
   register_list.
4. update the settings file to list the module.
"""

from adgtk.common import FactoryBlueprint, ArgumentSetting, ArgumentType
from adgtk.factory import ComponentFeatures


class TestClassOne:
    """An extremely basic class for demonstrating plugin usage.py"""

    blueprint: FactoryBlueprint = {

        "group_label": "plugin",
        "type_label": "test_class_one",
        "arguments": {
            "counter": ArgumentSetting(
                help_str="An example of how to tell the factory to pass a value",
                default_value=0,
                argument_type=ArgumentType.INT)
        }
    }

    # Component Features
    # set object_factory to True if you want the Factory to pass itself
    # into the constructor. This is useful if you want to your code will
    # create other objects.

    # set experiment_journal to True if you want the Factory to pass the
    # experiment journal into the constructor. This is useful if you want
    # to log or report information.
    features = ComponentFeatures(
        object_factory=False, experiment_journal=False)

    def __init__(self, counter: int = 0):
        # Notice this matches the ArgumentSetting in the arguments of
        # the blueprint.
        self.counter = counter

    def hello(self):
        """Print something to console
        """
        print("Hello World")

    def greeting(self):
        """Print something to console
        """
        print("Greetings from the demo code")
