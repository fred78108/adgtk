===============================
Agentic Data Generation Toolkit
===============================
Agentic Data Generation Toolkit is designed to provide an easy to use interface for both a human user as well as an Agent. The primary purpose of this Toolkit is to provide a framework for experimentation with Agents that generate data. The framework provides all the automation needed to excute a scenario while providing the user with both consistent measurements across scenarios as well as tracking and reporting of results.

----------
Highlights
----------
- A "lab journal" which can be invoked through an experiment.
- Reports saved to disk of both preview and results of an experiment.
- extensible architecture. The framework is designed to be extensible on load and during execution.


Installation
------------
**Note**: This package has not been made available via a public repository. As such the instructions require the following steps for installation.

1. active your virtual environment.
2. navigate to the main folder
3. run: ``$ python -m pip install -e .``

I will be publishing shortly so this section will change.

Folder structure
----------------
**IMPORTANT** The location where you downloaded the source code should not be where you create your project. In a new folder location create a folder where you will be performing your experimentation.

Usage
-----
The adgtk-mgr provides a command line interface to handle the common functions without needing to write or edit code. With your virtual environment activated you can do the following:


Roadmap
-------

Larger features that are planned for the future include:

1. Add the ability to filter data within a measurement set before measuring.
2. Add the ability to start a HTTP server from the CLI with a page that indexes and shows the reports.
3. Add project journal and tracking of experiments.
4. Re-write the CLI launch to be more user friendly by not requiring commands. It will be an interactive menu driven experience.
5. Provide an improved experiment builder experience with a split screen view.
