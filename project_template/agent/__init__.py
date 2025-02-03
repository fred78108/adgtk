"""The Agent module is focused on providing a consistent design for the
Agents within a given project.
"""


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
# from .simple import BasicAgent
from .generation import GenerationAgent


register_list = [GenerationAgent]
