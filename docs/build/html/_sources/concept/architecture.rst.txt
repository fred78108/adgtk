============
Architecture
============

.. toctree::
    :maxdepth: 2

ADGTK provides a framework for both a human and an automated agent to explore the creation of synthetic data. The framework is designed to provide a consistent environment for the agent to operate in, while providing the human user with the ability to track and report on the results of the agent's actions. The framework can also be used by a human to create the automated agent which will then interact within the system but this is not a requirement of the framework.

The framework is designed to be extensible, allowing the user to create custom components to be used in their experiments. The user is not constrained to the components that are provided.


System context
==============
There are two main interfaces for ADGTK. For the human user its a command line interface (CLI) and for the agent it is a set of APIs. The CLI is designed to be a simple interface for the user to interact with the framework. The APIs are designed to be a simple interface for the agent to interact with the framework.

.. image:: ../_static/adgtk.c4.context.png
    :alt: ADGTK Context Diagram
    :align: center
    :width: 800px


ADGTK attempts to save all configuration and data along with any experimental results with measurements to disk. This allows for follow up analysis and reporting on the results of the experiments. It also creates reports of the results of the experiments that can be shared with others. The current design uses basic HTML for this report. The report contains plots and links to the created data as well as the configuration used for the experiment.

