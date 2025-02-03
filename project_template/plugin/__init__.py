"""A plugin demo for ADGTK."""

# import your objects
from .demo import TestClassOne

# this is the list of classes that will be registered with the Factory
# by the Scenario Manager or similar objects that need components.

register_list = [TestClassOne]
