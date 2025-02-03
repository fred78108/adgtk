"""Used for creating agents in a project

Versions:
v 0.1
- mvp

References:
-

TODO:

1.0

Defects:

1.0

Test
python -m unittest tests.
"""


import os
import sys
from jinja2 import Environment, FileSystemLoader
from adgtk.utils import camel_case_generation

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
WIZARD_OPTIONS = ("agent", "environment", "policy", "scenario")


def create_blank_agent(agent_name: str) -> None:
    """Creates an Agent plugin using a blank template

    Args:
        agent_name (str): The desired agent name
    """
    print("TESTING")
    target_path = os.path.join("plugins", "agent", agent_name)
    env = Environment(loader=FileSystemLoader(
        os.path.join('templates')))
    template = env.get_template("agent_blank.jinja")

    agent_class_name = camel_case_generation(agent_name)
    output = template.render(agent_class_name=agent_class_name)
    target_file = os.path.join(target_path, "base.py")

    # print(output)
    with open(file=target_file, encoding="utf-8", mode="w") as outfile:
        outfile.write(output)


def create_agent_plugin() -> None:
    """Creates an Agent plugin
    """
    input_msg = "What do you want to name the Agent? \n" \
                "for example my_agent_one: "
    agent_name = input(input_msg).lower()

    if agent_name == "agent":
        print("ERROR: invalid agent name")
        sys.exit()

    target_path = os.path.join("plugins", "agent", agent_name)
    if os.path.exists(target_path):
        print(f"ERROR: {target_path} exists. exiting")
        sys.exit()

    os.makedirs(target_path)
    create_blank_agent(agent_name)
    # Path.touch(os.path.join(target_path, "__init__.py"))
