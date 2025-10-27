"""constants.py handle Constants for the CLI which are larger than
simple strings"""


BOOT_FILENAME = "bootstrap.py"

BOOT_PY = """
\"""bootstrap.py

This script is your startup script. Use this to load your custom code
into the factory.
\"""

import adgtk.factory.component as factory
from adgtk.builtins.scenario import HelloWorldScenario

def foundation():
    \"""These are built-in components that should not be removed unless
    you are replacing them with another. loss of these will impact
    overall operations.
    \"""
    pass
    # factory.register()

def builtin():
    \"""these are optional components that can be removed if desired.\"""
    factory.register(HelloWorldScenario)
    
def user_code():
    pass
    # factory.register()
"""
